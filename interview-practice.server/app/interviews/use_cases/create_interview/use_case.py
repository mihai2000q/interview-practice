"""Create Interview: analyse the documents, plan the interview, open it, store it all.

Phase 1 (JD/CV analysis, `app.services.document_analysis`) and phase 2 (`planning.py`)
run in sequence; then the persona's portrait (`portrait.py`) and the interviewer's
opening message are produced together, and everything is committed.
"""

import uuid
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from flask import current_app

from app.errors.exceptions import BadRequestError, NotFoundError
from app.extensions import db
from app.interviews.model_rules import (
    ensure_judge_differs_from_interviewer,
)
from app.interviews.schemas import ExistingJobApplication, InterviewCreate
from app.interviews.shared import live_settings
from app.interviews.shared.conversation import Turn, take_turn
from app.interviews.shared.helpers import generate_helper
from app.interviews.use_cases.create_interview.planning import (
    FALLBACK_DOMAIN,
    CriterionDraft,
    QuestionDraft,
    plan_interview,
)
from app.interviews.use_cases.create_interview.portrait import (
    delete_portrait,
    generate_portrait,
    store_portrait,
)
from app.llm.defaults import (
    DEFAULT_IMAGE_MODEL,
    DEFAULT_INTERVIEW_MODEL,
    completion_settings,
    effective_model,
)
from app.llm.factory import get_llm_client
from app.models import (
    Difficulty,
    Document,
    DocumentType,
    EvaluationCriterion,
    GenerationPhase,
    Interview,
    InterviewPhaseSettings,
    InterviewQuestion,
    InterviewStatus,
    JobApplication,
    Message,
    MessagePhase,
    MessageRole,
)
from app.services.document_analysis import ensure_analyses


def create_interview(body: InterviewCreate) -> Interview:
    """Analyse the documents, plan the interview, open it, and store it all."""
    override = (
        body.phase_settings_override.to_storage()
        if body.phase_settings_override
        else {}
    )
    ensure_judge_differs_from_interviewer(override)

    job_description = _load_document(
        body.job_description_id, DocumentType.job_description
    )
    cv = _load_document(body.cv_id, DocumentType.cv)
    cover_letter = _load_document(body.cover_letter_id, DocumentType.cover_letter)

    setup = _generate_setup(
        job_title=body.job_title,
        company_name=body.company_name,
        seniority=body.seniority,
        difficulty=body.difficulty,
        tone=body.tone,
        interview_type=body.interview_type,
        interviewer_role=body.interviewer_role,
        target_question_count=body.target_question_count,
        job_description=job_description,
        cv=cv,
        cover_letter=cover_letter,
        phase_settings_override=override,
    )

    application: JobApplication | None = None
    if isinstance(body.job_application, ExistingJobApplication):
        application = db.session.get(JobApplication, body.job_application.id)
        if application is None:
            raise NotFoundError("Job application not found.")
    elif body.job_application is not None:
        application = JobApplication(
            company_name=body.company_name or setup.company_name,
            job_title=body.job_title,
            job_description_document=job_description,
            cv_document=cv,
            cover_letter_document=cover_letter,
        )
        db.session.add(application)

    interview = Interview(
        job_application=application,
        job_title=body.job_title,
        company_name=body.company_name,
        domain=setup.domain,
        seniority=body.seniority,
        difficulty=body.difficulty,
        tone=body.tone,
        interview_type=body.interview_type,
        interviewer_role=body.interviewer_role,
        target_question_count=body.target_question_count,
        status=InterviewStatus.in_progress,
        persona_name=setup.persona_name,
        persona_title=setup.persona_title,
        persona_backstory=setup.persona_backstory,
        job_description_document=job_description,
        cv_document=cv,
        cover_letter_document=cover_letter,
        coaching_helpers_enabled=body.coaching_helpers_enabled,
        response_style=body.response_style,
        questions=[
            InterviewQuestion(category=q.category, question=q.question)
            for q in setup.questions
        ],
        evaluation_criteria=[
            EvaluationCriterion(category=c.category, criterion=c.criterion)
            for c in setup.evaluation_criteria
        ],
        phase_settings=[
            InterviewPhaseSettings(phase=GenerationPhase(phase), **settings)
            for phase, settings in override.items()
        ],
    )

    # The interviewer opens the session, so an Interview always has a first message.
    # The portrait is the slowest step and needs only the persona, so it is generated
    # while the opening message is written.
    client = get_llm_client()
    with ThreadPoolExecutor(max_workers=1) as pool:
        portrait_job = (
            pool.submit(
                generate_portrait,
                client,
                DEFAULT_IMAGE_MODEL,
                setup.persona_name,
                setup.persona_title,
                body.tone,
            )
            if current_app.config["PORTRAIT_GENERATION_ENABLED"]
            else None
        )
        opening = take_turn(
            client, *live_settings(override), interview, [], Turn.open, asked=0
        )
        helper = (
            generate_helper(
                client,
                *live_settings(override),
                interview,
                opening.message,
            )
            if interview.coaching_helpers_enabled
            else None
        )
        portrait = portrait_job.result() if portrait_job else None
    interview.messages.append(
        Message(
            role=MessageRole.interviewer,
            phase=MessagePhase.qa,
            content=opening.message,
            helper_text=helper,
            sequence=1,
        )
    )
    interview.persona_image_path = store_portrait(portrait) if portrait else None
    db.session.add(interview)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        if interview.persona_image_path:
            delete_portrait(interview.persona_image_path)
        raise
    return interview


def _load_document(
    document_id: uuid.UUID | None, expected: DocumentType
) -> Document | None:
    if document_id is None:
        return None
    document = db.session.get(Document, document_id)
    if document is None:
        raise BadRequestError("Document not found.", code="DOCUMENT_NOT_FOUND")
    if document.type != expected:
        raise BadRequestError(
            f"expected a {expected.value} Document, got {document.type.value}."
        )
    return document


@dataclass(frozen=True)
class _InterviewSetup:
    domain: str
    company_name: str | None  # read from the JD / cover letter; None if not found
    persona_name: str
    persona_title: str
    persona_backstory: str
    questions: list[QuestionDraft]
    evaluation_criteria: list[CriterionDraft]


def _analysed(document: Document | None, attribute: str) -> str | None:
    if document is None or document.analysis is None:
        return None
    value: str | None = getattr(document.analysis, attribute)
    return value


def _generate_setup(
    *,
    job_title: str,
    company_name: str | None,
    seniority: str,
    difficulty: Difficulty,
    tone: str,
    interview_type: str,
    interviewer_role: str,
    target_question_count: int,
    job_description: Document | None,
    cv: Document | None,
    cover_letter: Document | None,
    phase_settings_override: Mapping[str, Any],
) -> _InterviewSetup:
    """Phase 1 for each Document, then phase 2 for the whole Interview."""
    client = get_llm_client()
    documents = [d for d in (job_description, cv, cover_letter) if d is not None]
    ensure_analyses(
        client,
        effective_model(
            phase_settings_override, "jd_analysis", DEFAULT_INTERVIEW_MODEL
        ),
        completion_settings(phase_settings_override, "jd_analysis"),
        documents,
    )

    analysed_company = _analysed(job_description, "company_name") or _analysed(
        cover_letter, "company_name"
    )
    domain = _analysed(job_description, "domain") or _analysed(cv, "domain")

    plan = plan_interview(
        client,
        effective_model(
            phase_settings_override, "question_plan", DEFAULT_INTERVIEW_MODEL
        ),
        completion_settings(phase_settings_override, "question_plan"),
        job_title=job_title,
        seniority=seniority,
        difficulty=difficulty,
        tone=tone,
        interview_type=interview_type,
        interviewer_role=interviewer_role,
        target_question_count=target_question_count,
        company_name=company_name or analysed_company,
        domain=domain,
        job_description_analysis=job_description.analysis if job_description else None,
        cv_analysis=cv.analysis if cv else None,
    )

    return _InterviewSetup(
        domain=domain or plan.domain or FALLBACK_DOMAIN,
        company_name=analysed_company,
        persona_name=plan.persona_name,
        persona_title=plan.persona_title,
        persona_backstory=plan.persona_backstory,
        questions=plan.questions,
        evaluation_criteria=plan.evaluation_criteria,
    )

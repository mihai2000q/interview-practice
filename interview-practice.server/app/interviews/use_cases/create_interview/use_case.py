"""Create Interview: analyse the documents, plan the interview, open it, store it all.

Phase 1 (JD/CV analysis, `app.services.document_analysis`) and phase 2 (`planning.py`)
run in sequence; then the persona's portrait (`portrait.py`) and the interviewer's
opening message are produced together, and everything is committed.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial

from flask import current_app

from app.errors.exceptions import BadRequestError, NotFoundError
from app.extensions import db
from app.interviews.schemas import ExistingJobApplication, InterviewCreate
from app.interviews.shared.exchange import run_exchange
from app.interviews.use_cases.create_interview.planning import (
    InterviewPlan,
    plan_interview,
)
from app.interviews.use_cases.create_interview.portrait import (
    delete_portrait,
    generate_portrait,
    store_portrait,
)
from app.llm.concurrency import background
from app.llm.factory import get_llm_client
from app.llm.openrouter import GeneratedImage, OpenRouterClient
from app.llm.phase_settings import (
    DEFAULT_IMAGE_MODEL,
    ensure_judge_differs_from_interviewer,
    phase_config,
)
from app.models import (
    Document,
    DocumentType,
    EvaluationCriterion,
    GenerationPhase,
    Interview,
    InterviewPhaseSettings,
    InterviewQuestion,
    InterviewStatus,
    JobApplication,
)
from app.services.document_analysis import JobContext, analyse_job_documents


def create_interview(body: InterviewCreate) -> Interview:
    """Analyse the documents, plan the interview, open it, and store it all."""
    phase_settings = (
        body.phase_settings_override.to_rows() if body.phase_settings_override else []
    )
    ensure_judge_differs_from_interviewer(phase_settings)
    client = get_llm_client()

    documents = _load_documents(body)
    context = analyse_job_documents(
        client,
        *phase_config(GenerationPhase.jd_analysis, phase_settings),
        job_description=documents.job_description,
        cv=documents.cv,
        cover_letter=documents.cover_letter,
    )
    plan = plan_interview(
        client,
        *phase_config(GenerationPhase.question_plan, phase_settings),
        body,
        context,
    )
    application = _resolve_application(body, context, documents)
    interview = _build_interview(body, plan, application, documents, phase_settings)

    portrait = _open(client, interview)
    _store(interview, portrait)
    return interview


@dataclass(frozen=True)
class _Documents:
    """The three Documents an Interview can be made from, each optional."""

    job_description: Document | None
    cv: Document | None
    cover_letter: Document | None


def _load_documents(body: InterviewCreate) -> _Documents:
    return _Documents(
        _load_document(body.job_description_id, DocumentType.job_description),
        _load_document(body.cv_id, DocumentType.cv),
        _load_document(body.cover_letter_id, DocumentType.cover_letter),
    )


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


def _resolve_application(
    body: InterviewCreate, context: JobContext, documents: _Documents
) -> JobApplication | None:
    """None for a standalone Interview, an existing JobApplication, or a new one."""
    if isinstance(body.job_application, ExistingJobApplication):
        application = db.session.get(JobApplication, body.job_application.id)
        if application is None:
            raise NotFoundError("Job application not found.")
        return application
    if body.job_application is None:
        return None
    application = JobApplication(
        company_name=body.company_name or context.company_name,
        job_title=body.job_title,
        job_description_document=documents.job_description,
        cv_document=documents.cv,
        cover_letter_document=documents.cover_letter,
    )
    db.session.add(application)
    return application


def _build_interview(
    body: InterviewCreate,
    plan: InterviewPlan,
    application: JobApplication | None,
    documents: _Documents,
    phase_settings: Sequence[InterviewPhaseSettings],
) -> Interview:
    """The request and the plan, mapped field by field onto an unsaved Interview."""
    return Interview(
        job_application=application,
        job_title=body.job_title,
        company_name=body.company_name,
        domain=plan.domain,
        seniority=body.seniority,
        difficulty=body.difficulty,
        tone=body.tone,
        interview_type=body.interview_type,
        interviewer_role=body.interviewer_role,
        target_question_count=body.target_question_count,
        status=InterviewStatus.in_progress,
        persona_name=plan.persona_name,
        persona_title=plan.persona_title,
        persona_backstory=plan.persona_backstory,
        job_description_document=documents.job_description,
        cv_document=documents.cv,
        cover_letter_document=documents.cover_letter,
        coaching_helpers_enabled=body.coaching_helpers_enabled,
        response_style=body.response_style,
        questions=[
            InterviewQuestion(category=q.category, question=q.question)
            for q in plan.questions
        ],
        evaluation_criteria=[
            EvaluationCriterion(category=c.category, criterion=c.criterion)
            for c in plan.evaluation_criteria
        ],
        phase_settings=list(phase_settings),
    )


def _open(client: OpenRouterClient, interview: Interview) -> GeneratedImage | None:
    """Add the interviewer's opening message; returns the persona's portrait, if any.

    The portrait is the slowest step and needs only the persona, so it is generated
    while the opening message is written.
    """
    portrait_job = (
        background(
            partial(
                generate_portrait,
                client,
                DEFAULT_IMAGE_MODEL,
                interview.persona_name,
                interview.persona_title,
                interview.tone,
            )
        )
        if current_app.config["PORTRAIT_GENERATION_ENABLED"]
        else None
    )
    try:
        model, settings = phase_config(
            GenerationPhase.live_conversation, interview.phase_settings
        )
        opening = run_exchange(client, model, settings, interview, None)
        portrait = portrait_job.result() if portrait_job else None
    finally:
        # If the opening failed the error goes out at once: don't wait for the image.
        if portrait_job:
            portrait_job.abandon()
    opening.apply_to(interview)
    return portrait


def _store(interview: Interview, portrait: GeneratedImage | None) -> None:
    """Keep the portrait file and commit; a failed commit removes the file again."""
    interview.persona_image_path = store_portrait(portrait) if portrait else None
    db.session.add(interview)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        if interview.persona_image_path:
            delete_portrait(interview.persona_image_path)
        raise

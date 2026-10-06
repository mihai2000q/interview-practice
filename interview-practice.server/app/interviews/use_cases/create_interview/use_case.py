"""Create Interview: analyze the documents, plan the interview, store it.

Phase 1 (JD/CV analysis, `app.services.document_analysis`) and phase 2 (`planning.py`)
run in sequence and the Interview is committed. The interviewer's opening message and
the persona's portrait are not made here: the session page asks for them (`PUT
.../opening`, `PUT .../persona-image`), so the candidate reaches the session as soon as
the plan exists.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.errors.exceptions import BadRequestError, NotFoundError
from app.extensions import db
from app.interviews.schemas import ExistingJobApplication, InterviewCreate
from app.interviews.use_cases.create_interview.planning import (
    InterviewPlan,
    plan_interview,
)
from app.llm.factory import get_llm_client
from app.llm.phase_settings import (
    ensure_judge_differs_from_interviewer,
    ensure_overrides_allowed,
    phase_config,
)
from app.llm.timing import timed
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
from app.services.document_analysis import analyze_job_documents
from app.services.preferences import load_preferences


def create_interview(body: InterviewCreate) -> Interview:
    """Analyze the documents, plan the interview, and store it."""
    phase_settings = (
        body.phase_settings_override.to_rows() if body.phase_settings_override else []
    )
    ensure_overrides_allowed(phase_settings)
    preferences = load_preferences()
    ensure_judge_differs_from_interviewer(phase_settings, preferences)
    client = get_llm_client()

    documents = _load_documents(body)
    with timed("analysis"):
        context = analyze_job_documents(
            client,
            *phase_config(GenerationPhase.jd_analysis, phase_settings, preferences),
            job_description=documents.job_description,
            cv=documents.cv,
            cover_letter=documents.cover_letter,
        )
    with timed("plan"):
        plan = plan_interview(
            client,
            *phase_config(GenerationPhase.question_plan, phase_settings, preferences),
            body,
            context,
        )
    application = _resolve_application(body, plan, documents)
    interview = _build_interview(body, plan, application, documents, phase_settings)

    db.session.add(interview)
    db.session.commit()
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
        raise NotFoundError("Document not found.")
    if document.type != expected:
        raise BadRequestError(
            f"expected a {expected.value} Document, got {document.type.value}."
        )
    return document


def _resolve_application(
    body: InterviewCreate, plan: InterviewPlan, documents: _Documents
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
        company_name=plan.company_name,
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
        company_name=plan.company_name,
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

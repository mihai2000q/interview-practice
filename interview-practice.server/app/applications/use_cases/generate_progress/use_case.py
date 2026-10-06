"""The progress summary of an Application, made now if it is missing or out of date.

Only the Evaluations that exist are read; making the missing ones is the client's job
(ADR 0015), through the interviews API, so this domain never calls into that one.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import joinedload, selectinload

from app.applications.use_cases.generate_progress.summary import (
    ProgressDraft,
    build_messages,
    summarize,
)
from app.errors.exceptions import ConflictError, NotFoundError
from app.extensions import db
from app.llm.factory import get_llm_client
from app.llm.phase_settings import phase_config
from app.llm.timing import timed
from app.models import GenerationPhase, Interview, JobApplication
from app.models.application_progress import MIN_EVALUATIONS, progress_basis
from app.services.preferences import load_preferences


def generate_progress(application_id: uuid.UUID) -> JobApplication:
    """The Application with a progress score and summary built from its current
    Evaluations.

    Idempotent: when they are the ones the stored pair was built from, it answers with
    that and calls no model. Two calls at once may both run the model; the first to
    store wins and both get that one.
    """
    application = _load(application_id)
    graded = [i for i in application.interviews if i.evaluation is not None]
    if len(graded) < MIN_EVALUATIONS:
        raise ConflictError(
            f"Comparing stages needs at least {MIN_EVALUATIONS} graded ones.",
            code="NOT_ENOUGH_STAGES",
        )
    basis = progress_basis(i.evaluation.id for i in graded if i.evaluation)
    if application.progress_basis == basis and application.progress_score is not None:
        return application

    # An Application has no overrides of its own: Preferences, else the default.
    model, settings = phase_config(GenerationPhase.evaluation, (), load_preferences())
    messages = build_messages(graded)
    seen_basis = application.progress_basis
    # Don't hold a connection in an open transaction while the model works.
    db.session.rollback()
    with timed("progress"):
        draft = summarize(get_llm_client(), model, settings, messages)
    return _store(application_id, seen_basis, basis, draft)


def _load(application_id: uuid.UUID) -> JobApplication:
    statement = (
        select(JobApplication)
        .where(JobApplication.id == application_id)
        .options(
            selectinload(JobApplication.interviews).options(
                joinedload(Interview.evaluation),
                selectinload(Interview.evaluation_criteria),
            )
        )
    )
    application = db.session.scalars(statement).unique().one_or_none()
    if application is None:
        raise NotFoundError("Application not found.")
    return application


def _store(
    application_id: uuid.UUID,
    seen_basis: str | None,
    basis: str,
    draft: ProgressDraft,
) -> JobApplication:
    """Store the pair unless another call did first (the basis moved on from the one
    this call read), and return the Application as it now stands."""
    db.session.execute(
        update(JobApplication)
        .where(
            JobApplication.id == application_id,
            JobApplication.progress_basis.is_not_distinct_from(seen_basis),
        )
        .values(
            progress_score=draft.progress_score,
            progress_summary=draft.progress_summary,
            progress_basis=basis,
        )
    )
    db.session.commit()
    stored = db.session.scalar(
        select(JobApplication)
        .where(JobApplication.id == application_id)
        .execution_options(populate_existing=True)
    )
    if stored is None:  # deleted while the model worked
        raise NotFoundError("Application not found.")
    return stored

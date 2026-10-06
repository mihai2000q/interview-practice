import uuid

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.errors.exceptions import NotFoundError
from app.extensions import db
from app.models import Document, Evaluation, Interview, JobApplication
from app.services.interview_lifecycle import settle_stale


def get_application(application_id: uuid.UUID) -> JobApplication:
    """One JobApplication with its stages (oldest first) as they stand now.

    Stages that went stale are closed as they are read (ADR 0006). Only each stage's
    Evaluation verdict is loaded, and none is ever generated here.
    """
    statement = (
        select(JobApplication)
        .where(JobApplication.id == application_id)
        .options(
            selectinload(JobApplication.interviews)
            .joinedload(Interview.evaluation)
            .load_only(Evaluation.verdict),
            joinedload(JobApplication.job_description_document).joinedload(
                Document.analysis
            ),
            joinedload(JobApplication.cv_document).joinedload(Document.analysis),
            joinedload(JobApplication.cover_letter_document).joinedload(
                Document.analysis
            ),
        )
    )
    application = db.session.scalars(statement).unique().one_or_none()
    if application is None:
        raise NotFoundError("Application not found.")
    settle_stale(application.interviews)
    return application

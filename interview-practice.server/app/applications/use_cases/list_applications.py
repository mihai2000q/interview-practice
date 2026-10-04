from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models import JobApplication
from app.services.interview_lifecycle import settle_stale


def list_applications() -> list[JobApplication]:
    """Every JobApplication, newest first, with its stages as they stand now.

    Stages that went stale are closed as they are read (ADR 0006), so the pipeline never
    shows a dead session as in progress.
    """
    statement = (
        select(JobApplication)
        .options(
            selectinload(JobApplication.interviews),
            joinedload(JobApplication.job_description_document),
            joinedload(JobApplication.cv_document),
            joinedload(JobApplication.cover_letter_document),
        )
        .order_by(JobApplication.created_at.desc())
    )
    applications = list(db.session.scalars(statement))
    settle_stale(i for application in applications for i in application.interviews)
    return applications

"""Loading an Interview as it should be seen now, and checking it can be acted on."""

import uuid

from app.errors.exceptions import ConflictError, NotFoundError
from app.extensions import db
from app.models import Interview, InterviewStatus
from app.services.interview_lifecycle import settle_stale


def get_interview_or_404(interview_id: uuid.UUID) -> Interview:
    """The Interview; one that went stale is closed as part of loading it (ADR 0006),
    so no reader can see (or act on) a dead session as still in progress."""
    interview = db.session.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError("Interview not found.")
    settle_stale([interview])
    return interview


def ensure_in_progress(interview: Interview) -> None:
    if interview.status is not InterviewStatus.in_progress:
        raise ConflictError("This interview has ended.", code="INTERVIEW_ALREADY_ENDED")

import uuid

from app.interviews.shared import get_interview_or_404
from app.models import Interview


def get_interview(interview_id: uuid.UUID) -> Interview:
    """The Interview with its transcript; a stale session is closed as it is read."""
    return get_interview_or_404(interview_id)

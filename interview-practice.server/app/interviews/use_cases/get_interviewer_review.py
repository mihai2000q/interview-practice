import uuid

from app.errors.exceptions import NotFoundError
from app.interviews.shared import get_interview_or_404
from app.models import InterviewerReview


def get_interviewer_review(interview_id: uuid.UUID) -> InterviewerReview:
    """The stored review; it is made with the Evaluation, but a failed judge call
    leaves it missing, so this can be a 404 after the Evaluation exists."""
    review = get_interview_or_404(interview_id).interviewer_review
    if review is None:
        raise NotFoundError("This interview has no interviewer review.")
    return review

import uuid

from app.errors.exceptions import NotFoundError
from app.interviews.shared import get_interview_or_404
from app.models import Evaluation


def get_evaluation(interview_id: uuid.UUID) -> Evaluation:
    """The stored Evaluation; it exists once `PUT .../evaluation` has produced it."""
    evaluation = get_interview_or_404(interview_id).evaluation
    if evaluation is None:
        raise NotFoundError("This interview has no evaluation yet.")
    return evaluation

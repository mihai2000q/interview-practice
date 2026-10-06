import uuid

from app.extensions import db
from app.interviews.shared import ensure_in_progress, get_interview_or_404
from app.models import Interview, InterviewStatus
from app.services.interview_lifecycle import end


def abandon_interview(interview_id: uuid.UUID) -> Interview:
    interview = get_interview_or_404(interview_id)
    ensure_in_progress(interview)
    # Re-read under a short lock: an exchange may be finishing (even completing the
    # Interview) right now, and abandoning must not overwrite that.
    db.session.refresh(interview, with_for_update=True)
    ensure_in_progress(interview)
    end(interview, InterviewStatus.abandoned)
    db.session.commit()
    return interview

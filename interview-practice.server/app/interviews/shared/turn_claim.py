"""The in-progress marker that keeps work on one Interview from overlapping (ADR 0013).

Replies and the opening both call the model for seconds. One conditional `UPDATE`
decides who may run; the other caller is refused at once with `409 TURN_IN_PROGRESS`
instead of queueing behind it. No row lock is held while the model works.
"""

import uuid

from sqlalchemy import func, or_, update

from app.errors.exceptions import ConflictError
from app.extensions import db
from app.interviews.shared.interview_access import (
    ensure_in_progress,
    get_interview_or_404,
)
from app.models import Interview, InterviewStatus
from app.services.interview_lifecycle import TURN_TTL


def claim_turn(interview_id: uuid.UUID) -> None:
    """Mark a turn as in progress, or refuse if one already is.

    Staleness is settled first: once the marker is set the Interview always looks
    active, so a session that went stale while the candidate was away must be closed
    before it can be claimed and revived.
    """
    interview = get_interview_or_404(interview_id)
    ensure_in_progress(interview)
    claimed = db.session.execute(
        update(Interview)
        .where(
            Interview.id == interview_id,
            Interview.status == InterviewStatus.in_progress,
            or_(
                Interview.turn_started_at.is_(None),
                Interview.turn_started_at < func.now() - TURN_TTL,
            ),
        )
        .values(turn_started_at=func.now())
        .returning(Interview.id)
    ).scalar_one_or_none()
    db.session.commit()
    if claimed is None:
        ensure_in_progress(interview)  # it may have ended in the meantime
        raise ConflictError(
            "The interviewer is already answering. Wait for it to finish.",
            code="TURN_IN_PROGRESS",
        )


def release_turn(interview_id: uuid.UUID) -> None:
    """Clear the marker after a failed turn (a successful one clears it itself)."""
    db.session.rollback()
    db.session.execute(
        update(Interview)
        .where(Interview.id == interview_id)
        .values(turn_started_at=None)
    )
    db.session.commit()

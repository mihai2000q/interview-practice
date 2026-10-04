import uuid
from dataclasses import dataclass

from sqlalchemy import func, or_, update

from app.errors.exceptions import ConflictError
from app.extensions import db
from app.interviews.shared import (
    ensure_in_progress,
    get_interview_or_404,
)
from app.interviews.shared.exchange import run_exchange
from app.llm.factory import get_llm_client
from app.llm.phase_settings import phase_config
from app.models import (
    GenerationPhase,
    Interview,
    InterviewStatus,
    Message,
    MessagePhase,
)
from app.services.interview_lifecycle import TURN_TTL


@dataclass(frozen=True)
class Exchange:
    """The stored candidate reply and the interviewer's answer, plus where we are."""

    candidate_message: Message
    interviewer_message: Message
    phase: MessagePhase
    status: InterviewStatus


def send_message(interview_id: uuid.UUID, content: str) -> Exchange:
    """The candidate's reply and the interviewer's answer to it."""
    _claim_turn(interview_id)
    try:
        return _exchange(interview_id, content)
    except BaseException:
        _release_turn(interview_id)
        raise


def _claim_turn(interview_id: uuid.UUID) -> None:
    """Mark a turn as in progress, or refuse if one already is.

    One conditional UPDATE decides it, so two replies sent at the same moment can't both
    win. No row lock is held afterwards: the slow LLM calls run without blocking readers
    or the next request, which is simply told to wait.

    Staleness is settled first: once the marker is set the Interview always looks
    active, so a session that went stale while the candidate was away must be closed
    before it can be claimed and revived by this reply.
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
            "A reply is already being processed.", code="TURN_IN_PROGRESS"
        )


def _release_turn(interview_id: uuid.UUID) -> None:
    """Clear the marker after a failed turn (a successful one clears it itself)."""
    db.session.rollback()
    db.session.execute(
        update(Interview)
        .where(Interview.id == interview_id)
        .values(turn_started_at=None)
    )
    db.session.commit()


def _exchange(interview_id: uuid.UUID, content: str) -> Exchange:
    interview = get_interview_or_404(interview_id)
    ensure_in_progress(interview)

    # Ask the model before storing anything, so a failed exchange leaves nothing behind
    # and the candidate can simply send the reply again.
    model, settings = phase_config(
        GenerationPhase.live_conversation, interview.phase_settings
    )
    outcome = run_exchange(get_llm_client(), model, settings, interview, content)

    # Re-read under a short lock: the candidate may have abandoned the Interview while
    # the model was answering, in which case the exchange is dropped.
    db.session.refresh(interview, with_for_update=True)
    if interview.status is not InterviewStatus.in_progress:
        raise ConflictError("This interview has ended.", code="INTERVIEW_ALREADY_ENDED")
    applied = outcome.apply_to(interview)
    interview.turn_started_at = None
    db.session.commit()

    assert applied.candidate_message is not None  # a reply was given
    return Exchange(
        candidate_message=applied.candidate_message,
        interviewer_message=applied.interviewer_message,
        phase=interview.phase,
        status=interview.status,
    )

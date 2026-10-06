import uuid
from dataclasses import dataclass

from app.errors.exceptions import ConflictError
from app.extensions import db
from app.interviews.shared import ensure_in_progress, get_interview_or_404
from app.interviews.shared.exchange import run_exchange
from app.interviews.shared.turn_claim import claim_turn, release_turn
from app.llm.factory import get_llm_client
from app.llm.phase_settings import phase_config
from app.models import (
    GenerationPhase,
    InterviewStatus,
    Message,
    MessagePhase,
)
from app.services.preferences import load_preferences


@dataclass(frozen=True)
class Exchange:
    """The stored candidate reply and the interviewer's answer, plus where we are."""

    candidate_message: Message
    interviewer_message: Message
    phase: MessagePhase
    status: InterviewStatus


def send_message(interview_id: uuid.UUID, content: str) -> Exchange:
    """The candidate's reply and the interviewer's answer to it."""
    claim_turn(interview_id)
    try:
        return _run_and_store_exchange(interview_id, content)
    except BaseException:
        release_turn(interview_id)
        raise


def _run_and_store_exchange(interview_id: uuid.UUID, content: str) -> Exchange:
    interview = get_interview_or_404(interview_id)
    ensure_in_progress(interview)
    if not interview.messages:
        raise ConflictError(
            "The interview hasn't been opened yet.", code="INTERVIEW_NOT_OPENED"
        )

    # Ask the model before storing anything, so a failed exchange leaves nothing behind
    # and the candidate can simply send the reply again.
    model, settings = phase_config(
        GenerationPhase.live_conversation, interview.phase_settings, load_preferences()
    )
    outcome = run_exchange(get_llm_client(), model, settings, interview, content)

    # Re-read under a short lock: the candidate may have abandoned the Interview while
    # the model was answering, in which case the exchange is dropped.
    db.session.refresh(interview, with_for_update=True)
    ensure_in_progress(interview)
    applied = outcome.apply_to(interview)
    interview.turn_started_at = None
    db.session.commit()

    if applied.candidate_message is None:  # a reply was given, so one was stored
        raise RuntimeError("The exchange stored no candidate message.")
    return Exchange(
        candidate_message=applied.candidate_message,
        interviewer_message=applied.interviewer_message,
        phase=interview.phase,
        status=interview.status,
    )

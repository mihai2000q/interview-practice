import uuid

from app.extensions import db
from app.interviews.shared import ensure_in_progress, get_interview_or_404
from app.interviews.shared.exchange import run_exchange
from app.interviews.shared.turn_claim import claim_turn, release_turn
from app.llm.factory import get_llm_client
from app.llm.phase_settings import phase_config
from app.llm.timing import timed
from app.models import GenerationPhase, Message


def open_interview(interview_id: uuid.UUID) -> Message:
    """The interviewer's opening message (a greeting and the first question).

    Called by the session page when it loads, not by Create Interview, so the candidate
    reaches the session without waiting for it. Idempotent: an Interview that already
    has messages answers with its first one and calls no model.
    """
    interview = get_interview_or_404(interview_id)
    if interview.messages:
        return interview.messages[0]
    claim_turn(interview_id)
    try:
        return _run_and_store_opening(interview_id)
    except BaseException:
        release_turn(interview_id)
        raise


def _run_and_store_opening(interview_id: uuid.UUID) -> Message:
    interview = get_interview_or_404(interview_id)
    ensure_in_progress(interview)
    if interview.messages:  # opened while we were claiming
        release_turn(interview_id)
        return interview.messages[0]

    model, settings = phase_config(
        GenerationPhase.live_conversation, interview.phase_settings
    )
    with timed("opening"):
        outcome = run_exchange(get_llm_client(), model, settings, interview, None)

    db.session.refresh(interview, with_for_update=True)
    ensure_in_progress(interview)
    applied = outcome.apply_to(interview)
    interview.turn_started_at = None
    db.session.commit()
    return applied.interviewer_message

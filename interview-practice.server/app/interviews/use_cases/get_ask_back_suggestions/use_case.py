import uuid

from app.errors.exceptions import ConflictError
from app.interviews.shared import ensure_in_progress, get_interview_or_404
from app.interviews.use_cases.get_ask_back_suggestions.suggestions import (
    suggest_questions,
)
from app.llm.factory import get_llm_client
from app.llm.phase_settings import phase_config
from app.models import GenerationPhase, MessagePhase


def get_ask_back_suggestions(interview_id: uuid.UUID) -> list[str]:
    """Ephemeral: nothing is stored until the candidate sends one as a message."""
    interview = get_interview_or_404(interview_id)
    ensure_in_progress(interview)
    if not interview.coaching_helpers_enabled:
        raise ConflictError(
            "Interview helpers are off for this interview.", code="HELPERS_DISABLED"
        )
    if interview.phase is not MessagePhase.ask_back:
        raise ConflictError(
            "Suggestions are only available in the ask-back phase.",
            code="NOT_IN_ASK_BACK_PHASE",
        )
    model, settings = phase_config(GenerationPhase.ask_back, interview.phase_settings)
    return suggest_questions(get_llm_client(), model, settings, interview)

from collections.abc import Mapping
from typing import Any

from app.errors.exceptions import ConflictError
from app.llm.defaults import (
    DEFAULT_INTERVIEW_MODEL,
    DEFAULT_JUDGE_MODEL,
    effective_model,
)

# Phases whose output is "the interviewer" the judge scores (ADR 0009).
INTERVIEWER_PHASES = ("question_plan", "live_conversation")


def ensure_judge_differs_from_interviewer(
    phase_settings_override: Mapping[str, Any] | None,
    *,
    interview_model: str = DEFAULT_INTERVIEW_MODEL,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> None:
    """Enforce ADR 0009: the judge may not be a model that ran the interview.

    `phase_settings_override` is the snake_case `Interview.phase_settings_override`
    shape. Phases without an override fall back to the given Preferences defaults.
    """
    judge = effective_model(phase_settings_override, "interviewer_review", judge_model)
    interviewers = {
        phase: effective_model(phase_settings_override, phase, interview_model)
        for phase in INTERVIEWER_PHASES
    }
    collisions = sorted(p for p, model in interviewers.items() if model == judge)
    if collisions:
        raise ConflictError(
            f"The judge model '{judge}' is also the interviewer model for "
            f"{', '.join(collisions)}. Pick a different judge model.",
            details={"judgeModel": judge, "phases": collisions},
            code="JUDGE_MODEL_COLLISION",
        )


def ensure_preferences_judge_differs(interview_model: str, judge_model: str) -> None:
    """Same rule for the global Preferences pair (`interviewModel` / `judgeModel`)."""
    if interview_model == judge_model:
        raise ConflictError(
            f"The judge model '{judge_model}' cannot be the interview model.",
            details={"judgeModel": judge_model},
            code="JUDGE_MODEL_COLLISION",
        )

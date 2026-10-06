"""Which model and settings each LLM phase runs on.

One module answers "for this phase, given the overrides an Interview carries, which
model and which completion settings", and enforces the judge rule built on that answer
(ADR 0009). Overrides are the `InterviewPhaseSettings` rows themselves, persisted or not
yet saved. A field an override leaves unset falls back to the phase's default; the
defaults are one table here, which is also where Preferences will plug in.
"""

from collections.abc import Iterable
from typing import NamedTuple

from app.errors.exceptions import ConflictError
from app.llm.openrouter import CompletionSettings
from app.models import GenerationPhase, InterviewPhaseSettings

# The portrait is not one of the six phases, so it has no override: a plain default.
DEFAULT_IMAGE_MODEL = "google/gemini-2.5-flash-image"

_INTERVIEW_MODEL = "gpt-5-mini"
_JUDGE_MODEL = "google/gemini-2.5-flash"
_DEFAULT_MODELS = {phase: _INTERVIEW_MODEL for phase in GenerationPhase} | {
    GenerationPhase.interviewer_review: _JUDGE_MODEL
}

# Phases whose output is "the interviewer" the judge scores (ADR 0009).
_INTERVIEWER_PHASES = (GenerationPhase.question_plan, GenerationPhase.live_conversation)


class PhaseConfig(NamedTuple):
    model: str
    settings: CompletionSettings


def phase_config(
    phase: GenerationPhase, overrides: Iterable[InterviewPhaseSettings] = ()
) -> PhaseConfig:
    """The model and settings `phase` runs on; `overrides` are an Interview's rows."""
    row = next((r for r in overrides if r.phase is phase), None)
    if row is None:
        return PhaseConfig(_DEFAULT_MODELS[phase], CompletionSettings())
    return PhaseConfig(
        row.model or _DEFAULT_MODELS[phase],
        CompletionSettings(
            temperature=row.temperature,
            max_tokens=row.max_tokens,
            reasoning_effort=row.reasoning_effort,
        ),
    )


def ensure_judge_differs_from_interviewer(
    overrides: Iterable[InterviewPhaseSettings],
) -> None:
    """Enforce ADR 0009: the judge may not be a model that ran the interview."""
    rows = list(overrides)
    judge = phase_config(GenerationPhase.interviewer_review, rows).model
    collisions = sorted(
        phase.value
        for phase in _INTERVIEWER_PHASES
        if phase_config(phase, rows).model == judge
    )
    if collisions:
        raise ConflictError(
            f"The judge model '{judge}' is also the interviewer model for "
            f"{', '.join(collisions)}. Pick a different judge model.",
            details={"judgeModel": judge, "phases": collisions},
            code="JUDGE_MODEL_COLLISION",
        )

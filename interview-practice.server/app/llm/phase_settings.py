"""Which model and settings each LLM phase runs on.

One module answers "for this phase, given the overrides an Interview carries, which
model and which completion settings", and enforces the judge rule built on that answer
(ADR 0009). Each setting resolves through three layers: the Interview's override (the
`InterviewPhaseSettings` rows, persisted or not yet saved), then the Preferences default
(`PreferencePhaseSettings` rows), then the built-in default, one table here. A layer
that leaves a field unset passes it to the next one.
"""

from collections.abc import Iterable
from typing import Any, NamedTuple

from app.errors.exceptions import BadRequestError, ConflictError
from app.llm.openrouter import CompletionSettings
from app.models import GenerationPhase, InterviewPhaseSettings, PreferencePhaseSettings

# The portrait is not one of the six phases, so it has no override: a plain default.
DEFAULT_IMAGE_MODEL = "google/gemini-2.5-flash-image"

_INTERVIEW_MODEL = "gpt-5-mini"
_JUDGE_MODEL = "google/gemini-2.5-flash"
_DEFAULT_MODELS = {phase: _INTERVIEW_MODEL for phase in GenerationPhase} | {
    GenerationPhase.interviewer_review: _JUDGE_MODEL
}

# The models each kind of phase may run on (docs/architecture.md). The judge's set is
# deliberately not a subset of the interview's: it centers on a different vendor
# (ADR 0009).
_INTERVIEW_MODELS = ("gpt-5-mini", "gpt-5-nano", "gpt-4o-mini")
_JUDGE_MODELS = (
    "google/gemini-2.5-flash",
    "gpt-5-mini",
    "gpt-5-nano",
)

# The reasoning efforts Preferences may set, the same four the client offers.
_REASONING_EFFORTS = ("minimal", "low", "medium", "high")

# Phases whose output is "the interviewer" the judge scores (ADR 0009).
_INTERVIEWER_PHASES = (GenerationPhase.question_plan, GenerationPhase.live_conversation)


class PhaseConfig(NamedTuple):
    model: str
    settings: CompletionSettings


def ensure_model_allowed(phase: GenerationPhase, model: str) -> None:
    """Preferences only lets `phase` run on the models listed for it."""
    allowed = (
        _JUDGE_MODELS
        if phase is GenerationPhase.interviewer_review
        else _INTERVIEW_MODELS
    )
    if model not in allowed:
        raise BadRequestError(
            f"'{model}' is not a model the {phase.value} phase can run on.",
            details={"phase": phase.value, "model": model, "allowed": list(allowed)},
            code="MODEL_NOT_ALLOWED",
        )


def ensure_reasoning_effort_allowed(effort: str) -> None:
    """Preferences only lets a phase run on the reasoning efforts listed here."""
    if effort not in _REASONING_EFFORTS:
        raise BadRequestError(
            f"'{effort}' is not a reasoning effort a phase can run on.",
            details={"reasoningEffort": effort, "allowed": list(_REASONING_EFFORTS)},
            code="REASONING_EFFORT_NOT_ALLOWED",
        )


def ensure_overrides_allowed(rows: Iterable[InterviewPhaseSettings]) -> None:
    """An Interview's overrides only name what Preferences could: models and efforts."""
    for row in rows:
        if row.model is not None:
            ensure_model_allowed(row.phase, row.model)
        if row.reasoning_effort is not None:
            ensure_reasoning_effort_allowed(row.reasoning_effort)


def phase_config(
    phase: GenerationPhase,
    overrides: Iterable[InterviewPhaseSettings] = (),
    preferences: Iterable[PreferencePhaseSettings] = (),
) -> PhaseConfig:
    """The model and settings `phase` runs on: an Interview's `overrides`, else the
    `preferences`, else the built-in default, field by field."""
    layers = [
        next((r for r in rows if r.phase is phase), None)
        for rows in (overrides, preferences)
    ]

    def pick(field: str) -> Any:
        values = (getattr(row, field) for row in layers if row is not None)
        return next((v for v in values if v is not None), None)

    return PhaseConfig(
        pick("model") or _DEFAULT_MODELS[phase],
        CompletionSettings(
            temperature=pick("temperature"),
            max_tokens=pick("max_tokens"),
            reasoning_effort=pick("reasoning_effort"),
        ),
    )


def phase_defaults(
    preferences: Iterable[PreferencePhaseSettings],
) -> dict[GenerationPhase, PhaseConfig]:
    """What every phase runs on when an Interview overrides nothing."""
    rows = list(preferences)
    return {phase: phase_config(phase, (), rows) for phase in GenerationPhase}


def ensure_judge_differs_from_interviewer(
    overrides: Iterable[InterviewPhaseSettings] = (),
    preferences: Iterable[PreferencePhaseSettings] = (),
) -> None:
    """Enforce ADR 0009: the judge may not be a model that ran the interview."""
    rows, defaults = list(overrides), list(preferences)
    judge = phase_config(GenerationPhase.interviewer_review, rows, defaults).model
    collisions = sorted(
        phase.value
        for phase in _INTERVIEWER_PHASES
        if phase_config(phase, rows, defaults).model == judge
    )
    if collisions:
        raise ConflictError(
            f"The judge model '{judge}' is also the interviewer model for "
            f"{', '.join(collisions)}. Pick a different judge model.",
            details={"judgeModel": judge, "phases": collisions},
            code="JUDGE_MODEL_COLLISION",
        )

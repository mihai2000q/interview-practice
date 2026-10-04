"""Default models and the per-phase override lookup, shared by every domain that calls
an LLM (documents, interviews, ...). Interview-specific model rules stay in
`app.interviews.model_rules`.
"""

from collections.abc import Mapping
from typing import Any

from app.llm.openrouter import CompletionSettings

DEFAULT_INTERVIEW_MODEL = "gpt-5-mini"
DEFAULT_JUDGE_MODEL = "google/gemini-2.5-flash"
DEFAULT_IMAGE_MODEL = "google/gemini-2.5-flash-image"


def effective_model(
    phase_settings_override: Mapping[str, Any] | None,
    phase: str,
    default: str,
) -> str:
    """The model a phase will run on: its override if set, else `default`."""
    settings = (phase_settings_override or {}).get(phase) or {}
    model = settings.get("model")
    return model if isinstance(model, str) and model else default


def completion_settings(
    phase_settings_override: Mapping[str, Any] | None, phase: str
) -> CompletionSettings:
    """The per-call LLM settings a phase's override asks for (unset ones stay None)."""
    settings = (phase_settings_override or {}).get(phase) or {}
    return CompletionSettings(
        temperature=settings.get("temperature"),
        max_tokens=settings.get("max_tokens"),
        reasoning_effort=settings.get("reasoning_effort"),
    )

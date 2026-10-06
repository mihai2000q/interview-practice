"""Request schema for the per-phase LLM overrides, shared by the domains using it."""

from pydantic import ConfigDict, Field

from app.models import GenerationPhase, InterviewPhaseSettings
from app.serialization import ApiModel, ShortText


class PhaseSettings(ApiModel):
    """Per-phase LLM overrides; any field left out falls back to Preferences."""

    model_config = ConfigDict(extra="forbid")

    model: ShortText | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    reasoning_effort: ShortText | None = None

    def to_row(self, phase: GenerationPhase) -> InterviewPhaseSettings | None:
        """An unsaved row carrying these overrides, or None if none was given."""
        fields = self.model_dump(by_alias=False, exclude_none=True)
        return InterviewPhaseSettings(phase=phase, **fields) if fields else None

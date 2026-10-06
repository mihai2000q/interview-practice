from typing import Any

from pydantic import model_validator

from app.models import GenerationPhase
from app.serialization import ApiModel


class PhasePreferencesPublic(ApiModel):
    """What one phase runs on by default. `model` is always known (the built-in default
    when none was chosen); a null setting means the provider's own default."""

    model: str
    temperature: float | None
    max_tokens: int | None
    reasoning_effort: str | None


class PreferencesPublic(ApiModel):
    """`GET`/`PATCH /api/preferences`: every phase, keyed like overrides."""

    jd_analysis: PhasePreferencesPublic
    question_plan: PhasePreferencesPublic
    live_conversation: PhasePreferencesPublic
    coaching_helpers: PhasePreferencesPublic
    evaluation: PhasePreferencesPublic
    interviewer_review: PhasePreferencesPublic

    @model_validator(mode="before")
    @classmethod
    def _from_configs(cls, configs: Any) -> Any:
        """Accept the `{phase: PhaseConfig}` the use cases return."""
        if not isinstance(configs, dict) or not all(
            isinstance(key, GenerationPhase) for key in configs
        ):
            return configs
        return {
            phase.value: {"model": config.model, **vars(config.settings)}
            for phase, config in configs.items()
        }


# The response names the six phases as explicit fields (the API contract); they must
# stay in step with the enum the rest of the code uses.
if set(PreferencesPublic.model_fields) != {p.value for p in GenerationPhase}:
    raise RuntimeError("PreferencesPublic and GenerationPhase list different phases")

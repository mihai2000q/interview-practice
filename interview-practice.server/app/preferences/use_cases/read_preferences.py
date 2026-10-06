from app.llm.phase_settings import PhaseConfig, phase_defaults
from app.models import GenerationPhase
from app.services.preferences import load_preferences


def read_preferences() -> dict[GenerationPhase, PhaseConfig]:
    """What each phase runs on when an Interview overrides nothing."""
    return phase_defaults(load_preferences())

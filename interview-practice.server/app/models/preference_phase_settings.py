from __future__ import annotations

import uuid

from sqlalchemy import Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import Base, uuid_pk
from app.models.interview_phase_settings import GenerationPhase


class PreferencePhaseSettings(Base):
    """One phase's global default, set in Preferences.

    The app-wide counterpart of `InterviewPhaseSettings`: a row exists only for a phase
    the developer customized, and a field left null uses the built-in default. An
    Interview's own override still wins over it.
    """

    __tablename__ = "preference_phase_settings"

    id: Mapped[uuid.UUID] = uuid_pk()
    phase: Mapped[GenerationPhase] = mapped_column(Enum(GenerationPhase), unique=True)
    model: Mapped[str | None] = mapped_column(String)
    temperature: Mapped[float | None] = mapped_column(Float)
    max_tokens: Mapped[int | None]
    reasoning_effort: Mapped[str | None] = mapped_column(String)

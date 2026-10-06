from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import Base, uuid_pk

if TYPE_CHECKING:
    from app.models.interview import Interview


class GenerationPhase(enum.Enum):
    """The LLM phases whose settings an Interview can override."""

    jd_analysis = "jd_analysis"
    question_plan = "question_plan"
    live_conversation = "live_conversation"
    coaching_helpers = "coaching_helpers"
    evaluation = "evaluation"
    interviewer_review = "interviewer_review"


class InterviewPhaseSettings(Base):
    """One phase's overrides for one Interview.

    A row exists only for a phase the candidate actually overrode; fields left null use
    the Preferences default.
    """

    __tablename__ = "interview_phase_settings"
    __table_args__ = (UniqueConstraint("interview_id", "phase"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE")
    )
    phase: Mapped[GenerationPhase] = mapped_column(Enum(GenerationPhase))
    model: Mapped[str | None] = mapped_column(String)
    temperature: Mapped[float | None] = mapped_column(Float)
    max_tokens: Mapped[int | None]
    reasoning_effort: Mapped[str | None] = mapped_column(String)

    interview: Mapped[Interview] = relationship(back_populates="phase_settings")

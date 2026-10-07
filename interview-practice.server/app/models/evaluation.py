from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import Base, uuid_pk

if TYPE_CHECKING:
    from app.models.interview import Interview


class Verdict(enum.Enum):
    hire = "hire"
    no_hire = "no_hire"


class StarCompleteness(enum.Enum):
    strong = "strong"
    partial = "partial"
    weak = "weak"


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = uuid_pk()
    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), unique=True
    )
    verdict: Mapped[Verdict] = mapped_column(Enum(Verdict))
    reasoning: Mapped[str] = mapped_column(Text)
    strengths: Mapped[str] = mapped_column(Text)  # one per line
    weaknesses: Mapped[str] = mapped_column(Text)  # one per line
    improvement_suggestions: Mapped[str] = mapped_column(Text)
    # STAR breakdown, aggregated across the whole interview
    star_situation: Mapped[str] = mapped_column(Text)
    star_task: Mapped[str] = mapped_column(Text)
    star_action: Mapped[str] = mapped_column(Text)
    star_result: Mapped[str] = mapped_column(Text)
    star_completeness: Mapped[StarCompleteness] = mapped_column(Enum(StarCompleteness))
    incomplete: Mapped[bool] = mapped_column(Boolean, server_default=false())
    model_used: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    interview: Mapped[Interview] = relationship(back_populates="evaluation")

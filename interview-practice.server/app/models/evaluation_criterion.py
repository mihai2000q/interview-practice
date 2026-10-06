from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import Base, uuid_pk
from app.models.interview_question import InterviewCategory

if TYPE_CHECKING:
    from app.models.interview import Interview


class EvaluationCriterion(Base):
    """One of an Interview's Evaluation criteria (phase 2)."""

    __tablename__ = "evaluation_criteria"
    __table_args__ = (UniqueConstraint("interview_id", "sequence"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE")
    )
    sequence: Mapped[int]
    category: Mapped[InterviewCategory] = mapped_column(Enum(InterviewCategory))
    criterion: Mapped[str] = mapped_column(Text)

    interview: Mapped[Interview] = relationship(back_populates="evaluation_criteria")

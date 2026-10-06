from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import Base, uuid_pk

if TYPE_CHECKING:
    from app.models.interview import Interview


class MessagePhase(enum.Enum):
    qa = "qa"
    ask_back = "ask_back"


class MessageRole(enum.Enum):
    interviewer = "interviewer"
    candidate = "candidate"


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_interview_id_sequence", "interview_id", "sequence"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE")
    )
    phase: Mapped[MessagePhase] = mapped_column(Enum(MessagePhase))
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    helper_text: Mapped[str | None] = mapped_column(Text)
    sequence: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    interview: Mapped[Interview] = relationship(back_populates="messages")

    @property
    def is_question(self) -> bool:
        """An interviewer's Q&A question (follow-ups included), as opposed to a
        candidate message or the ask-back phase."""
        return self.role is MessageRole.interviewer and self.phase is MessagePhase.qa

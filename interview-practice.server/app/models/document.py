from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import Base, uuid_pk


class DocumentType(enum.Enum):
    cv = "cv"
    cover_letter = "cover_letter"
    job_description = "job_description"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))
    name: Mapped[str] = mapped_column(String)
    raw_text: Mapped[str] = mapped_column(Text)
    source_filename: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    saved: Mapped[bool] = mapped_column(Boolean, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analysis: Mapped[DocumentAnalysis | None] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def analysis_model(self) -> str | None:
        """The model that produced its cached analysis, or None if it has none."""
        return self.analysis.model if self.analysis is not None else None


class DocumentAnalysis(Base):
    """What phase 1 extracted from a Document, cached for reuse (ADR 0012)."""

    __tablename__ = "document_analyses"

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), unique=True
    )
    # The model that produced it: an Interview using a different one re-analyzes.
    model: Mapped[str] = mapped_column(String)
    domain: Mapped[str | None] = mapped_column(String)
    company_name: Mapped[str | None] = mapped_column(String)
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]")
    )
    likely_topics: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped[Document] = relationship(back_populates="analysis")

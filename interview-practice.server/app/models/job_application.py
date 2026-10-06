from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import Base, uuid_pk

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.interview import Interview


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_name: Mapped[str | None] = mapped_column(String)
    job_title: Mapped[str] = mapped_column(String)
    job_description_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    cv_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    cover_letter_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )
    progress_score: Mapped[int | None]
    progress_summary: Mapped[str | None] = mapped_column(Text)
    # Fingerprint of the Evaluations the pair above was built from (ADR 0015).
    progress_basis: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job_description_document: Mapped[Document | None] = relationship(
        foreign_keys=[job_description_document_id]
    )
    cv_document: Mapped[Document | None] = relationship(foreign_keys=[cv_document_id])
    cover_letter_document: Mapped[Document | None] = relationship(
        foreign_keys=[cover_letter_document_id]
    )
    # Deleting an application deletes its interviews (ADR 0008)
    interviews: Mapped[list[Interview]] = relationship(
        back_populates="job_application",
        order_by="Interview.created_at",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

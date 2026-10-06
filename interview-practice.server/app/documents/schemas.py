import uuid
from datetime import datetime

from app.models import DocumentType
from app.serialization import ApiModel, ShortText


class DocumentPublic(ApiModel):
    """Response shape. Omits `raw_text` (large) and `file_path` (a server path)."""

    id: uuid.UUID
    type: DocumentType
    name: str
    source_filename: str
    saved: bool
    analysis_model: str | None
    created_at: datetime


class DocumentAnalysisPublic(ApiModel):
    """Response of `PUT /api/documents/:id/analysis`."""

    model: str
    domain: str | None
    company_name: str | None
    skills: list[str]
    likely_topics: list[str]


class DocumentListQuery(ApiModel):
    type: DocumentType | None = None


class DocumentCreateForm(ApiModel):
    """The non-file fields of the multipart upload."""

    type: DocumentType
    name: ShortText | None = None
    save: bool


class DocumentUpdate(ApiModel):
    """PATCH body: rename and/or change whether the Document is kept in the library."""

    name: ShortText | None = None
    saved: bool | None = None

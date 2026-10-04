import uuid
from dataclasses import dataclass
from pathlib import Path

from app.documents.shared import file_on_disk, get_document_or_404
from app.errors.exceptions import NotFoundError


@dataclass(frozen=True)
class DocumentFile:
    path: Path
    download_name: str


def download_document(document_id: uuid.UUID) -> DocumentFile:
    """The original uploaded file and the name to offer it under."""
    document = get_document_or_404(document_id)
    path = file_on_disk(document)
    if not path.is_file():
        raise NotFoundError("The stored file is missing.")
    return DocumentFile(path=path, download_name=document.source_filename)

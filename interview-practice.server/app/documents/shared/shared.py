"""Helpers shared by several documents use cases."""

import uuid
from pathlib import Path

from app.errors.exceptions import NotFoundError
from app.extensions import db
from app.models import Document
from app.paths import instance_dir


def get_document_or_404(document_id: uuid.UUID) -> Document:
    document = db.session.get(Document, document_id)
    if document is None:
        raise NotFoundError("Document not found.")
    return document


def file_on_disk(document: Document) -> Path:
    # file_path is stored relative to the instance folder so it survives moving
    # the app between machines/containers.
    return instance_dir() / document.file_path

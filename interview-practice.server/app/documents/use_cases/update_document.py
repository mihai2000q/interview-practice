import uuid

from app.documents.schemas import DocumentUpdate
from app.documents.shared import get_document_or_404
from app.errors.exceptions import BadRequestError
from app.extensions import db
from app.models import Document


def update_document(document_id: uuid.UUID, body: DocumentUpdate) -> Document:
    """Rename a Document and/or change whether it is kept in the library."""
    if body.name is None and body.saved is None:
        raise BadRequestError("Provide a name or a saved value to update.")
    document = get_document_or_404(document_id)
    if body.name is not None:
        document.name = body.name
    if body.saved is not None:
        document.saved = body.saved
    db.session.commit()
    return document

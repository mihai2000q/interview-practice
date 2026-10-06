import uuid

from app.documents.shared import file_on_disk, get_document_or_404
from app.extensions import db


def delete_document(document_id: uuid.UUID) -> None:
    document = get_document_or_404(document_id)
    path = file_on_disk(document)
    db.session.delete(document)
    db.session.commit()
    path.unlink(missing_ok=True)

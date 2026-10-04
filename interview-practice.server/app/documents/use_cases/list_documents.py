from sqlalchemy import select

from app.documents.schemas import DocumentListQuery
from app.extensions import db
from app.models import Document


def list_documents(query: DocumentListQuery) -> list[Document]:
    """The saved Documents, newest first, optionally of one type."""
    statement = (
        select(Document)
        .where(Document.saved.is_(True))
        .order_by(Document.created_at.desc())
    )
    if query.type is not None:
        statement = statement.where(Document.type == query.type)
    return list(db.session.scalars(statement))

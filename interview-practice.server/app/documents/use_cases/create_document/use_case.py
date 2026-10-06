import uuid
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.documents.schemas import DocumentCreateForm
from app.documents.use_cases.create_document.parsing import (
    PdfParseError,
    extract_pdf_text,
)
from app.errors.exceptions import (
    BadRequestError,
    FileTooLargeError,
    UnprocessableFileError,
)
from app.extensions import db
from app.llm.guard import MAX_DOCUMENT_CHARS, check_text
from app.models import Document
from app.paths import instance_dir

UPLOAD_SUBDIR = Path("uploads") / "documents"


def create_document(form: DocumentCreateForm, upload: FileStorage | None) -> Document:
    """Validate an uploaded PDF, read its text, keep the file, store the Document."""
    if upload is None or not upload.filename:
        raise BadRequestError("A PDF file is required.")
    source_filename = Path(upload.filename).name[:255]
    if not source_filename.lower().endswith(".pdf"):
        raise BadRequestError("Only PDF files are supported.")

    max_bytes: int = current_app.config["MAX_UPLOAD_BYTES"]
    data = upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise FileTooLargeError(
            f"Files are limited to {max_bytes // (1024 * 1024)} MB."
        )
    try:
        raw_text = extract_pdf_text(data)
    except PdfParseError as exc:
        raise UnprocessableFileError(str(exc)) from exc
    # the text goes into prompts later, so vet it before anything is stored
    check_text(raw_text, max_length=MAX_DOCUMENT_CHARS)

    # save locally
    relative_path = UPLOAD_SUBDIR / f"{uuid.uuid4()}.pdf"
    absolute_path = instance_dir() / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(data)

    # persist
    document = Document(
        type=form.type,
        name=form.name or source_filename,
        raw_text=raw_text,
        source_filename=source_filename,
        file_path=str(relative_path),
        saved=form.save,
    )
    db.session.add(document)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        absolute_path.unlink(missing_ok=True)  # cleanup
        raise
    return document

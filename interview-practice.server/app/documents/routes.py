import uuid
from pathlib import Path

from flask import current_app, jsonify, request, send_file
from flask.typing import ResponseReturnValue
from sqlalchemy import select
from sqlalchemy.orm.exc import ObjectDeletedError

from app.documents import documents_bp
from app.documents.analysis import ensure_analyses
from app.documents.parsing import PdfParseError, extract_pdf_text
from app.documents.schemas import (
    DocumentAnalysisPublic,
    DocumentCreateForm,
    DocumentListQuery,
    DocumentPublic,
    DocumentUpdate,
)
from app.errors.exceptions import (
    BadRequestError,
    FileTooLargeError,
    NotFoundError,
    UnprocessableFileError,
)
from app.extensions import db
from app.interviews.model_rules import DEFAULT_INTERVIEW_MODEL
from app.llm.factory import get_llm_client
from app.llm.guard import MAX_DOCUMENT_CHARS, check_text
from app.llm.openrouter import CompletionSettings
from app.models import Document
from app.paths import instance_dir
from app.serialization import to_json, to_json_list

UPLOAD_SUBDIR = Path("uploads") / "documents"


def _get_document_or_404(document_id: uuid.UUID) -> Document:
    document = db.session.get(Document, document_id)
    if document is None:
        raise NotFoundError("Document not found.")
    return document


def _file_on_disk(document: Document) -> Path:
    # file_path is stored relative to the instance folder so it survives moving
    # the app between machines/containers.
    return instance_dir() / document.file_path


@documents_bp.get("")
def list_documents() -> ResponseReturnValue:
    query = DocumentListQuery.model_validate(request.args.to_dict())
    statement = (
        select(Document)
        .where(Document.saved.is_(True))
        .order_by(Document.created_at.desc())
    )
    if query.type is not None:
        statement = statement.where(Document.type == query.type)
    documents = db.session.scalars(statement)
    return jsonify(to_json_list(DocumentPublic, documents))


@documents_bp.post("")
def create_document() -> ResponseReturnValue:
    form = DocumentCreateForm.model_validate(request.form.to_dict())

    # validation
    upload = request.files.get("file")
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

    return jsonify(to_json(DocumentPublic, document)), 201


@documents_bp.put("/<uuid:document_id>/analysis")
def analyze_document(document_id: uuid.UUID) -> ResponseReturnValue:
    """Run phase 1 on the Document now, so Create Interview can reuse the result.

    Idempotent: with a cached analysis from the default model it
    answers without calling the LLM. An Interview that overrides the `jd_analysis`
    model, or a Document with no analysis, is (re-)analysed at creation instead.
    """
    document = _get_document_or_404(document_id)
    ensure_analyses(
        get_llm_client(), DEFAULT_INTERVIEW_MODEL, CompletionSettings(), [document]
    )
    try:
        analysis = document.analysis
    except ObjectDeletedError as exc:
        # Removed while the LLM call ran (the candidate deleted the attachment).
        raise NotFoundError("Document not found.") from exc
    return jsonify(to_json(DocumentAnalysisPublic, analysis))


@documents_bp.get("/<uuid:document_id>/download")
def download_document(document_id: uuid.UUID) -> ResponseReturnValue:
    document = _get_document_or_404(document_id)
    path = _file_on_disk(document)
    if not path.is_file():
        raise NotFoundError("The stored file is missing.")
    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=document.source_filename,
    )


@documents_bp.patch("/<uuid:document_id>")
def update_document(document_id: uuid.UUID) -> ResponseReturnValue:
    body = DocumentUpdate.model_validate(request.get_json(silent=True) or {})
    if body.name is None and body.saved is None:
        raise BadRequestError("Provide a name or a saved value to update.")
    document = _get_document_or_404(document_id)
    if body.name is not None:
        document.name = body.name
    if body.saved is not None:
        document.saved = body.saved
    db.session.commit()
    return jsonify(to_json(DocumentPublic, document))


@documents_bp.delete("/<uuid:document_id>")
def delete_document(document_id: uuid.UUID) -> ResponseReturnValue:
    document = _get_document_or_404(document_id)
    path = _file_on_disk(document)
    db.session.delete(document)
    db.session.commit()
    path.unlink(missing_ok=True)
    return "", 204

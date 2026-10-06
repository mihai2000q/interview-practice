"""HTTP layer of the documents API: read the request, call a use case, build the reply.

The logic of each endpoint lives in `app/documents/use_cases/`.
"""

import uuid

from flask import jsonify, request, send_file
from flask.typing import ResponseReturnValue

from app.documents import documents_bp
from app.documents.schemas import (
    DocumentAnalysisPublic,
    DocumentCreateForm,
    DocumentListQuery,
    DocumentPublic,
    DocumentUpdate,
)
from app.documents.use_cases.analyze_document import analyze_document
from app.documents.use_cases.create_document import create_document
from app.documents.use_cases.delete_document import delete_document
from app.documents.use_cases.download_document import download_document
from app.documents.use_cases.list_documents import list_documents
from app.documents.use_cases.update_document import update_document
from app.llm.schemas import PhaseSettings
from app.serialization import to_json, to_json_list


@documents_bp.get("")
def get_documents() -> ResponseReturnValue:
    query = DocumentListQuery.model_validate(request.args.to_dict())
    return jsonify(to_json_list(DocumentPublic, list_documents(query)))


@documents_bp.post("")
def post_documents() -> ResponseReturnValue:
    form = DocumentCreateForm.model_validate(request.form.to_dict())
    document = create_document(form, request.files.get("file"))
    return jsonify(to_json(DocumentPublic, document)), 201


@documents_bp.put("/<uuid:document_id>/analysis")
def put_document_analysis(document_id: uuid.UUID) -> ResponseReturnValue:
    settings = PhaseSettings.model_validate(request.get_json(silent=True) or {})
    return jsonify(
        to_json(DocumentAnalysisPublic, analyze_document(document_id, settings))
    )


@documents_bp.get("/<uuid:document_id>/download")
def get_document_download(document_id: uuid.UUID) -> ResponseReturnValue:
    file = download_document(document_id)
    return send_file(
        file.path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=file.download_name,
    )


@documents_bp.patch("/<uuid:document_id>")
def patch_document_by_id(document_id: uuid.UUID) -> ResponseReturnValue:
    body = DocumentUpdate.model_validate(request.get_json(silent=True) or {})
    return jsonify(to_json(DocumentPublic, update_document(document_id, body)))


@documents_bp.delete("/<uuid:document_id>")
def delete_document_by_id(document_id: uuid.UUID) -> ResponseReturnValue:
    delete_document(document_id)
    return "", 204

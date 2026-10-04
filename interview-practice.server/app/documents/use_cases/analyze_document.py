import uuid

from sqlalchemy.orm.exc import ObjectDeletedError

from app.documents.shared import get_document_or_404
from app.errors.exceptions import NotFoundError
from app.llm.defaults import DEFAULT_INTERVIEW_MODEL
from app.llm.factory import get_llm_client
from app.llm.openrouter import CompletionSettings
from app.models import DocumentAnalysis
from app.services.document_analysis import ensure_analyses


def analyze_document(document_id: uuid.UUID) -> DocumentAnalysis:
    """Run phase 1 on the Document now, so Create Interview can reuse the result.

    Idempotent: with a cached analysis from the default model it answers without
    calling the LLM. An Interview that overrides the `jd_analysis` model, or a Document
    with no analysis, is (re-)analysed at creation instead.
    """
    document = get_document_or_404(document_id)
    ensure_analyses(
        get_llm_client(), DEFAULT_INTERVIEW_MODEL, CompletionSettings(), [document]
    )
    # A Document removed while the LLM call ran (the candidate deleted the attachment)
    # takes its analysis with it.
    try:
        analysis = document.analysis
    except ObjectDeletedError as exc:
        raise NotFoundError("Document not found.") from exc
    if analysis is None:
        raise NotFoundError("Document not found.")
    return analysis

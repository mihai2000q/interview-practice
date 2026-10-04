import uuid

from app.documents.shared import get_document_or_404
from app.llm.factory import get_llm_client
from app.llm.phase_settings import phase_config
from app.models import DocumentAnalysis, GenerationPhase
from app.services.document_analysis import analyse_document


def analyze_document(document_id: uuid.UUID) -> DocumentAnalysis:
    """Run phase 1 on the Document now, so Create Interview can reuse the result.

    Idempotent: with a cached analysis from the default model it answers without
    calling the LLM. An Interview that overrides the `jd_analysis` model, or a Document
    with no analysis, is (re-)analysed at creation instead.
    """
    document = get_document_or_404(document_id)
    model, settings = phase_config(GenerationPhase.jd_analysis)
    return analyse_document(get_llm_client(), model, settings, document)

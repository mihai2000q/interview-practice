import uuid

from app.documents.shared import get_document_or_404
from app.llm.factory import get_llm_client
from app.llm.phase_settings import ensure_overrides_allowed, phase_config
from app.llm.schemas import PhaseSettings
from app.models import DocumentAnalysis, GenerationPhase
from app.services import document_analysis
from app.services.preferences import load_preferences


def analyze_document(
    document_id: uuid.UUID, settings: PhaseSettings | None = None
) -> DocumentAnalysis:
    """Run phase 1 on the Document now, so Create Interview can reuse the result.

    `settings` is the `jd_analysis` override the Interview will be created with, if any;
    without it the default model is used. Idempotent: with a cached analysis from that
    model it answers without calling the LLM. A Document with no analysis from the model
    the Interview ends up using is (re-)analyzed at creation instead.
    """
    document = get_document_or_404(document_id)
    row = settings.to_row(GenerationPhase.jd_analysis) if settings else None
    ensure_overrides_allowed([row] if row else [])
    model, completion = phase_config(
        GenerationPhase.jd_analysis, [row] if row else [], load_preferences()
    )
    return document_analysis.analyze_document(
        get_llm_client(), model, completion, document
    )

import uuid

from app.documents.shared import get_document_or_404
from app.interviews.schemas import PhaseSettings
from app.llm.factory import get_llm_client
from app.llm.phase_settings import phase_config
from app.models import DocumentAnalysis, GenerationPhase, InterviewPhaseSettings
from app.services.document_analysis import analyse_document


def analyze_document(
    document_id: uuid.UUID, settings: PhaseSettings | None = None
) -> DocumentAnalysis:
    """Run phase 1 on the Document now, so Create Interview can reuse the result.

    `settings` is the `jd_analysis` override the Interview will be created with, if any;
    without it the default model is used. Idempotent: with a cached analysis from that
    model it answers without calling the LLM. A Document with no analysis from the model
    the Interview ends up using is (re-)analysed at creation instead.
    """
    document = get_document_or_404(document_id)
    overrides = []
    if settings is not None:
        fields = settings.model_dump(by_alias=False, exclude_none=True)
        if fields:
            overrides.append(
                InterviewPhaseSettings(phase=GenerationPhase.jd_analysis, **fields)
            )
    model, completion = phase_config(GenerationPhase.jd_analysis, overrides)
    return analyse_document(get_llm_client(), model, completion, document)

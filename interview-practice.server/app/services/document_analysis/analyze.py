"""Analyzing Documents: the cached `DocumentAnalysis` rows and what callers get back.

An analysis belongs to its Document and is reused by every later Interview until a
different model is chosen (ADR 0012). Callers never read `Document.analysis` or handle a
Document deleted while the model ran: they get the analysis, or a ready-made context.
"""

from collections.abc import Sequence
from functools import partial

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import ObjectDeletedError

from app.errors.exceptions import NotFoundError
from app.extensions import db
from app.llm.concurrency import fan_out
from app.llm.openrouter import CompletionSettings, OpenRouterClient
from app.models import Document, DocumentAnalysis
from app.services.document_analysis.context import JobContext
from app.services.document_analysis.extraction import extract


def analyze_document(
    client: OpenRouterClient,
    model: str,
    settings: CompletionSettings,
    document: Document,
) -> DocumentAnalysis:
    """The Document's analysis by `model`, running the model only if it has none.

    A Document removed while the model ran takes its analysis with it: `NotFoundError`.
    """
    _ensure_analyses(client, model, settings, [document])
    try:
        analysis = document.analysis
    except ObjectDeletedError as exc:
        raise NotFoundError("Document not found.") from exc
    if analysis is None:
        raise NotFoundError("Document not found.")
    return analysis


def analyze_job_documents(
    client: OpenRouterClient,
    model: str,
    settings: CompletionSettings,
    *,
    job_description: Document | None,
    cv: Document | None,
    cover_letter: Document | None,
) -> JobContext:
    """Analyze whichever of the three Documents exist and resolve what they say."""
    documents = [d for d in (job_description, cv, cover_letter) if d is not None]
    _ensure_analyses(client, model, settings, documents)
    try:
        return JobContext.from_documents(
            job_description=job_description, cv=cv, cover_letter=cover_letter
        )
    except ObjectDeletedError as exc:
        raise NotFoundError("Document not found.") from exc


def _ensure_analyses(
    client: OpenRouterClient,
    model: str,
    settings: CompletionSettings,
    documents: Sequence[Document],
) -> None:
    """Make sure each Document has a `DocumentAnalysis` made by `model`.

    Documents already analyzed by `model` are skipped; the rest are analyzed in
    parallel and their rows created or overwritten, then committed straight away: an
    analysis is valid on its own, so it stays even if a later step of the request fails.

    Two requests can analyze the same Document at once (a canceled client request keeps
    running on the server while the candidate submits). The first to commit wins; the
    other finds the row already there, which is just as good.
    """
    stale = [d for d in documents if d.analysis is None or d.analysis.model != model]
    if not stale:
        return
    results = fan_out(
        [partial(extract, client, model, settings, d.type, d.raw_text) for d in stale]
    )
    for document, result in zip(stale, results, strict=True):
        analysis = document.analysis or DocumentAnalysis()
        analysis.model = model
        analysis.domain = result.domain
        analysis.company_name = result.company_name
        analysis.skills = result.skills
        analysis.likely_topics = result.likely_topics
        analysis.created_at = func.now()
        document.analysis = analysis
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

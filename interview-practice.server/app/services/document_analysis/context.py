"""What the analyses of a job description, CV and cover letter say, resolved for use.

Pure: reads the analyses already stored on the Documents and calls no model. Shared by
the interview plan and the coaching hint, so the rules and the rendering exist once.
"""

from dataclasses import dataclass

from app.llm.guard import fence
from app.models import Document, DocumentAnalysis


def _render(label: str, analysis: DocumentAnalysis | None) -> str:
    """Skills and topics as a fenced prompt block, or nothing if there are none."""
    if analysis is None or not (analysis.skills or analysis.likely_topics):
        return ""
    skills = ", ".join(analysis.skills) or "(none)"
    topics = ", ".join(analysis.likely_topics) or "(none)"
    return fence(label, f"skills: {skills}\ntopics: {topics}")


def _analysis(document: Document | None) -> DocumentAnalysis | None:
    return document.analysis if document is not None else None


@dataclass(frozen=True)
class JobContext:
    company_name: str | None  # the job description's, else the cover letter's
    # A proposal: the job description's, else the cover letter's, else the CV's. A CV
    # may be another field than the position, so the plan checks it against the job.
    domain: str | None
    job_text: str  # the job description's skills and topics, fenced; "" if none
    candidate_text: str  # the CV's skills and topics, fenced; "" if none

    @classmethod
    def from_documents(
        cls,
        *,
        job_description: Document | None,
        cv: Document | None,
        cover_letter: Document | None,
    ) -> "JobContext":
        job = _analysis(job_description)
        candidate = _analysis(cv)
        letter = _analysis(cover_letter)
        return cls(
            company_name=(job.company_name if job else None)
            or (letter.company_name if letter else None),
            domain=(job.domain if job else None)
            or (letter.domain if letter else None)
            or (candidate.domain if candidate else None),
            job_text=_render("job_analysis", job),
            candidate_text=_render("candidate_analysis", candidate),
        )

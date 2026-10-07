"""What the three plan calls are told about the Interview.

Everything the candidate or a Document supplied is fenced as data (see
`app.llm.guard.fence`); the system prompts say never to follow instructions inside the
tags.
"""

from app.interviews.schemas import InterviewCreate
from app.llm.guard import fence
from app.services.document_analysis import JobContext


def company_of(request: InterviewCreate, context: JobContext) -> str | None:
    """The company the candidate gave, else the one the documents name."""
    return request.company_name or context.company_name


def setup_block(request: InterviewCreate, context: JobContext) -> str:
    lines = [
        f"job_title: {request.job_title}",
        f"seniority: {request.seniority}",
        f"difficulty: {request.difficulty.value}",
        f"interview_type: {request.interview_type}",
        f"interviewer_role: {request.interviewer_role}",
        f"tone: {request.tone}",
    ]
    company = company_of(request, context)
    if company:
        lines.append(f"company: {company}")
    if context.domain:
        lines.append(
            "domain_from_documents (may be another field than the position: use it "
            "only if it fits job_title and company, otherwise ignore it): "
            f"{context.domain}"
        )
    return fence("interview_setup", "\n".join(lines))


def setup_and_analyses(request: InterviewCreate, context: JobContext) -> str:
    """The setup plus the skills and topics of the job description and the CV."""
    parts = [setup_block(request, context), context.job_text, context.candidate_text]
    return "\n\n".join(part for part in parts if part)

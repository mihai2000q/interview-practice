"""What the evaluation and the review are told about the Interview.

The transcript holds the candidate's own words, so everything is fenced as data (see
`app.llm.guard.fence`) and the system prompts say never to follow instructions inside
the tags. A message is flattened to one line so its text cannot imitate another
message's header.
"""

from app.llm.guard import fence
from app.models import Interview, MessageRole


def setup_block(interview: Interview) -> str:
    lines = [
        f"job_title: {interview.job_title}",
        f"seniority: {interview.seniority}",
        f"domain: {interview.domain}",
        f"difficulty: {interview.difficulty.value}",
        f"interview_type: {interview.interview_type}",
        f"interviewer_role: {interview.interviewer_role}",
        f"tone: {interview.tone}",
        f"target_question_count: {interview.target_question_count}",
    ]
    if interview.company_name:
        lines.append(f"company: {interview.company_name}")
    return fence("interview_setup", "\n".join(lines))


def transcript_block(interview: Interview) -> str:
    """The messages in order, each tagged with its number, speaker and phase."""
    lines = [
        f"{m.sequence}. {m.role.value} ({m.phase.value}): {' '.join(m.content.split())}"
        for m in interview.messages
    ]
    return fence("transcript", "\n".join(lines))


def has_candidate_message(interview: Interview) -> bool:
    return any(m.role is MessageRole.candidate for m in interview.messages)

"""What several test modules need: a model client on a fake transport, and an unsaved
Interview. No database anywhere."""

import json
from collections.abc import Callable, Collection
from typing import Any

import httpx

from app.llm.openrouter import OpenRouterClient
from app.models import (
    Difficulty,
    Document,
    DocumentAnalysis,
    DocumentType,
    Interview,
    InterviewCategory,
    InterviewQuestion,
    InterviewStatus,
    Message,
    MessagePhase,
    MessageRole,
    ResponseStyle,
)


def fake_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> OpenRouterClient:
    """The real client, talking to `handler` instead of the network."""
    return OpenRouterClient(
        base_url="https://llm.test",
        api_key=lambda: "k",
        transport=httpx.MockTransport(handler),
    )


def chat_response(content: object) -> httpx.Response:
    """A successful chat completion whose message is `content` (JSON-encoded unless it
    is already text)."""
    text = content if isinstance(content, str) else json.dumps(content)
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def _document(kind: DocumentType, text: str) -> Document:
    return Document(
        type=kind, name="n", raw_text=text, source_filename="f", file_path="x"
    )


def build_interview(
    *,
    target: int = 3,
    helpers: bool = False,
    messages: list[tuple[MessageRole, MessagePhase]] | None = None,
    clarifications: Collection[int] = (),
    job_analysis: bool = False,
    cv: str | None = None,
    cover_letter: str | None = None,
    **fields: Any,
) -> Interview:
    """An unsaved Interview. `messages` are (role, phase) pairs, numbered from 1,
    those whose number is in `clarifications` flagged as clarifications;
    `job_analysis` attaches an analyzed job description; other fields override."""
    job_description = None
    if job_analysis:
        job_description = _document(DocumentType.job_description, "job ad")
        job_description.analysis = DocumentAnalysis(
            model="m", skills=["Python"], likely_topics=["caching"]
        )
    interview = Interview(
        **{
            "job_title": "Backend Dev",
            "seniority": "senior",
            "domain": "backend",
            "difficulty": Difficulty.easy,
            "tone": "neutral",
            "interview_type": "technical",
            "interviewer_role": "recruiter",
            "target_question_count": target,
            "status": InterviewStatus.in_progress,
            "persona_name": "Dana",
            "persona_title": "Recruiter",
            "persona_backstory": "Recruited for years.",
            "coaching_helpers_enabled": helpers,
            "response_style": ResponseStyle.concise,
            "questions": [
                InterviewQuestion(category=InterviewCategory.technical, question="q")
            ],
            "job_description_document": job_description,
            "cv_document": cv and _document(DocumentType.cv, cv),
            "cover_letter_document": cover_letter
            and _document(DocumentType.cover_letter, cover_letter),
            **fields,
        }
    )
    for number, (role, phase) in enumerate(messages or [], start=1):
        interview.messages.append(
            Message(
                role=role,
                phase=phase,
                content=f"m{number}",
                sequence=number,
                is_clarification=number in clarifications,
            )
        )
    return interview

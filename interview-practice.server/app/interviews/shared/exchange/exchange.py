"""The interviewer's side of the conversation as one module (ADR 0013).

An exchange is the candidate's reply and the interviewer's answer to it; the opening
exchange has no reply. `run_exchange` does the slow part (pacing, the model, the
coaching hint) and changes nothing; the caller decides when it is safe to `apply_to`
the Interview, then commits. A failed or dropped exchange therefore leaves nothing
behind.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.interviews.shared.exchange.conversation import ask_interviewer, phase_after
from app.interviews.shared.exchange.helper import generate_helper
from app.interviews.shared.exchange.pacing import (
    ExchangeKind,
    decide_kind,
    questions_asked,
)
from app.llm.openrouter import CompletionSettings, OpenRouterClient
from app.models import (
    Interview,
    InterviewStatus,
    Message,
    MessagePhase,
    MessageRole,
)
from app.services.interview_lifecycle import end


@dataclass(frozen=True)
class AppliedExchange:
    """The Messages an exchange added; `candidate_message` is None for the opening."""

    candidate_message: Message | None
    interviewer_message: Message


@dataclass(frozen=True)
class ExchangeOutcome:
    """What an exchange will add to the Interview, not yet added."""

    reply: str | None
    candidate_phase: MessagePhase
    interviewer_content: str
    interviewer_phase: MessagePhase
    helper_text: str | None
    completes_interview: bool

    def apply_to(self, interview: Interview) -> AppliedExchange:
        """Add the Messages, number them, record the activity, close the Interview if
        this exchange ends it. The caller owns the transaction."""
        count = len(interview.messages)
        candidate = None
        if self.reply is not None:
            count += 1
            candidate = Message(
                role=MessageRole.candidate,
                phase=self.candidate_phase,
                content=self.reply,
                sequence=count,
            )
        interviewer = Message(
            role=MessageRole.interviewer,
            phase=self.interviewer_phase,
            content=self.interviewer_content,
            helper_text=self.helper_text,
            sequence=count + 1,
        )
        interview.messages.extend(m for m in (candidate, interviewer) if m is not None)
        interview.last_activity_at = datetime.now(UTC)
        if self.completes_interview:
            end(interview, InterviewStatus.completed)
        return AppliedExchange(
            candidate_message=candidate, interviewer_message=interviewer
        )


def run_exchange(
    client: OpenRouterClient,
    model: str,
    settings: CompletionSettings,
    interview: Interview,
    reply: str | None,
) -> ExchangeOutcome:
    """Work out and ask for the interviewer's side of the next exchange.

    `reply` is the candidate's message, or None to open an Interview that has no
    messages yet. Reads the Interview; changes nothing.
    """
    kind = decide_kind(interview, has_reply=reply is not None)
    transcript = [(m.role, m.content) for m in interview.messages]
    if reply is not None:
        transcript.append((MessageRole.candidate, reply))
    result = ask_interviewer(
        client,
        model,
        settings,
        interview,
        transcript,
        kind,
        questions_asked(interview),
    )
    interviewer_phase = phase_after(kind, result)
    # A coaching hint accompanies each Q&A question, not the wrap-up or ask-back.
    helper = (
        generate_helper(client, model, settings, interview, result.message)
        if interview.coaching_helpers_enabled and interviewer_phase is MessagePhase.qa
        else None
    )
    return ExchangeOutcome(
        reply=reply,
        candidate_phase=interview.phase,
        interviewer_content=result.message,
        interviewer_phase=interviewer_phase,
        helper_text=helper,
        completes_interview=(
            kind in (ExchangeKind.answer, ExchangeKind.close_interview) and result.done
        ),
    )

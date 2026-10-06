"""Pacing: what kind of exchange comes next, decided from the Interview's state alone.

Pure rules, no model and no database: the server paces the interview so the model can't
run it past its budget (ADR 0013).
"""

from enum import Enum

from app.models import Interview, MessagePhase, MessageRole

# A real interview lets the candidate ask a handful of questions, not an endless Q&A.
MAX_ASK_BACK_QUESTIONS = 5


class ExchangeKind(Enum):
    """What the interviewer has to do in this exchange."""

    open = "open"  # greet the candidate and ask the first question
    ask = "ask"  # ask the next question; may end the questions early
    close_questions = "close_questions"  # questions are over: invite the candidate's
    answer = "answer"  # ask-back: answer the candidate; may close the interview
    close_interview = "close_interview"  # ask-back is over: thank them and close


def questions_asked(interview: Interview) -> int:
    """Interviewer messages in the Q&A phase so far (follow-ups count)."""
    return sum(m.is_question for m in interview.messages)


def decide_kind(interview: Interview, *, has_reply: bool) -> ExchangeKind:
    """The kind of exchange that follows, given whether the candidate just replied."""
    if not has_reply:
        if interview.messages:
            raise ValueError("Only an Interview with no messages can be opened.")
        return ExchangeKind.open
    if interview.phase is MessagePhase.qa:
        # Once the budget is spent the interviewer must wrap up, whatever the model
        # would prefer.
        if questions_asked(interview) >= interview.target_question_count:
            return ExchangeKind.close_questions
        return ExchangeKind.ask
    # `1 +` counts the reply being answered, which isn't stored yet.
    candidate_questions = 1 + sum(
        m.role is MessageRole.candidate and m.phase is MessagePhase.ask_back
        for m in interview.messages
    )
    if candidate_questions >= MAX_ASK_BACK_QUESTIONS:
        return ExchangeKind.close_interview
    return ExchangeKind.answer

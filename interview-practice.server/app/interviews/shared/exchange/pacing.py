"""Pacing: what kind of exchange comes next, decided from the Interview's state alone.

Pure rules, no model and no database: the server paces the interview so the model can't
run it past its budget (ADR 0013).
"""

from enum import Enum

from app.models import Interview, MessagePhase, MessageRole

# A real interview lets the candidate ask a handful of questions, not an endless Q&A.
MAX_ASK_BACK_QUESTIONS = 5
# How many times in a row the interviewer may stay on one question (to answer what the
# candidate asked back, or to ask for clarification) before accepting the answer.
MAX_CLARIFICATIONS = 2


class ExchangeKind(Enum):
    """What the interviewer has to do in this exchange."""

    open = "open"  # greet the candidate and ask the first question
    ask = "ask"  # ask the next question; may end the questions early
    close_questions = "close_questions"  # questions are over: invite the candidate's
    answer = "answer"  # ask-back: answer the candidate; may close the interview
    close_interview = "close_interview"  # ask-back is over: answer, thank, close


def questions_asked(interview: Interview) -> int:
    """Interviewer questions in the Q&A phase so far. Clarifications don't count."""
    return sum(m.is_question for m in interview.messages)


def clarifications_left(kind: ExchangeKind, streak: int) -> int:
    """How many more times the interviewer may stay on the question in this exchange:
    only an `ask` exchange can, and only up to `MAX_CLARIFICATIONS` in a row."""
    return max(0, MAX_CLARIFICATIONS - streak) if kind is ExchangeKind.ask else 0


def clarification_streak(interview: Interview) -> int:
    """How many interviewer messages in a row, ending the Q&A so far, stayed on one
    question instead of asking a new one."""
    streak = 0
    for message in reversed(interview.messages):
        if message.role is not MessageRole.interviewer:
            continue
        if message.phase is not MessagePhase.qa or not message.is_clarification:
            break
        streak += 1
    return streak


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
    # `1 +` counts the reply being answered, which isn't stored yet. The question that
    # reaches the cap is still answered: the same message answers it and closes.
    candidate_questions = 1 + sum(
        m.role is MessageRole.candidate and m.phase is MessagePhase.ask_back
        for m in interview.messages
    )
    if candidate_questions >= MAX_ASK_BACK_QUESTIONS:
        return ExchangeKind.close_interview
    return ExchangeKind.answer

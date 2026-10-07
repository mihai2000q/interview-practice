"""The interviewer's side of the conversation (ADR 0013): pacing, the reply contract
and applying an exchange. No database: Interviews are built unsaved and the real
client talks to a fake transport."""

import httpx
import pytest

from app.errors.exceptions import LlmUpstreamError
from app.interviews.shared.exchange import run_exchange
from app.interviews.shared.exchange.conversation import build_messages
from app.interviews.shared.exchange.pacing import (
    MAX_ASK_BACK_QUESTIONS,
    MAX_CLARIFICATIONS,
    ExchangeKind,
    clarification_streak,
    decide_kind,
    questions_asked,
)
from app.llm.openrouter import CompletionSettings
from app.models import (
    Interview,
    InterviewCategory,
    InterviewQuestion,
    InterviewStatus,
    MessagePhase,
    MessageRole,
)
from tests.support import build_interview, chat_response, fake_client

QA, ASK_BACK = MessagePhase.qa, MessagePhase.ask_back
INTERVIEWER, CANDIDATE = MessageRole.interviewer, MessageRole.candidate


def qa_exchanges(count: int) -> list[tuple[MessageRole, MessagePhase]]:
    """`count` interviewer questions, each answered except the last."""
    messages: list[tuple[MessageRole, MessagePhase]] = []
    for number in range(count):
        if number:
            messages.append((CANDIDATE, QA))
        messages.append((INTERVIEWER, QA))
    return messages


# -- pacing ---------------------------------------------------------------------------


def test_opening_is_the_exchange_with_no_reply() -> None:
    assert decide_kind(build_interview(), has_reply=False) is ExchangeKind.open


def test_only_an_interview_without_messages_can_be_opened() -> None:
    with pytest.raises(ValueError):
        decide_kind(build_interview(messages=qa_exchanges(1)), has_reply=False)


@pytest.mark.parametrize(
    ("target", "asked", "expected"),
    [
        (3, 1, ExchangeKind.ask),
        (3, 2, ExchangeKind.ask),
        (3, 3, ExchangeKind.close_questions),  # budget spent: wrap up
        (1, 1, ExchangeKind.close_questions),
        (5, 4, ExchangeKind.ask),
    ],
)
def test_qa_pacing_follows_the_question_budget(
    target: int, asked: int, expected: ExchangeKind
) -> None:
    interview = build_interview(target=target, messages=qa_exchanges(asked))
    assert decide_kind(interview, has_reply=True) is expected


@pytest.mark.parametrize(
    ("candidate_questions_so_far", "expected"),
    [
        (0, ExchangeKind.answer),
        (MAX_ASK_BACK_QUESTIONS - 2, ExchangeKind.answer),
        (MAX_ASK_BACK_QUESTIONS - 1, ExchangeKind.close_interview),  # the cap
    ],
)
def test_ask_back_closes_at_the_cap(
    candidate_questions_so_far: int, expected: ExchangeKind
) -> None:
    messages = [*qa_exchanges(1), (INTERVIEWER, ASK_BACK)]
    for _ in range(candidate_questions_so_far):
        messages += [(CANDIDATE, ASK_BACK), (INTERVIEWER, ASK_BACK)]
    interview = build_interview(messages=messages)
    assert decide_kind(interview, has_reply=True) is expected


# -- a fake model ---------------------------------------------------------------------


class FakeModel:
    """Scripted replies for the interviewer; any other call is a failure."""

    def __init__(self) -> None:
        self.replies: list[dict[str, object]] = []
        self.client = fake_client(self.handle)

    def say(
        self,
        message: str,
        *,
        done: bool = False,
        clarification: bool = False,
        end_interview: bool = False,
    ) -> "FakeModel":
        self.replies.append(
            {
                "message": message,
                "done": done,
                "clarification": clarification,
                "end_interview": end_interview,
            }
        )
        return self

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert "coach helping a candidate" not in request.content.decode()
        reply = self.replies.pop(0)
        return chat_response(reply)


def run(model: FakeModel, interview: Interview, reply: str | None = "my answer"):
    return run_exchange(model.client, "m", CompletionSettings(), interview, reply)


# -- no coaching helper ---------------------------------------------------------------


def test_an_exchange_makes_no_coaching_helper_call() -> None:
    """The session page asks for the helper separately (`PUT .../helper`); the fake
    model fails the test if a helper prompt ever reaches it."""
    model = FakeModel().say("Next question?")
    interview = build_interview(helpers=True, messages=qa_exchanges(1))
    outcome = run(model, interview)
    assert outcome.interviewer_phase is QA


# -- the reply contract ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("interview", "reply", "message", "done"),
    [
        # budget spent but the model keeps asking
        (build_interview(target=1, messages=qa_exchanges(1)), "a", "One more?", False),
        # the opening must not end the phase
        (build_interview(), None, "Hi", True),
        # nothing to store
        (build_interview(messages=qa_exchanges(1)), "a", "   ", False),
    ],
)
def test_a_reply_that_breaks_the_contract_is_an_error(
    interview: Interview, reply: str | None, message: str, done: bool
) -> None:
    with pytest.raises(LlmUpstreamError):
        run(FakeModel().say(message, done=done), interview, reply)


# -- running changes nothing, applying does -------------------------------------------


def test_running_an_exchange_does_not_touch_the_interview() -> None:
    interview = build_interview(messages=qa_exchanges(1))
    run(FakeModel().say("Next question?"), interview)
    assert len(interview.messages) == 1
    assert interview.status is InterviewStatus.in_progress


def test_applying_numbers_the_messages_and_records_activity() -> None:
    interview = build_interview(messages=qa_exchanges(1))
    applied = run(FakeModel().say("Next question?"), interview).apply_to(interview)
    assert applied.candidate_message is not None
    assert applied.candidate_message.sequence == 2
    assert applied.candidate_message.phase is QA
    assert applied.interviewer_message.sequence == 3
    assert [m.sequence for m in interview.messages] == [1, 2, 3]
    assert interview.last_activity_at is not None


def test_the_opening_adds_one_message() -> None:
    interview = build_interview()
    applied = run(FakeModel().say("Hi!"), interview, reply=None).apply_to(interview)
    assert applied.candidate_message is None
    assert applied.interviewer_message.sequence == 1
    assert applied.interviewer_message.phase is QA


def test_the_wrap_up_moves_to_ask_back_without_ending_the_interview() -> None:
    interview = build_interview(target=1, messages=qa_exchanges(1))
    outcome = run(FakeModel().say("Any questions?", done=True), interview)
    outcome.apply_to(interview)
    assert interview.phase is ASK_BACK
    assert interview.status is InterviewStatus.in_progress


def finish_ask_back(interview: Interview, reply: str, model: FakeModel) -> None:
    run(model, interview, reply).apply_to(interview)


def ask_back_interview(candidate_questions: int = 0) -> Interview:
    messages = [*qa_exchanges(1), (INTERVIEWER, ASK_BACK)]
    for _ in range(candidate_questions):
        messages += [(CANDIDATE, ASK_BACK), (INTERVIEWER, ASK_BACK)]
    return build_interview(messages=messages)


def test_declining_in_ask_back_completes_the_interview() -> None:
    interview = ask_back_interview()
    finish_ask_back(interview, "No more questions", FakeModel().say("Bye!", done=True))
    assert interview.status is InterviewStatus.completed
    assert interview.ended_at is not None


def test_an_ask_back_answer_keeps_the_interview_going() -> None:
    interview = ask_back_interview()
    finish_ask_back(interview, "What's the team like?", FakeModel().say("Great."))
    assert interview.status is InterviewStatus.in_progress


def test_the_ask_back_cap_forces_the_close() -> None:
    interview = ask_back_interview(MAX_ASK_BACK_QUESTIONS - 1)
    finish_ask_back(interview, "One more", FakeModel().say("Goodbye!", done=True))
    assert interview.status is InterviewStatus.completed


def test_the_close_at_the_cap_still_answers_the_last_question() -> None:
    interview = ask_back_interview(MAX_ASK_BACK_QUESTIONS - 1)
    transcript = [(m.role, m.content) for m in interview.messages]
    system = build_messages(interview, transcript, ExchangeKind.close_interview, 1)[
        0
    ].content
    assert "Answer their last message" in system
    assert "close the interview" in system


def test_an_ask_back_close_that_keeps_going_is_an_error() -> None:
    interview = ask_back_interview(MAX_ASK_BACK_QUESTIONS - 1)
    with pytest.raises(LlmUpstreamError):
        run(FakeModel().say("Ask me more!", done=False), interview, "One more")


# -- clarifications -------------------------------------------------------------------


def with_clarifications(count: int, *, target: int = 3) -> Interview:
    """One question, then `count` clarifications of it, each after a candidate reply."""
    messages = [(INTERVIEWER, QA)]
    for _ in range(count):
        messages += [(CANDIDATE, QA), (INTERVIEWER, QA)]
    flagged = {number for number in range(3, len(messages) + 1, 2)}
    return build_interview(target=target, messages=messages, clarifications=flagged)


def test_clarifications_are_not_counted_as_questions() -> None:
    interview = with_clarifications(2, target=1)
    assert questions_asked(interview) == 1
    # One question asked against a target of one: wrap up, whatever came after it.
    assert decide_kind(interview, has_reply=True) is ExchangeKind.close_questions
    assert decide_kind(with_clarifications(2), has_reply=True) is ExchangeKind.ask


@pytest.mark.parametrize("count", [0, 1, 2])
def test_the_streak_counts_the_clarifications_ending_the_transcript(
    count: int,
) -> None:
    assert clarification_streak(with_clarifications(count)) == count


def test_a_new_question_ends_the_streak() -> None:
    interview = build_interview(
        messages=[(INTERVIEWER, QA), (CANDIDATE, QA), (INTERVIEWER, QA)] * 2,
        clarifications={3},
    )
    assert clarification_streak(interview) == 0


def test_a_clarification_is_stored_and_not_counted() -> None:
    interview = with_clarifications(0)
    model = FakeModel().say("Do you mean in production?", clarification=True)
    applied = run(model, interview).apply_to(interview)
    assert applied.interviewer_message.is_clarification
    assert not applied.interviewer_message.is_question
    assert not applied.candidate_message.is_clarification  # type: ignore[union-attr]
    assert questions_asked(interview) == 1


def test_past_the_limit_a_reply_counts_as_a_question() -> None:
    interview = with_clarifications(MAX_CLARIFICATIONS)
    model = FakeModel().say("Still unclear, say more?", clarification=True)
    applied = run(model, interview).apply_to(interview)
    assert not applied.interviewer_message.is_clarification
    assert questions_asked(interview) == 2


def test_only_an_ask_exchange_that_continues_can_be_a_clarification() -> None:
    wrapping_up = build_interview(target=1, messages=qa_exchanges(1))
    model = FakeModel().say("Any questions?", done=True, clarification=True)
    assert not run(model, wrapping_up).interviewer_is_clarification


def test_the_interviewer_is_told_not_to_follow_off_topic_tangents() -> None:
    interview = with_clarifications(0)
    transcript = [(m.role, m.content) for m in interview.messages]
    for kind in (ExchangeKind.ask, ExchangeKind.answer):
        system = build_messages(interview, transcript, kind, 1)[0].content
        assert "never ask about it or follow it up" in system


def test_the_plan_shows_core_questions_and_reserves() -> None:
    interview = build_interview(target=1)
    interview.questions.append(
        InterviewQuestion(category=InterviewCategory.behavioral, question="spare")
    )
    for number, question in enumerate(interview.questions, start=1):
        question.sequence = number
    transcript: list[tuple[MessageRole, str]] = []
    system = build_messages(interview, transcript, ExchangeKind.ask, 0)[0].content
    assert "Core:\n1. [technical] q\nReserves:\n2. [behavioral] spare" in system
    assert "end the questions" in system


def test_the_interviewer_sticks_to_the_position_and_company() -> None:
    interview = build_interview(company_name="Cafe Luna", job_title="Barista")
    system = build_messages(interview, [], ExchangeKind.ask, 0)[0].content
    assert "exactly this position at Cafe Luna" in system
    assert "Never invent a different or combined position" in system


def test_the_interviewer_is_not_an_assistant() -> None:
    interview = ask_back_interview()
    transcript = [(m.role, m.content) for m in interview.messages]
    system = build_messages(interview, transcript, ExchangeKind.answer, 1)[0].content
    assert "Never offer or suggest mock interviews" in system
    assert "never as an encyclopedia" in system
    assert "never make a figure or a fact up" in system


def test_the_prompt_says_how_many_clarifications_are_left() -> None:
    def ask_prompt(count: int) -> str:
        interview = with_clarifications(count)
        transcript = [(m.role, m.content) for m in interview.messages]
        return build_messages(interview, transcript, ExchangeKind.ask, 1, count)[
            0
        ].content

    assert "allowed 2 more times" in ask_prompt(0)
    assert "allowed 1 more time;" in ask_prompt(1)
    assert "may not stay on it again" in ask_prompt(MAX_CLARIFICATIONS)


# -- ending the interview early -------------------------------------------------------


def test_without_a_warning_the_interviewer_cannot_end_the_interview() -> None:
    interview = with_clarifications(0)
    model = FakeModel().say("Goodbye.", end_interview=True)
    outcome = run(model, interview)
    assert not outcome.completes_interview
    outcome.apply_to(interview)
    assert interview.status is InterviewStatus.in_progress


def test_after_a_warning_the_interviewer_can_end_the_interview() -> None:
    interview = with_clarifications(1)
    model = FakeModel().say("I'm ending the interview here.", end_interview=True)
    applied = run(model, interview).apply_to(interview)
    assert interview.status is InterviewStatus.completed
    assert interview.ended_at is not None
    assert interview.phase is QA  # no ask-back
    assert interview.ended_by_interviewer
    assert not applied.interviewer_message.is_question  # a goodbye, not a question


def test_an_interview_that_reached_ask_back_was_not_ended_by_the_interviewer() -> None:
    interview = ask_back_interview()
    finish_ask_back(interview, "No more questions", FakeModel().say("Bye!", done=True))
    assert interview.status is InterviewStatus.completed
    assert not interview.ended_by_interviewer


def test_the_prompt_offers_ending_only_after_a_warning() -> None:
    def ask_prompt(count: int) -> str:
        interview = with_clarifications(count)
        transcript = [(m.role, m.content) for m in interview.messages]
        return build_messages(interview, transcript, ExchangeKind.ask, 1, count)[
            0
        ].content

    assert "end the interview now" not in ask_prompt(0)
    assert "end the interview now" in ask_prompt(1)
    assert "you will have to end the interview if it continues" in ask_prompt(0)

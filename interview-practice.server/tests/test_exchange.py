"""The interviewer's side of the conversation (ADR 0013): pacing, helper gating, the
reply contract and applying an exchange. No database: Interviews are built unsaved and
the real client talks to a fake transport."""

import json

import httpx
import pytest

from app.errors.exceptions import LlmUpstreamError
from app.interviews.shared.exchange import run_exchange
from app.interviews.shared.exchange.pacing import (
    MAX_ASK_BACK_QUESTIONS,
    ExchangeKind,
    decide_kind,
)
from app.llm.openrouter import CompletionSettings, OpenRouterClient
from app.models import (
    Difficulty,
    Interview,
    InterviewCategory,
    InterviewQuestion,
    InterviewStatus,
    Message,
    MessagePhase,
    MessageRole,
    ResponseStyle,
)

QA, ASK_BACK = MessagePhase.qa, MessagePhase.ask_back
INTERVIEWER, CANDIDATE = MessageRole.interviewer, MessageRole.candidate


def make_interview(
    *,
    target: int = 3,
    helpers: bool = False,
    messages: list[tuple[MessageRole, MessagePhase]] | None = None,
) -> Interview:
    interview = Interview(
        job_title="Backend Dev",
        seniority="senior",
        domain="backend",
        difficulty=Difficulty.easy,
        tone="neutral",
        interview_type="technical",
        interviewer_role="recruiter",
        target_question_count=target,
        status=InterviewStatus.in_progress,
        persona_name="Dana",
        persona_title="Recruiter",
        persona_backstory="Recruited for years.",
        coaching_helpers_enabled=helpers,
        response_style=ResponseStyle.concise,
        questions=[
            InterviewQuestion(category=InterviewCategory.technical, question="q")
        ],
    )
    for number, (role, phase) in enumerate(messages or [], start=1):
        interview.messages.append(
            Message(role=role, phase=phase, content=f"m{number}", sequence=number)
        )
    return interview


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
    assert decide_kind(make_interview(), has_reply=False) is ExchangeKind.open


def test_only_an_interview_without_messages_can_be_opened() -> None:
    with pytest.raises(ValueError):
        decide_kind(make_interview(messages=qa_exchanges(1)), has_reply=False)


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
    interview = make_interview(target=target, messages=qa_exchanges(asked))
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
    interview = make_interview(messages=messages)
    assert decide_kind(interview, has_reply=True) is expected


# -- a fake model ---------------------------------------------------------------------


class FakeModel:
    """Scripted replies for the interviewer, and a hint (or an outage) for the coach."""

    def __init__(self, hint: str | None = "Talk about a project.") -> None:
        self.replies: list[dict[str, object]] = []
        self.hint = hint
        self.hint_calls = 0
        self.client = OpenRouterClient(
            base_url="https://llm.test",
            api_key=lambda: "k",
            transport=httpx.MockTransport(self.handle),
        )

    def say(self, message: str, *, done: bool = False) -> "FakeModel":
        self.replies.append({"message": message, "done": done})
        return self

    def handle(self, request: httpx.Request) -> httpx.Response:
        system = json.loads(request.content)["messages"][0]["content"]
        if "coach helping a candidate" in system:
            self.hint_calls += 1
            if self.hint is None:
                return httpx.Response(503, json={"error": {"message": "busy"}})
            reply: dict[str, object] = {"hint": self.hint}
        else:
            reply = self.replies.pop(0)
        body = {"choices": [{"message": {"content": json.dumps(reply)}}]}
        return httpx.Response(200, json=body)


def run(model: FakeModel, interview: Interview, reply: str | None = "my answer"):
    return run_exchange(model.client, "m", CompletionSettings(), interview, reply)


# -- helper gating --------------------------------------------------------------------


def test_a_question_gets_a_hint_when_helpers_are_on() -> None:
    model = FakeModel().say("Next question?")
    interview = make_interview(helpers=True, messages=qa_exchanges(1))
    outcome = run(model, interview)
    assert outcome.helper_text == "Talk about a project."
    assert outcome.interviewer_phase is QA


def test_no_hint_when_helpers_are_off() -> None:
    model = FakeModel().say("Next question?")
    outcome = run(model, make_interview(helpers=False, messages=qa_exchanges(1)))
    assert outcome.helper_text is None
    assert model.hint_calls == 0


def test_the_wrap_up_gets_no_hint() -> None:
    model = FakeModel().say("That's all, any questions?", done=True)
    interview = make_interview(target=1, helpers=True, messages=qa_exchanges(1))
    outcome = run(model, interview)
    assert outcome.interviewer_phase is ASK_BACK
    assert outcome.helper_text is None
    assert model.hint_calls == 0


def test_ending_the_questions_early_gets_no_hint() -> None:
    model = FakeModel().say("Enough, any questions?", done=True)
    interview = make_interview(target=5, helpers=True, messages=qa_exchanges(1))
    outcome = run(model, interview)
    assert outcome.interviewer_phase is ASK_BACK
    assert model.hint_calls == 0


def test_the_opening_gets_a_hint_when_helpers_are_on() -> None:
    model = FakeModel().say("Hi! Tell me about yourself?")
    outcome = run(model, make_interview(helpers=True), reply=None)
    assert outcome.helper_text == "Talk about a project."


def test_a_hint_outage_leaves_the_card_out_not_the_exchange() -> None:
    model = FakeModel(hint=None).say("Next question?")
    interview = make_interview(helpers=True, messages=qa_exchanges(1))
    outcome = run(model, interview)
    assert outcome.helper_text is None
    assert outcome.interviewer_content == "Next question?"


# -- the reply contract ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("interview", "reply", "message", "done"),
    [
        # budget spent but the model keeps asking
        (make_interview(target=1, messages=qa_exchanges(1)), "a", "One more?", False),
        # the opening must not end the phase
        (make_interview(), None, "Hi", True),
        # nothing to store
        (make_interview(messages=qa_exchanges(1)), "a", "   ", False),
    ],
)
def test_a_reply_that_breaks_the_contract_is_an_error(
    interview: Interview, reply: str | None, message: str, done: bool
) -> None:
    with pytest.raises(LlmUpstreamError):
        run(FakeModel().say(message, done=done), interview, reply)


# -- running changes nothing, applying does -------------------------------------------


def test_running_an_exchange_does_not_touch_the_interview() -> None:
    interview = make_interview(messages=qa_exchanges(1))
    run(FakeModel().say("Next question?"), interview)
    assert len(interview.messages) == 1
    assert interview.status is InterviewStatus.in_progress


def test_applying_numbers_the_messages_and_records_activity() -> None:
    interview = make_interview(messages=qa_exchanges(1))
    applied = run(FakeModel().say("Next question?"), interview).apply_to(interview)
    assert applied.candidate_message is not None
    assert applied.candidate_message.sequence == 2
    assert applied.candidate_message.phase is QA
    assert applied.interviewer_message.sequence == 3
    assert [m.sequence for m in interview.messages] == [1, 2, 3]
    assert interview.last_activity_at is not None


def test_the_opening_adds_one_message() -> None:
    interview = make_interview()
    applied = run(FakeModel().say("Hi!"), interview, reply=None).apply_to(interview)
    assert applied.candidate_message is None
    assert applied.interviewer_message.sequence == 1
    assert applied.interviewer_message.phase is QA


def test_the_wrap_up_moves_to_ask_back_without_ending_the_interview() -> None:
    interview = make_interview(target=1, messages=qa_exchanges(1))
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
    return make_interview(messages=messages)


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


def test_an_ask_back_close_that_keeps_going_is_an_error() -> None:
    interview = ask_back_interview(MAX_ASK_BACK_QUESTIONS - 1)
    with pytest.raises(LlmUpstreamError):
        run(FakeModel().say("Ask me more!", done=False), interview, "One more")

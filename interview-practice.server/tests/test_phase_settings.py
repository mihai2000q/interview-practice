"""Which model and settings each phase runs on, the judge rule (ADR 0009), and how the
request's overrides become rows. No database: rows are built unsaved."""

import pytest
from pydantic import ValidationError

from app.errors.exceptions import BadRequestError, ConflictError
from app.interviews.schemas import InterviewPublic, PhaseSettingsOverride
from app.llm.phase_settings import (
    ensure_judge_differs_from_interviewer,
    ensure_overrides_allowed,
    phase_config,
)
from app.models import GenerationPhase, InterviewPhaseSettings

DEFAULT_MODEL = "gpt-5-mini"
JUDGE_MODEL = "google/gemini-2.5-flash"


def row(
    phase: GenerationPhase,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
) -> InterviewPhaseSettings:
    return InterviewPhaseSettings(
        phase=phase,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
    )


# -- resolving a phase -----------------------------------------------------------------


@pytest.mark.parametrize(
    "phase", [p for p in GenerationPhase if p is not GenerationPhase.interviewer_review]
)
def test_candidate_facing_phases_default_to_the_interview_model(
    phase: GenerationPhase,
) -> None:
    config = phase_config(phase)
    assert config.model == DEFAULT_MODEL
    assert config.settings.temperature is None
    assert config.settings.max_tokens is None
    assert config.settings.reasoning_effort is None


def test_the_judge_defaults_to_a_different_vendor() -> None:
    assert phase_config(GenerationPhase.interviewer_review).model == JUDGE_MODEL


def test_an_override_wins() -> None:
    config = phase_config(
        GenerationPhase.question_plan,
        [
            row(
                GenerationPhase.question_plan,
                model="other",
                temperature=0.3,
                max_tokens=700,
                reasoning_effort="low",
            )
        ],
    )
    assert config.model == "other"
    assert config.settings.temperature == 0.3
    assert config.settings.max_tokens == 700
    assert config.settings.reasoning_effort == "low"


def test_a_field_left_unset_falls_back_to_the_default() -> None:
    config = phase_config(
        GenerationPhase.live_conversation,
        [row(GenerationPhase.live_conversation, temperature=0.9)],
    )
    assert config.model == DEFAULT_MODEL
    assert config.settings.temperature == 0.9


def test_an_empty_model_falls_back_to_the_default() -> None:
    config = phase_config(
        GenerationPhase.evaluation, [row(GenerationPhase.evaluation, model="")]
    )
    assert config.model == DEFAULT_MODEL


def test_only_the_rows_of_that_phase_apply() -> None:
    rows = [row(GenerationPhase.jd_analysis, model="analysis-model", max_tokens=5)]
    config = phase_config(GenerationPhase.question_plan, rows)
    assert config.model == DEFAULT_MODEL
    assert config.settings.max_tokens is None


# -- the judge rule --------------------------------------------------------------------


def test_the_defaults_do_not_collide() -> None:
    ensure_judge_differs_from_interviewer([])


def test_a_judge_that_is_the_default_interview_model_collides_with_both_phases() -> (
    None
):
    with pytest.raises(ConflictError) as error:
        ensure_judge_differs_from_interviewer(
            [row(GenerationPhase.interviewer_review, model=DEFAULT_MODEL)]
        )
    assert error.value.status == 409
    assert error.value.code == "JUDGE_MODEL_COLLISION"
    assert error.value.details == {
        "judgeModel": DEFAULT_MODEL,
        "phases": ["live_conversation", "question_plan"],
    }


def test_overriding_the_interviewer_phases_to_the_judge_model_collides() -> None:
    with pytest.raises(ConflictError) as error:
        ensure_judge_differs_from_interviewer(
            [
                row(GenerationPhase.question_plan, model=JUDGE_MODEL),
                row(GenerationPhase.live_conversation, model=JUDGE_MODEL),
            ]
        )
    assert error.value.details is not None
    assert error.value.details["phases"] == ["live_conversation", "question_plan"]


def test_only_the_colliding_phase_is_reported() -> None:
    with pytest.raises(ConflictError) as error:
        ensure_judge_differs_from_interviewer(
            [
                row(GenerationPhase.interviewer_review, model="shared"),
                row(GenerationPhase.live_conversation, model="shared"),
            ]
        )
    assert error.value.details is not None
    assert error.value.details["phases"] == ["live_conversation"]


def test_a_judge_that_differs_from_overridden_phases_is_fine() -> None:
    ensure_judge_differs_from_interviewer(
        [
            row(GenerationPhase.interviewer_review, model=DEFAULT_MODEL),
            row(GenerationPhase.question_plan, model="a"),
            row(GenerationPhase.live_conversation, model="b"),
        ]
    )


def test_other_phases_may_use_the_judge_model() -> None:
    # Only the interviewer's own phases are excluded (ADR 0009).
    ensure_judge_differs_from_interviewer(
        [row(GenerationPhase.evaluation, model=JUDGE_MODEL)]
    )


# -- the request's overrides -----------------------------------------------------------


def test_the_request_names_exactly_the_phases_the_code_knows() -> None:
    assert set(PhaseSettingsOverride.model_fields) == {p.value for p in GenerationPhase}


def test_camel_case_request_fields_become_snake_case_rows() -> None:
    override = PhaseSettingsOverride.model_validate(
        {
            "jdAnalysis": {"model": "m", "maxTokens": 700},
            "liveConversation": {"reasoningEffort": "low", "temperature": 0.5},
        }
    )
    rows = {r.phase: r for r in override.to_rows()}
    assert set(rows) == {GenerationPhase.jd_analysis, GenerationPhase.live_conversation}
    assert rows[GenerationPhase.jd_analysis].model == "m"
    assert rows[GenerationPhase.jd_analysis].max_tokens == 700
    assert rows[GenerationPhase.live_conversation].reasoning_effort == "low"
    assert rows[GenerationPhase.live_conversation].temperature == 0.5


def test_no_overrides_make_no_rows() -> None:
    assert PhaseSettingsOverride.model_validate({}).to_rows() == []


@pytest.mark.parametrize(
    "bad",
    [
        {"bogusPhase": {}},
        {"questionPlan": {"model": "m", "unknown": 1}},
        {"questionPlan": {"temperature": 3}},
        {"questionPlan": {"maxTokens": 0}},
    ],
)
def test_invalid_overrides_are_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PhaseSettingsOverride.model_validate(bad)


# -- how the settings come back in a response ---------------------------------------


def response_overrides(rows: list[InterviewPhaseSettings]) -> dict[str, object]:
    """`phaseSettingsOverride` of an Interview response built around `rows`."""
    now = "2026-10-06T10:00:00Z"
    public = InterviewPublic.model_validate(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "job_application_id": None,
            "job_title": "Dev",
            "company_name": None,
            "domain": "backend",
            "seniority": "senior",
            "difficulty": "easy",
            "tone": "neutral",
            "interview_type": "technical",
            "interviewer_role": "recruiter",
            "target_question_count": 3,
            "status": "in_progress",
            "persona_name": "Dana",
            "persona_title": "Recruiter",
            "persona_image_url": None,
            "job_description_document_id": None,
            "cv_document_id": None,
            "cover_letter_document_id": None,
            "coaching_helpers_enabled": False,
            "response_style": "concise",
            "phase_settings": rows,
            "last_activity_at": now,
            "created_at": now,
            "ended_at": None,
        }
    )
    return dict(public.model_dump(mode="json")["phaseSettingsOverride"])


def test_the_response_uses_the_same_camel_case_keys_as_the_request() -> None:
    sent = {
        "coachingHelpers": {"model": "gpt-5-nano", "maxTokens": 400},
        "questionPlan": {"temperature": 0.3, "reasoningEffort": "low"},
    }
    rows = PhaseSettingsOverride.model_validate(sent).to_rows()
    assert response_overrides(rows) == sent


def test_unset_settings_and_phases_are_left_out_of_the_response() -> None:
    rows = [row(GenerationPhase.live_conversation, model="gpt-5-nano")]
    assert response_overrides(rows) == {"liveConversation": {"model": "gpt-5-nano"}}
    assert response_overrides([]) == {}


# -- the overrides an Interview carries ------------------------------------------------


def test_overrides_with_a_known_reasoning_effort_are_allowed() -> None:
    ensure_overrides_allowed(
        [
            row(GenerationPhase.evaluation, reasoning_effort="high"),
            row(GenerationPhase.question_plan, model=DEFAULT_MODEL),
        ]
    )


def test_an_override_with_an_unknown_reasoning_effort_is_refused() -> None:
    with pytest.raises(BadRequestError) as error:
        ensure_overrides_allowed(
            [row(GenerationPhase.evaluation, reasoning_effort="bogus")]
        )
    assert error.value.code == "REASONING_EFFORT_NOT_ALLOWED"


def test_overrides_with_an_allowed_model_for_their_phase_are_allowed() -> None:
    ensure_overrides_allowed(
        [
            row(GenerationPhase.live_conversation, model="gpt-4o-mini"),
            row(GenerationPhase.interviewer_review, model="google/gemini-2.5-flash"),
        ]
    )


@pytest.mark.parametrize(
    ("phase", "model"),
    [
        (GenerationPhase.question_plan, "google/gemini-2.5-flash"),
        (GenerationPhase.live_conversation, "made-up/model"),
        (GenerationPhase.interviewer_review, "gpt-4o-mini"),
    ],
)
def test_an_override_with_a_model_its_phase_cannot_run_on_is_refused(
    phase: GenerationPhase, model: str
) -> None:
    with pytest.raises(BadRequestError) as error:
        ensure_overrides_allowed([row(phase, model=model)])
    assert error.value.code == "MODEL_NOT_ALLOWED"

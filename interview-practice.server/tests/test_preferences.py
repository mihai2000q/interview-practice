"""Preferences as the middle layer between an Interview's overrides and the built-in
defaults, the models each phase may be given, and the judge rule over the defaults.
No database: rows are built unsaved."""

import pytest

from app.errors.exceptions import BadRequestError, ConflictError
from app.llm.phase_settings import (
    ensure_judge_differs_from_interviewer,
    ensure_model_allowed,
    ensure_reasoning_effort_allowed,
    phase_config,
    phase_defaults,
)
from app.llm.schemas import PhaseSettingsOverride
from app.models import GenerationPhase, InterviewPhaseSettings, PreferencePhaseSettings
from app.preferences.schemas import PreferencesPublic
from app.serialization import to_json

P = GenerationPhase


def preference(phase: GenerationPhase, **fields: object) -> PreferencePhaseSettings:
    return PreferencePhaseSettings(phase=phase, **fields)


def override(phase: GenerationPhase, **fields: object) -> InterviewPhaseSettings:
    return InterviewPhaseSettings(phase=phase, **fields)


# -- layering -------------------------------------------------------------------------


def test_a_preference_replaces_the_built_in_default() -> None:
    config = phase_config(
        P.evaluation,
        (),
        [preference(P.evaluation, model="gpt-5-nano", temperature=0.2, max_tokens=900)],
    )
    assert config.model == "gpt-5-nano"
    assert config.settings.temperature == 0.2
    assert config.settings.max_tokens == 900


def test_a_preference_only_applies_to_its_own_phase() -> None:
    config = phase_config(P.question_plan, (), [preference(P.evaluation, model="x")])
    assert config.model == "gpt-5-mini"


def test_an_override_wins_over_a_preference_field_by_field() -> None:
    config = phase_config(
        P.evaluation,
        [override(P.evaluation, temperature=1.0)],
        [preference(P.evaluation, model="gpt-5-nano", temperature=0.2, max_tokens=900)],
    )
    assert config.settings.temperature == 1.0  # the Interview's own choice
    assert config.model == "gpt-5-nano"  # not overridden: the preference
    assert config.settings.max_tokens == 900


def test_nothing_set_anywhere_is_the_built_in_default() -> None:
    config = phase_config(P.interviewer_review, [override(P.interviewer_review)], [])
    assert config.model == "google/gemini-2.5-flash"
    assert config.settings.temperature is None


def test_defaults_cover_every_phase() -> None:
    defaults = phase_defaults([preference(P.jd_analysis, model="gpt-5-nano")])
    assert set(defaults) == set(P)
    assert defaults[P.jd_analysis].model == "gpt-5-nano"
    assert defaults[P.evaluation].model == "gpt-5-mini"


# -- allowed models -------------------------------------------------------------------


@pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-5-nano", "gpt-4o-mini"])
def test_candidate_facing_phases_accept_the_chat_models(model: str) -> None:
    ensure_model_allowed(P.live_conversation, model)


@pytest.mark.parametrize("model", ["typesafe/jev-1.13", "google/gemini-2.5-flash"])
def test_candidate_facing_phases_refuse_the_judge_only_models(model: str) -> None:
    with pytest.raises(BadRequestError) as caught:
        ensure_model_allowed(P.question_plan, model)
    assert caught.value.code == "MODEL_NOT_ALLOWED"


def test_the_judge_accepts_its_own_set_but_not_gpt_4o_mini() -> None:
    for model in ("google/gemini-3.5-flash-lite", "typesafe/jev-1.13"):
        ensure_model_allowed(P.interviewer_review, model)
    with pytest.raises(BadRequestError):
        ensure_model_allowed(P.interviewer_review, "gpt-4o-mini")


@pytest.mark.parametrize("effort", ["minimal", "low", "medium", "high"])
def test_the_known_reasoning_efforts_are_accepted(effort: str) -> None:
    ensure_reasoning_effort_allowed(effort)


@pytest.mark.parametrize("effort", ["bogus", "HIGH", ""])
def test_any_other_reasoning_effort_is_refused(effort: str) -> None:
    with pytest.raises(BadRequestError) as caught:
        ensure_reasoning_effort_allowed(effort)
    assert caught.value.code == "REASONING_EFFORT_NOT_ALLOWED"


# -- the judge rule over Preferences --------------------------------------------------


def test_the_built_in_defaults_do_not_collide() -> None:
    ensure_judge_differs_from_interviewer((), [])


def test_a_judge_preference_equal_to_the_interview_model_collides() -> None:
    with pytest.raises(ConflictError) as caught:
        ensure_judge_differs_from_interviewer(
            (), [preference(P.interviewer_review, model="gpt-5-mini")]
        )
    assert caught.value.code == "JUDGE_MODEL_COLLISION"


def test_a_preferred_interview_model_that_reaches_the_judge_collides() -> None:
    with pytest.raises(ConflictError) as caught:
        ensure_judge_differs_from_interviewer(
            (),
            [
                preference(P.question_plan, model="gpt-5-nano"),
                preference(P.interviewer_review, model="gpt-5-nano"),
            ],
        )
    assert caught.value.details == {
        "judgeModel": "gpt-5-nano",
        "phases": ["question_plan"],
    }


def test_an_interview_override_can_collide_with_a_preference_judge() -> None:
    with pytest.raises(ConflictError):
        ensure_judge_differs_from_interviewer(
            [override(P.question_plan, model="gpt-5-nano")],
            [preference(P.interviewer_review, model="gpt-5-nano")],
        )


def test_an_interview_can_move_its_judge_away_from_a_colliding_preference() -> None:
    ensure_judge_differs_from_interviewer(
        [override(P.interviewer_review, model="google/gemini-3.5-flash-lite")],
        [
            preference(P.question_plan, model="gpt-5-nano"),
            preference(P.interviewer_review, model="gpt-5-nano"),
        ],
    )


# -- the request and response shapes --------------------------------------------------


def test_the_response_has_every_phase_in_camel_case() -> None:
    body = to_json(
        PreferencesPublic,
        phase_defaults([preference(P.evaluation, temperature=0.2, max_tokens=900)]),
    )
    assert set(body) == {
        "jdAnalysis",
        "questionPlan",
        "liveConversation",
        "coachingHelpers",
        "evaluation",
        "interviewerReview",
    }
    assert body["evaluation"] == {
        "model": "gpt-5-mini",
        "temperature": 0.2,
        "maxTokens": 900,
        "reasoningEffort": None,
    }


def test_an_explicit_null_is_told_apart_from_a_missing_setting() -> None:
    body = PhaseSettingsOverride.model_validate(
        {"evaluation": {"temperature": None}, "interviewerReview": None}
    )
    assert body.model_fields_set == {"evaluation", "interviewer_review"}
    assert body.evaluation is not None
    assert body.evaluation.model_fields_set == {"temperature"}

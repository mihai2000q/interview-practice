"""The vocabularies an Interview is described with, and the limits on its size.

Tone and role are plain text in the database, so these checks are what keeps the wording
tables, the portrait prompt and the API in step with the `Tone` and `InterviewerRole`
members. No database: the table's constraints are read from its metadata.
"""

from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import CheckConstraint

from app.interviews.schemas import InterviewCreate
from app.interviews.shared.guidance import ROLE_GUIDANCE, TONE_GUIDANCE
from app.interviews.use_cases.generate_evaluation import evaluation
from app.interviews.use_cases.generate_persona_image.portrait import build_prompt
from app.models import Interview, InterviewerRole, InterviewType, Tone
from app.models.interview import MAX_TARGET_QUESTIONS, MIN_TARGET_QUESTIONS
from tests.support import build_interview


def create_body(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "jobTitle": "Backend Developer",
        "seniority": "senior",
        "difficulty": "medium",
        "targetQuestionCount": 5,
        "tone": "neutral",
        "interviewType": "technical",
        "interviewerRole": "recruiter",
        "responseStyle": "concise",
        "coachingHelpersEnabled": False,
    }
    return {**fields, **overrides}


def test_every_role_and_tone_has_guidance_wording() -> None:
    assert set(ROLE_GUIDANCE) == set(InterviewerRole)
    assert set(TONE_GUIDANCE) == set(Tone)


@pytest.mark.parametrize("interview_type", list(InterviewType))
def test_every_interview_type_has_a_weighting(interview_type: InterviewType) -> None:
    interview = build_interview(interview_type=interview_type.value)
    assert "weigh" in evaluation.build_messages(interview)[0].content


def test_every_tone_gives_the_portrait_its_own_expression() -> None:
    prompts = {build_prompt("Dana Whitfield", "Recruiter", tone) for tone in Tone}
    assert len(prompts) == len(Tone)


@pytest.mark.parametrize(
    "overrides",
    [{"tone": "grumpy"}, {"interviewerRole": "ceo"}, {"interviewType": "mixed"}],
    ids=["tone", "role", "type"],
)
def test_a_tone_or_role_outside_the_vocabulary_is_rejected(
    overrides: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        InterviewCreate.model_validate(create_body(**overrides))


@pytest.mark.parametrize(
    ("count", "valid"),
    [
        (MIN_TARGET_QUESTIONS - 1, False),
        (MIN_TARGET_QUESTIONS, True),
        (MAX_TARGET_QUESTIONS, True),
        (MAX_TARGET_QUESTIONS + 1, False),
    ],
)
def test_the_question_count_is_limited_by_the_api(count: int, valid: bool) -> None:
    body = create_body(targetQuestionCount=count)
    if valid:
        assert InterviewCreate.model_validate(body).target_question_count == count
    else:
        with pytest.raises(ValidationError):
            InterviewCreate.model_validate(body)


def test_the_question_count_is_limited_by_the_table_too() -> None:
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in Interview.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks == {
        "ck_target_question_count_1_30": "target_question_count BETWEEN 1 AND 30"
    }

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.llm.guard import MAX_MESSAGE_CHARS, guarded
from app.llm.schemas import PhaseSettings, PhaseSettingsOverride
from app.models import (
    Difficulty,
    Evaluation,
    InterviewerRole,
    InterviewStatus,
    InterviewType,
    MessagePhase,
    MessageRole,
    ResponseStyle,
    StarCompleteness,
    Tone,
    Verdict,
)
from app.models.interview import MAX_TARGET_QUESTIONS, MIN_TARGET_QUESTIONS
from app.serialization import ApiModel, ShortText

# Free text that is later fed to the LLM, so it goes through the security guard. It is
# capped at 200 characters before the guard runs, so only the injection check can fire.
GuardedText = Annotated[ShortText, guarded()]


class ExistingJobApplication(ApiModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID


class NewJobApplication(ApiModel):
    model_config = ConfigDict(extra="forbid")

    create_new: Literal[True]


class InterviewCreate(ApiModel):
    model_config = ConfigDict(extra="forbid")

    job_title: GuardedText
    company_name: GuardedText | None = None
    seniority: GuardedText
    difficulty: Difficulty
    target_question_count: int = Field(ge=MIN_TARGET_QUESTIONS, le=MAX_TARGET_QUESTIONS)
    tone: Tone
    interview_type: InterviewType
    interviewer_role: InterviewerRole
    response_style: ResponseStyle
    coaching_helpers_enabled: bool
    job_description_id: uuid.UUID | None = None
    cv_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    job_application: ExistingJobApplication | NewJobApplication | None = None
    phase_settings_override: PhaseSettingsOverride | None = None


class InterviewPublic(ApiModel):
    """Response shape. Omits `evaluation_criteria`, which the candidate must not see."""

    id: uuid.UUID
    job_application_id: uuid.UUID | None
    job_title: str
    company_name: str | None
    domain: str
    seniority: str
    difficulty: Difficulty
    tone: str
    interview_type: str
    interviewer_role: str
    target_question_count: int
    status: InterviewStatus
    persona_name: str
    persona_title: str
    persona_image_url: str | None
    job_description_document_id: uuid.UUID | None
    cv_document_id: uuid.UUID | None
    cover_letter_document_id: uuid.UUID | None
    coaching_helpers_enabled: bool
    response_style: ResponseStyle
    phase_settings_override: dict[str, dict[str, Any]] = Field(
        validation_alias="phase_settings", serialization_alias="phaseSettingsOverride"
    )
    last_activity_at: datetime
    created_at: datetime
    ended_at: datetime | None

    @field_validator("phase_settings_override", mode="before")
    @classmethod
    def _from_rows(cls, rows: Any) -> Any:
        """The settings rows as `{phase: {setting: value}}`, set fields only, with the
        same camelCase keys the request takes (`PhaseSettingsOverride` owns them)."""
        if isinstance(rows, dict):
            return rows
        by_phase = {
            row.phase.value: {
                name: value
                for name in PhaseSettings.model_fields
                if (value := getattr(row, name)) is not None
            }
            for row in rows
        }
        return PhaseSettingsOverride.model_validate(by_phase).model_dump(
            by_alias=True, exclude_none=True
        )


class MessagePublic(ApiModel):
    id: uuid.UUID
    phase: MessagePhase
    role: MessageRole
    content: str
    helper_text: str | None
    sequence: int
    created_at: datetime


class InterviewDetail(InterviewPublic):
    """`GET /api/interviews/:id`: the Interview with its transcript."""

    phase: MessagePhase
    messages: list[MessagePublic]


class MessageCreate(ApiModel):
    """`POST /api/interviews/:id/messages` body: the candidate's reply."""

    model_config = ConfigDict(extra="forbid")

    content: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
        guarded(MAX_MESSAGE_CHARS),
    ]


class MessageExchange(ApiModel):
    """Response of `POST /api/interviews/:id/messages`."""

    candidate_message: MessagePublic
    interviewer_message: MessagePublic
    phase: MessagePhase
    status: InterviewStatus


class AskBackSuggestions(ApiModel):
    """Response of `GET /api/interviews/:id/ask-back-suggestions`."""

    suggestions: list[str]


class PersonaImage(ApiModel):
    """Response of `PUT /api/interviews/:id/persona-image`."""

    persona_image_url: str | None


class StarBreakdown(ApiModel):
    situation: str
    task: str
    action: str
    result: str
    completeness: StarCompleteness


class EvaluationPublic(ApiModel):
    """The Results page data: `GET`/`PUT /api/interviews/:id/evaluation`."""

    verdict: Verdict
    reasoning: str
    improvement_suggestions: str
    star_breakdown: StarBreakdown
    incomplete: bool

    @model_validator(mode="before")
    @classmethod
    def _nest_star_breakdown(cls, evaluation: Any) -> Any:
        """The model keeps the STAR fields flat; the response groups them."""
        if isinstance(evaluation, dict):
            return evaluation
        return {
            "verdict": evaluation.verdict,
            "reasoning": evaluation.reasoning,
            "improvement_suggestions": evaluation.improvement_suggestions,
            "incomplete": evaluation.incomplete,
            "star_breakdown": {
                "situation": evaluation.star_situation,
                "task": evaluation.star_task,
                "action": evaluation.star_action,
                "result": evaluation.star_result,
                "completeness": evaluation.star_completeness,
            },
        }


class ReviewScores(ApiModel):
    question_relevance: int
    persona_consistency: int
    pacing: int


class InterviewerReviewPublic(ApiModel):
    """`GET /api/interviews/:id/interviewer-review` (dev-facing)."""

    judge_model: str
    scores: ReviewScores
    reasoning: str

    @model_validator(mode="before")
    @classmethod
    def _nest_scores(cls, review: Any) -> Any:
        if isinstance(review, dict):
            return review
        return {
            "judge_model": review.judge_model,
            "reasoning": review.reasoning,
            "scores": {
                "question_relevance": review.score_question_relevance,
                "persona_consistency": review.score_persona_consistency,
                "pacing": review.score_pacing,
            },
        }


class InterviewSummary(ApiModel):
    """`GET /api/interviews` list item: enough to draw a history entry.

    `verdict` is read off the stored Evaluation; it is `null` until one exists.
    """

    id: uuid.UUID
    job_title: str
    company_name: str | None
    interviewer_role: str
    status: InterviewStatus
    verdict: Verdict | None = Field(
        validation_alias="evaluation", serialization_alias="verdict"
    )
    job_application_id: uuid.UUID | None
    created_at: datetime
    ended_at: datetime | None

    @field_validator("verdict", mode="before")
    @classmethod
    def _verdict_of_evaluation(cls, value: object) -> object:
        return value.verdict if isinstance(value, Evaluation) else value

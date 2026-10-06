import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.models import Evaluation, InterviewStatus, Verdict
from app.serialization import ApiModel


class ApplicationStage(ApiModel):
    """One Interview under an Application: enough to draw the pipeline."""

    id: uuid.UUID
    interviewer_role: str
    status: InterviewStatus


class ApplicationDocument(ApiModel):
    """A Document attached to an Application, with just what the UI needs to show it."""

    id: uuid.UUID
    name: str
    analysis_model: str | None


class ApplicationSummary(ApiModel):
    """List item. The documents let Create Interview pre-fill (and name) a new stage."""

    id: uuid.UUID
    company_name: str | None
    job_title: str
    seniority: str
    job_description: ApplicationDocument | None = Field(
        validation_alias="job_description_document",
        serialization_alias="jobDescription",
    )
    cv: ApplicationDocument | None = Field(
        validation_alias="cv_document", serialization_alias="cv"
    )
    cover_letter: ApplicationDocument | None = Field(
        validation_alias="cover_letter_document", serialization_alias="coverLetter"
    )
    interviews: list[ApplicationStage]


class OverviewStage(ApiModel):
    """One stage on the Application Overview: its status, and how it went once graded.

    `verdict` is read off the stored Evaluation; it is `null` until one exists.
    """

    id: uuid.UUID
    interviewer_role: str
    status: InterviewStatus
    verdict: Verdict | None = Field(
        validation_alias="evaluation", serialization_alias="verdict"
    )
    created_at: datetime
    ended_at: datetime | None

    @field_validator("verdict", mode="before")
    @classmethod
    def _verdict_of_evaluation(cls, value: object) -> object:
        return value.verdict if isinstance(value, Evaluation) else value


class ApplicationOverview(ApiModel):
    """`GET /api/applications/:id`: the Application, its stages and its progress.

    `progress_score` and `progress_summary` are `null` until they have been generated.
    `progress_outdated` says they should be (re)generated now: there are enough
    Evaluations to compare and they are not the ones the stored pair was built from
    (ADR 0015); the model works that out, since the basis is internal.
    """

    id: uuid.UUID
    company_name: str | None
    job_title: str
    seniority: str
    job_description: ApplicationDocument | None = Field(
        validation_alias="job_description_document",
        serialization_alias="jobDescription",
    )
    cv: ApplicationDocument | None = Field(
        validation_alias="cv_document", serialization_alias="cv"
    )
    cover_letter: ApplicationDocument | None = Field(
        validation_alias="cover_letter_document", serialization_alias="coverLetter"
    )
    progress_score: int | None
    progress_summary: str | None
    progress_outdated: bool
    created_at: datetime
    interviews: list[OverviewStage]


class ApplicationProgress(ApiModel):
    """`PUT /api/applications/:id/progress`: the score and summary, made together."""

    progress_score: int
    progress_summary: str

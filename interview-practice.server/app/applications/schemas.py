import uuid

from pydantic import Field

from app.models import InterviewStatus
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

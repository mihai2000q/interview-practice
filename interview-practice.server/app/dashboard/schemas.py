import uuid
from datetime import datetime

from app.models import InterviewerRole, InterviewStatus, Verdict
from app.serialization import ApiModel


class StatusCounts(ApiModel):
    in_progress: int
    completed: int
    abandoned: int


class OutcomeCounts(ApiModel):
    hire: int
    no_hire: int
    awaiting_evaluation: int


class RecentInterview(ApiModel):
    id: uuid.UUID
    job_title: str
    company_name: str | None
    interviewer_role: InterviewerRole
    status: InterviewStatus
    verdict: Verdict | None
    ended_at: datetime


class DashboardPublic(ApiModel):
    """`GET /api/dashboard`: the Home page's numbers."""

    total_interviews: int
    by_status: StatusCounts
    outcomes: OutcomeCounts
    recent: list[RecentInterview]

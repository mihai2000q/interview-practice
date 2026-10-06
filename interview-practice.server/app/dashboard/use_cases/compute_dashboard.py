import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import exists, func, select

from app.extensions import db
from app.models import (
    Evaluation,
    Interview,
    InterviewStatus,
    Message,
    MessageRole,
    Verdict,
)
from app.services.interview_lifecycle import settle_all_stale

RECENT_LIMIT = 5


@dataclass(frozen=True)
class StatusCounts:
    in_progress: int
    completed: int
    abandoned: int


@dataclass(frozen=True)
class OutcomeCounts:
    hire: int
    no_hire: int
    awaiting_evaluation: int


@dataclass(frozen=True)
class RecentInterview:
    id: uuid.UUID
    job_title: str
    company_name: str | None
    status: InterviewStatus
    verdict: Verdict | None
    ended_at: datetime


@dataclass(frozen=True)
class Dashboard:
    total_interviews: int
    by_status: StatusCounts
    outcomes: OutcomeCounts
    recent: list[RecentInterview]


def build_dashboard(
    status_counts: Mapping[InterviewStatus, int],
    verdict_counts: Mapping[Verdict, int],
    awaiting_evaluation: int,
    recent: Sequence[RecentInterview],
) -> Dashboard:
    """Put the grouped counts together; a status or verdict with no rows counts 0."""
    by_status = StatusCounts(
        in_progress=status_counts.get(InterviewStatus.in_progress, 0),
        completed=status_counts.get(InterviewStatus.completed, 0),
        abandoned=status_counts.get(InterviewStatus.abandoned, 0),
    )
    return Dashboard(
        total_interviews=sum(status_counts.values()),
        by_status=by_status,
        outcomes=OutcomeCounts(
            hire=verdict_counts.get(Verdict.hire, 0),
            no_hire=verdict_counts.get(Verdict.no_hire, 0),
            awaiting_evaluation=awaiting_evaluation,
        ),
        recent=list(recent),
    )


def compute_dashboard() -> Dashboard:
    """The Home page's numbers, from grouped queries (no Interview is loaded whole).

    Stale sessions are closed first (ADR 0006), so the counts agree with the history
    list. Read-only: no Evaluation is ever generated here.
    """
    settle_all_stale()

    status_counts = {
        status: count
        for status, count in db.session.execute(
            select(Interview.status, func.count()).group_by(Interview.status)
        ).tuples()
    }
    verdict_counts = {
        verdict: count
        for verdict, count in db.session.execute(
            select(Evaluation.verdict, func.count()).group_by(Evaluation.verdict)
        ).tuples()
    }

    # Ended, with something the candidate said, and no Evaluation yet.
    awaiting_evaluation = db.session.scalar(
        select(func.count())
        .select_from(Interview)
        .where(
            Interview.status != InterviewStatus.in_progress,
            exists().where(
                Message.interview_id == Interview.id,
                Message.role == MessageRole.candidate,
            ),
            ~exists().where(Evaluation.interview_id == Interview.id),
        )
    )

    recent_rows = db.session.execute(
        select(
            Interview.id,
            Interview.job_title,
            Interview.company_name,
            Interview.status,
            Evaluation.verdict,
            Interview.ended_at,
        )
        .outerjoin(Evaluation, Evaluation.interview_id == Interview.id)
        .where(Interview.ended_at.is_not(None))
        .order_by(Interview.ended_at.desc(), Interview.created_at.desc())
        .limit(RECENT_LIMIT)
    ).all()
    recent = [
        RecentInterview(
            id=row.id,
            job_title=row.job_title,
            company_name=row.company_name,
            status=row.status,
            verdict=row.verdict,
            ended_at=row.ended_at,
        )
        for row in recent_rows
    ]

    return build_dashboard(
        status_counts, verdict_counts, awaiting_evaluation or 0, recent
    )

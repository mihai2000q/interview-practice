"""When an Interview is stale, when a turn is in progress, and how an Interview ends.

Shared by the interviews and applications domains (ADR 0006): staleness is detected
lazily, as an Interview is read, never by a background job. The rules are pure and take
the time as an argument; `settle_stale` applies them to the database.
"""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.extensions import db
from app.models import Interview, InterviewStatus

# Long enough that thinking mid-answer isn't flagged, short enough that history doesn't
# show dead "in progress" sessions.
STALE_AFTER = timedelta(minutes=30)

# An exchange makes up to two LLM calls (60s timeout each by default). If its request
# dies without clearing the marker, the Interview accepts a new one after this long.
TURN_TTL = timedelta(minutes=5)


def turn_in_progress(interview: Interview, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    started = interview.turn_started_at
    return started is not None and now - started < TURN_TTL


def is_stale(interview: Interview, now: datetime | None = None) -> bool:
    """An `in_progress` Interview with no recent activity and no exchange running.

    An Interview with an exchange in progress is active, however long the model takes.
    """
    now = now or datetime.now(UTC)
    return (
        interview.status is InterviewStatus.in_progress
        and not turn_in_progress(interview, now)
        and now - interview.last_activity_at > STALE_AFTER
    )


def end(interview: Interview, status: InterviewStatus) -> None:
    interview.status = status
    interview.ended_at = datetime.now(UTC)


def settle_stale(interviews: Iterable[Interview]) -> None:
    """Flip the stale ones among `interviews` to `abandoned`, and keep that.

    Each flip is one compare-and-swap `UPDATE`, guarded by the values this reader saw
    (activity time and exchange marker): if a message arrived or an exchange started
    in the meantime, it matches no row and nothing changes. `ended_at` is when the
    activity stopped, not when it was noticed. Afterwards the Interviews are re-read
    on next access, so they show the state that actually holds.
    """
    now = datetime.now(UTC)
    attempted = False
    for interview in interviews:
        if not is_stale(interview, now):
            continue
        attempted = True
        db.session.execute(
            update(Interview)
            .where(
                Interview.id == interview.id,
                Interview.status == InterviewStatus.in_progress,
                Interview.last_activity_at == interview.last_activity_at,
                Interview.turn_started_at.is_not_distinct_from(
                    interview.turn_started_at
                ),
            )
            .values(
                status=InterviewStatus.abandoned,
                ended_at=interview.last_activity_at,
            )
        )
    if attempted:
        db.session.commit()


def settle_all_stale() -> None:
    """Close every stale Interview in the database, for readers of many at once.

    Only `in_progress` Interviews past the staleness window are loaded (a small set), so
    a list or an aggregate can then be read in one query and agree with `settle_stale`.
    """
    candidates = db.session.scalars(
        select(Interview).where(
            Interview.status == InterviewStatus.in_progress,
            Interview.last_activity_at < datetime.now(UTC) - STALE_AFTER,
        )
    )
    settle_stale(candidates)

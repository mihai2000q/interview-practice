"""When an Interview counts as stale (ADR 0006) and how one ends. The rules are pure and
take the time as an argument, so no database and no waiting."""

from datetime import UTC, datetime, timedelta

import pytest

from app.models import Interview, InterviewStatus
from app.services.interview_lifecycle import (
    STALE_AFTER,
    TURN_TTL,
    end,
    is_stale,
    turn_in_progress,
)

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def interview(
    *,
    idle: timedelta = timedelta(0),
    status: InterviewStatus = InterviewStatus.in_progress,
    turn_started_ago: timedelta | None = None,
) -> Interview:
    return Interview(
        status=status,
        last_activity_at=NOW - idle,
        turn_started_at=None if turn_started_ago is None else NOW - turn_started_ago,
    )


# -- stale or not --------------------------------------------------------------


def test_an_interview_with_recent_activity_is_not_stale() -> None:
    assert not is_stale(interview(idle=timedelta(minutes=5)), NOW)


def test_exactly_at_the_limit_is_not_yet_stale() -> None:
    assert not is_stale(interview(idle=STALE_AFTER), NOW)


def test_just_past_the_limit_is_stale() -> None:
    assert is_stale(interview(idle=STALE_AFTER + timedelta(seconds=1)), NOW)


@pytest.mark.parametrize(
    "status", [InterviewStatus.completed, InterviewStatus.abandoned]
)
def test_an_interview_that_has_ended_is_never_stale(status: InterviewStatus) -> None:
    assert not is_stale(interview(idle=timedelta(hours=5), status=status), NOW)


# -- an exchange in progress ---------------------------------------------------


def test_no_marker_means_no_exchange_in_progress() -> None:
    assert not turn_in_progress(interview(), NOW)


def test_a_fresh_marker_means_an_exchange_in_progress() -> None:
    assert turn_in_progress(interview(turn_started_ago=timedelta(seconds=30)), NOW)


def test_a_marker_older_than_the_ttl_no_longer_counts() -> None:
    assert not turn_in_progress(interview(turn_started_ago=TURN_TTL), NOW)
    assert not turn_in_progress(
        interview(turn_started_ago=TURN_TTL + timedelta(seconds=1)), NOW
    )


def test_a_live_exchange_keeps_an_idle_interview_from_going_stale() -> None:
    idle_with_live_exchange = interview(
        idle=timedelta(hours=1), turn_started_ago=timedelta(minutes=1)
    )
    assert not is_stale(idle_with_live_exchange, NOW)


def test_an_expired_marker_does_not_protect_an_idle_interview() -> None:
    idle_with_dead_marker = interview(
        idle=timedelta(hours=1), turn_started_ago=TURN_TTL + timedelta(minutes=1)
    )
    assert is_stale(idle_with_dead_marker, NOW)


# -- ending --------------------------------------------------------------------


@pytest.mark.parametrize(
    "status", [InterviewStatus.completed, InterviewStatus.abandoned]
)
def test_ending_sets_the_status_and_the_time(status: InterviewStatus) -> None:
    ended = interview()
    before = datetime.now(UTC)
    end(ended, status)
    assert ended.status is status
    assert ended.ended_at is not None
    assert before <= ended.ended_at <= datetime.now(UTC)

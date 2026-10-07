"""The read-only history endpoints: the Interview list item and the Home dashboard.
No database: the queries need one, so what is tested is the shape of the JSON, the
verdict mapping, the counting, and that the routes are registered."""

import uuid
from datetime import UTC, datetime

from app.dashboard.schemas import DashboardPublic
from app.dashboard.use_cases.compute_dashboard import RecentInterview, build_dashboard
from app.interviews.schemas import InterviewSummary
from app.models import Evaluation, InterviewStatus, Verdict
from app.serialization import to_json
from tests.support import build_interview

ENDED = datetime(2026, 10, 6, 9, 10, tzinfo=UTC)


def summary(**fields: object) -> dict[str, object]:
    interview = build_interview(
        id=uuid.uuid4(),
        company_name="Acme",
        created_at=ENDED,
        ended_at=None,
        job_application_id=None,
        **fields,
    )
    return to_json(InterviewSummary, interview)


def test_interview_summary_has_exactly_the_contract_keys() -> None:
    assert set(summary()) == {
        "id",
        "jobTitle",
        "companyName",
        "interviewerRole",
        "status",
        "verdict",
        "jobApplicationId",
        "createdAt",
        "endedAt",
    }


def test_interview_without_evaluation_has_a_null_verdict() -> None:
    body = summary()
    assert body["verdict"] is None
    assert body["status"] == "in_progress"
    assert body["jobApplicationId"] is None
    assert body["endedAt"] is None
    assert body["companyName"] == "Acme"


def test_interview_verdict_comes_from_the_evaluation() -> None:
    for verdict in Verdict:
        assert summary(evaluation=Evaluation(verdict=verdict))["verdict"] == (
            verdict.value
        )


def test_standalone_company_may_be_null() -> None:
    interview = build_interview(
        id=uuid.uuid4(), company_name=None, created_at=ENDED, ended_at=ENDED
    )
    body = to_json(InterviewSummary, interview)
    assert body["companyName"] is None
    assert body["endedAt"] == "2026-10-06T09:10:00Z"


def recent(verdict: Verdict | None) -> RecentInterview:
    return RecentInterview(
        id=uuid.uuid4(),
        job_title="Senior Engineer",
        company_name="Acme",
        interviewer_role="recruiter",
        status=InterviewStatus.completed,
        verdict=verdict,
        ended_at=ENDED,
    )


def test_empty_dashboard_is_all_zeros() -> None:
    body = to_json(DashboardPublic, build_dashboard({}, {}, 0, []))
    assert body == {
        "totalInterviews": 0,
        "byStatus": {"inProgress": 0, "completed": 0, "abandoned": 0},
        "outcomes": {"hire": 0, "noHire": 0, "awaitingEvaluation": 0},
        "recent": [],
    }


def test_dashboard_total_is_the_sum_of_the_statuses() -> None:
    dashboard = build_dashboard(
        {
            InterviewStatus.in_progress: 1,
            InterviewStatus.completed: 9,
            InterviewStatus.abandoned: 2,
        },
        {Verdict.hire: 5, Verdict.no_hire: 3},
        2,
        [recent(Verdict.hire), recent(None)],
    )
    body = to_json(DashboardPublic, dashboard)
    assert body["totalInterviews"] == 12
    assert body["byStatus"] == {"inProgress": 1, "completed": 9, "abandoned": 2}
    assert body["outcomes"] == {"hire": 5, "noHire": 3, "awaitingEvaluation": 2}
    assert [r["verdict"] for r in body["recent"]] == ["hire", None]
    assert set(body["recent"][0]) == {
        "id",
        "jobTitle",
        "companyName",
        "interviewerRole",
        "status",
        "verdict",
        "endedAt",
    }


def test_missing_verdict_counts_default_to_zero() -> None:
    dashboard = build_dashboard(
        {InterviewStatus.completed: 1}, {Verdict.no_hire: 1}, 0, []
    )
    assert dashboard.outcomes.hire == 0
    assert dashboard.outcomes.no_hire == 1
    assert dashboard.by_status.abandoned == 0


def test_routes_are_registered() -> None:
    from app.app import create_app

    rules = {
        (method, rule.rule): rule.endpoint
        for rule in create_app().url_map.iter_rules()
        for method in rule.methods or ()
    }
    assert rules[("GET", "/api/interviews")] == "interviews.get_interviews"
    assert rules[("GET", "/api/dashboard")] == "dashboard.get_dashboard"

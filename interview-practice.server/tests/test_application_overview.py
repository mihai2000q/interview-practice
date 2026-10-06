"""The Application Overview endpoint's response. No database: the query needs one, so
what is tested is the shape of the JSON, the verdict mapping, and that the route is
registered."""

import uuid
from datetime import UTC, datetime

from app.app import create_app
from app.applications.schemas import ApplicationOverview
from app.applications.shared import progress_basis
from app.models import Evaluation, JobApplication, Verdict
from app.serialization import to_json
from tests.support import build_interview

STARTED = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def evaluation() -> Evaluation:
    return Evaluation(id=uuid.uuid4(), verdict=Verdict.hire)


def overview(*stages: dict[str, object], **fields: object) -> dict[str, object]:
    application = JobApplication(
        id=uuid.uuid4(),
        company_name="Acme",
        job_title="Backend Dev",
        created_at=STARTED,
        **fields,
    )
    for stage in stages:
        application.interviews.append(
            build_interview(id=uuid.uuid4(), created_at=STARTED, ended_at=None, **stage)
        )
    return to_json(ApplicationOverview, application)


def test_overview_has_exactly_the_contract_keys() -> None:
    assert set(overview()) == {
        "id",
        "companyName",
        "jobTitle",
        "jobDescription",
        "cv",
        "coverLetter",
        "progressScore",
        "progressSummary",
        "progressOutdated",
        "createdAt",
        "interviews",
    }


def test_progress_is_null_until_it_is_generated() -> None:
    body = overview()
    assert body["progressScore"] is None
    assert body["progressSummary"] is None
    assert body["jobDescription"] is None
    assert body["interviews"] == []


def test_progress_is_returned_as_stored() -> None:
    body = overview(progress_score=4, progress_summary="Better on STAR.")
    assert body["progressScore"] == 4
    assert body["progressSummary"] == "Better on STAR."


def test_one_evaluation_is_never_outdated() -> None:
    body = overview({"evaluation": Evaluation(id=uuid.uuid4(), verdict=Verdict.hire)})
    assert body["progressOutdated"] is False


def test_two_evaluations_with_no_summary_are_outdated() -> None:
    body = overview(*({"evaluation": evaluation()} for _ in range(2)))
    assert body["progressOutdated"] is True


def test_a_summary_built_from_these_evaluations_is_current() -> None:
    first, second = evaluation(), evaluation()
    basis = progress_basis([first.id, second.id])
    body = overview(
        {"evaluation": first},
        {"evaluation": second},
        progress_score=4,
        progress_summary="Steady.",
        progress_basis=basis,
    )
    assert body["progressOutdated"] is False
    assert "progressBasis" not in body


def test_a_summary_is_outdated_once_another_stage_is_graded() -> None:
    first, second, third = evaluation(), evaluation(), evaluation()
    body = overview(
        {"evaluation": first},
        {"evaluation": second},
        {"evaluation": third},
        progress_basis=progress_basis([first.id, second.id]),
    )
    assert body["progressOutdated"] is True


def test_stage_has_exactly_the_contract_keys() -> None:
    (stage,) = overview({})["interviews"]  # type: ignore[misc]
    assert set(stage) == {
        "id",
        "interviewerRole",
        "status",
        "verdict",
        "createdAt",
        "endedAt",
    }


def test_stage_verdict_comes_from_the_evaluation() -> None:
    stages = overview(
        {},
        {"evaluation": Evaluation(verdict=Verdict.hire)},
        {"evaluation": Evaluation(verdict=Verdict.no_hire)},
    )["interviews"]
    assert [stage["verdict"] for stage in stages] == [  # type: ignore[attr-defined]
        None,
        "hire",
        "no_hire",
    ]


def test_the_route_is_registered() -> None:
    rules = {
        (rule.rule, method)
        for rule in create_app().url_map.iter_rules()
        for method in rule.methods or ()
    }
    assert ("/api/applications/<uuid:application_id>", "GET") in rules

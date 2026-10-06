"""Running LLM calls concurrently (app.llm.concurrency): order, errors, the app context
inside workers, and abandoning without waiting. No database."""

import time
from collections.abc import Iterator

import pytest
from flask import Flask, current_app

from app.llm.concurrency import fan_out


@pytest.fixture
def app() -> Iterator[Flask]:
    flask_app = Flask("concurrency-test")
    flask_app.config["MARKER"] = "from-config"
    with flask_app.app_context():
        yield flask_app


def slow(seconds: float, value: str):
    def job() -> str:
        time.sleep(seconds)
        return value

    return job


def failing(message: str, after: float = 0.0):
    def job() -> str:
        time.sleep(after)
        raise RuntimeError(message)

    return job


# -- fan_out ---------------------------------------------------------------------------


def test_results_keep_the_input_order(app: Flask) -> None:
    assert fan_out([slow(0.2, "first"), slow(0.0, "second")]) == ["first", "second"]


def test_no_jobs_is_an_empty_result(app: Flask) -> None:
    assert fan_out([]) == []


def test_jobs_run_at_the_same_time(app: Flask) -> None:
    started = time.perf_counter()
    fan_out([slow(0.4, "a"), slow(0.4, "b"), slow(0.4, "c")])
    assert time.perf_counter() - started < 0.9


def test_a_worker_has_the_app_context(app: Flask) -> None:
    def read_config() -> str:
        return str(current_app.config["MARKER"])

    assert fan_out([read_config, read_config]) == ["from-config", "from-config"]


def test_an_error_is_raised_at_once_without_waiting_for_the_rest(app: Flask) -> None:
    started = time.perf_counter()
    with pytest.raises(RuntimeError, match="boom"):
        fan_out([slow(1.5, "slow"), failing("boom")])
    assert time.perf_counter() - started < 0.7


def test_the_error_of_whichever_job_fails_first_is_raised(app: Flask) -> None:
    with pytest.raises(RuntimeError, match="quick"):
        fan_out([failing("late", after=0.4), failing("quick")])

"""Running LLM calls concurrently: the one place that owns how.

Two shapes cover every use: `fan_out` (run several calls, collect all results) and
`background` (start one call, do other work, then join or abandon it). Both run each job
inside the caller's Flask app context, so a worker can never fail on a missing context,
and both stop waiting on the first failure.

A job should still receive only plain data and the client, and use no database
session: the context makes Flask lookups work, not the ORM thread-safe. Abandoning stops
*waiting* for a job; a request already in flight can't be cancelled and finishes
unobserved in its worker thread, with its result dropped.
"""

from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_EXCEPTION, Future, ThreadPoolExecutor, wait

from flask import Flask, current_app


def _in_app_context[T](app: Flask, job: Callable[[], T]) -> Callable[[], T]:
    def run() -> T:
        with app.app_context():
            return job()

    return run


def fan_out[T](jobs: Sequence[Callable[[], T]]) -> list[T]:
    """Run `jobs` at once; results come back in input order.

    On the first failure the error is raised at once and the rest are abandoned instead
    of waited for.
    """
    if not jobs:
        return []
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    pool = ThreadPoolExecutor(max_workers=len(jobs))
    try:
        futures = [pool.submit(_in_app_context(app, job)) for job in jobs]
        wait(futures, return_when=FIRST_EXCEPTION)
        for future in futures:
            if future.done() and future.exception() is not None:
                future.result()  # raises it
        return [future.result() for future in futures]
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


class Background[T]:
    """A job in its own thread: `result()` joins it, `abandon()` stops waiting."""

    def __init__(self, pool: ThreadPoolExecutor, future: Future[T]) -> None:
        self._pool = pool
        self._future = future

    def result(self) -> T:
        return self._future.result()

    def abandon(self) -> None:
        """Safe to call at any time, including after `result()`."""
        self._pool.shutdown(wait=False, cancel_futures=True)


def background[T](job: Callable[[], T]) -> Background[T]:
    """Start `job` now. Pair with `abandon()` in a `finally`, so a failure elsewhere
    returns at once instead of waiting for it."""
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    pool = ThreadPoolExecutor(max_workers=1)
    return Background(pool, pool.submit(_in_app_context(app, job)))

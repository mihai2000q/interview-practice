"""Running LLM calls concurrently: the one place that owns how.

`fan_out` runs several calls at once and collects the results. Each job runs inside the
caller's Flask app context, so a worker can never fail on a missing context, and the
first failure is raised at once instead of waiting for the others.

A job should still receive only plain data and the client, and use no database
session: the context makes Flask lookups work, not the ORM thread-safe. When one job
fails, `fan_out` stops *waiting* for the others; a request already in flight can't be
cancelled and finishes unobserved in its worker thread, with its result dropped.
"""

from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait

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

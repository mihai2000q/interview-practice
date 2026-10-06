"""Step timing: one log line per slow step, so we can see where the time goes.

with timed("plan"):
    ...                      # logs: step=plan seconds=12.34
"""

import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager


class _StderrHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Writes to whatever `sys.stderr` is *now*, so a job that finishes late (after a
    test or a request has swapped the stream) never logs to a closed one."""

    def __init__(self) -> None:
        super().__init__(sys.stderr)

    @property
    def stream(self) -> object:
        return sys.stderr

    @stream.setter
    def stream(self, value: object) -> None:
        pass


logger = logging.getLogger("app.timing")
if not logger.handlers:
    handler = _StderrHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s TIMING %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


@contextmanager
def timed(label: str) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        logger.info("step=%s seconds=%.2f", label, time.perf_counter() - started)

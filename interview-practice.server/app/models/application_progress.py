"""When an Application's progress summary is out of date (ADR 0015).

A stored score and summary were built from a set of Evaluations. `progress_basis` is a
fingerprint of that set: the summary is outdated as soon as the Application's current
Evaluations are a different set (one more was made, or a stage was deleted).
"""

import hashlib
import uuid
from collections.abc import Iterable

# Nothing is compared, so nothing is generated, below this many Evaluations.
MIN_EVALUATIONS = 2


def progress_basis(evaluation_ids: Iterable[uuid.UUID]) -> str:
    """A fingerprint of a set of Evaluations, the same whatever order they come in."""
    digest = hashlib.sha256()
    for evaluation_id in sorted(str(i) for i in evaluation_ids):
        digest.update(evaluation_id.encode())
    return digest.hexdigest()


def is_outdated(stored_basis: str | None, evaluation_ids: Iterable[uuid.UUID]) -> bool:
    """Whether a summary should be (re)generated: there are enough Evaluations to
    compare, and they are not the ones the stored summary was built from."""
    ids = list(evaluation_ids)
    return len(ids) >= MIN_EVALUATIONS and progress_basis(ids) != stored_basis

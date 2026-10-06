"""Removing stored persona portraits from disk, for the domains that delete Interviews.

Portraits live under the Flask `instance/` folder and `Interview.persona_image_path` is
relative to it. Removal is cosmetic cleanup that runs after the rows are gone, so it
never raises: a missing file is fine and any other failure is only logged.
"""

import logging
from collections.abc import Iterable

from app.paths import instance_dir

logger = logging.getLogger(__name__)


def remove_portrait_files(relative_paths: Iterable[str]) -> None:
    """Best-effort removal of the given files (paths relative to `instance/`).

    A path that would leave the instance folder (`..`, an absolute path, a symlink out)
    is skipped, so a bad value in the database can't delete anything else.
    """
    root = instance_dir().resolve()
    for relative in relative_paths:
        try:
            path = (root / relative).resolve()
            if not path.is_relative_to(root):
                logger.warning(
                    "Not removing a portrait outside instance/: %s", relative
                )
                continue
            path.unlink(missing_ok=True)
        except (OSError, ValueError):
            logger.exception("Could not remove the portrait file %s", relative)

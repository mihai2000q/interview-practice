import uuid
from pathlib import Path

from app.errors.exceptions import NotFoundError
from app.interviews.shared import get_interview_or_404
from app.paths import instance_dir


def get_persona_image(interview_id: uuid.UUID) -> Path:
    """The stored portrait of an Interview's persona."""
    interview = get_interview_or_404(interview_id)
    if interview.persona_image_path is None:
        raise NotFoundError("This interview has no portrait.")
    path = instance_dir() / interview.persona_image_path
    if not path.is_file():
        raise NotFoundError("The stored portrait is missing.")
    return path

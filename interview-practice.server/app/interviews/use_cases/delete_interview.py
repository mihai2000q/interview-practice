import uuid

from app.errors.exceptions import NotFoundError
from app.extensions import db
from app.models import Interview
from app.services.portrait_files import remove_portrait_files


def delete_interview(interview_id: uuid.UUID) -> None:
    """Hard-delete one Interview, in any status, and everything hanging off it. Its
    Application and the Documents stay. The database cascades the deletes; the portrait
    file is removed after the commit, best effort."""
    # Not `get_interview_or_404`: closing a stale Interview first would be pointless.
    interview = db.session.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError("Interview not found.")
    portrait = interview.persona_image_path
    db.session.delete(interview)
    db.session.commit()
    if portrait is not None:
        remove_portrait_files([portrait])

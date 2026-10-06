import uuid

from sqlalchemy import select

from app.errors.exceptions import NotFoundError
from app.extensions import db
from app.models import Interview, JobApplication
from app.services.portrait_files import remove_portrait_files


def delete_application(application_id: uuid.UUID) -> None:
    """Hard-delete a JobApplication, its Interviews and everything hanging off them
    (ADR 0008). The Documents stay. The database cascades the deletes; the portrait
    files are removed after the commit, best effort."""
    application = db.session.get(JobApplication, application_id)
    if application is None:
        raise NotFoundError("Application not found.")
    # Read before the rows are gone: they say which files to remove.
    portraits = list(
        db.session.scalars(
            select(Interview.persona_image_path).where(
                Interview.job_application_id == application_id,
                Interview.persona_image_path.is_not(None),
            )
        )
    )
    db.session.delete(application)
    db.session.commit()
    remove_portrait_files(path for path in portraits if path is not None)

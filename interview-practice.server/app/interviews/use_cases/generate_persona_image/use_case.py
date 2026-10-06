import uuid

from flask import current_app
from sqlalchemy import update

from app.errors.exceptions import LlmUpstreamError, NotFoundError
from app.extensions import db
from app.interviews.shared import get_interview_or_404
from app.interviews.use_cases.generate_persona_image.portrait import (
    build_prompt,
    delete_portrait,
    store_portrait,
)
from app.llm.factory import get_llm_client
from app.llm.phase_settings import DEFAULT_IMAGE_MODEL
from app.llm.timing import timed
from app.models import Interview


def generate_persona_image(interview_id: uuid.UUID) -> str | None:
    """The URL of the persona's portrait, generating it if there isn't one yet.

    Called by the session page when it loads, not by Create Interview. Idempotent: an
    Interview that has a portrait answers with its URL and calls no model. None when
    portrait generation is switched off (`PORTRAIT_GENERATION_ENABLED`). A failure of
    the image service is an error the client can retry; nothing else is affected.
    """
    interview = get_interview_or_404(interview_id)
    if interview.persona_image_path is not None:
        return interview.persona_image_url
    if not current_app.config["PORTRAIT_GENERATION_ENABLED"]:
        return None

    prompt = build_prompt(
        interview.persona_name, interview.persona_title, interview.tone
    )
    with timed("portrait"):
        image = get_llm_client().generate_image(DEFAULT_IMAGE_MODEL, prompt)
    path = store_portrait(image)
    if path is None:
        raise LlmUpstreamError("The portrait could not be stored.")

    # Two calls at once may both have generated one: the first to store it wins. The
    # file is deleted unless this call's row update committed.
    try:
        stored = db.session.execute(
            update(Interview)
            .where(Interview.id == interview_id, Interview.persona_image_path.is_(None))
            .values(persona_image_path=path)
            .returning(Interview.id)
        ).scalar_one_or_none()
        db.session.commit()
    except BaseException:
        delete_portrait(path)
        raise
    if stored is None:
        delete_portrait(path)
    refreshed = db.session.get(Interview, interview_id, populate_existing=True)
    if refreshed is None:  # the Interview was deleted while the image was made
        raise NotFoundError("Interview not found.")
    return refreshed.persona_image_url

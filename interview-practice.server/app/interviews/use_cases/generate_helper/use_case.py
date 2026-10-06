import uuid

from sqlalchemy import update

from app.errors.exceptions import ConflictError, NotFoundError
from app.extensions import db
from app.interviews.shared import ensure_in_progress, get_interview_or_404
from app.interviews.use_cases.generate_helper.helper import write_helper
from app.llm.factory import get_llm_client
from app.llm.phase_settings import phase_config
from app.llm.timing import timed
from app.models import GenerationPhase, Message
from app.services.preferences import load_preferences


def generate_helper(interview_id: uuid.UUID, message_id: uuid.UUID) -> Message:
    """The message, with the coaching helper written for its question.

    Called by the session page after it shows a Q&A question, so the question never
    waits for the hint. Idempotent: a message that has a helper answers with it and
    calls no model. A helper the model could not write is not an error: the message
    comes back without one and the card is left out.

    It takes no turn claim, so the candidate can answer while the hint is being written.
    """
    interview = get_interview_or_404(interview_id)
    message = next((m for m in interview.messages if m.id == message_id), None)
    if message is None:
        raise NotFoundError("Message not found.")
    if message.helper_text is not None:
        return message
    if not interview.coaching_helpers_enabled:
        raise ConflictError(
            "Coaching helpers are off for this interview.", code="HELPERS_DISABLED"
        )
    if not message.is_question:
        raise ConflictError(
            "Only an interviewer's question has a coaching helper.",
            code="NOT_A_QUESTION",
        )
    ensure_in_progress(interview)

    model, settings = phase_config(
        GenerationPhase.coaching_helpers, interview.phase_settings, load_preferences()
    )
    with timed("helper"):
        text = write_helper(
            get_llm_client(), model, settings, interview, message.content
        )
    if text is None:
        return message

    # Two calls at once may both have written one: the first to store it wins.
    db.session.execute(
        update(Message)
        .where(Message.id == message_id, Message.helper_text.is_(None))
        .values(helper_text=text)
    )
    db.session.commit()
    stored = db.session.get(Message, message_id, populate_existing=True)
    if stored is None:  # the Interview was deleted while the model was writing
        raise NotFoundError("Message not found.")
    return stored

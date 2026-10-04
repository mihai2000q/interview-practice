import uuid

from flask import jsonify, request, send_file
from flask.typing import ResponseReturnValue

from app.interviews import interviews_bp
from app.interviews.schemas import (
    AskBackSuggestions,
    InterviewCreate,
    InterviewDetail,
    InterviewPublic,
    MessageCreate,
    MessageExchange,
)
from app.interviews.use_cases.abandon_interview import abandon_interview
from app.interviews.use_cases.create_interview import create_interview
from app.interviews.use_cases.get_ask_back_suggestions import (
    get_ask_back_suggestions,
)
from app.interviews.use_cases.get_interview import get_interview
from app.interviews.use_cases.get_persona_image import get_persona_image
from app.interviews.use_cases.send_message import send_message
from app.serialization import to_json


@interviews_bp.post("")
def post_interview() -> ResponseReturnValue:
    body = InterviewCreate.model_validate(request.get_json(silent=True) or {})
    return jsonify(to_json(InterviewPublic, create_interview(body))), 201


@interviews_bp.get("/<uuid:interview_id>")
def read_interview(interview_id: uuid.UUID) -> ResponseReturnValue:
    return jsonify(to_json(InterviewDetail, get_interview(interview_id)))


@interviews_bp.post("/<uuid:interview_id>/messages")
def post_message(interview_id: uuid.UUID) -> ResponseReturnValue:
    body = MessageCreate.model_validate(request.get_json(silent=True) or {})
    return jsonify(to_json(MessageExchange, send_message(interview_id, body.content)))


@interviews_bp.post("/<uuid:interview_id>/abandon")
def post_abandon(interview_id: uuid.UUID) -> ResponseReturnValue:
    return jsonify(to_json(InterviewDetail, abandon_interview(interview_id)))


@interviews_bp.get("/<uuid:interview_id>/ask-back-suggestions")
def fetch_ask_back_suggestions(interview_id: uuid.UUID) -> ResponseReturnValue:
    suggestions = AskBackSuggestions(suggestions=get_ask_back_suggestions(interview_id))
    return jsonify(suggestions.model_dump(mode="json"))


@interviews_bp.get("/<uuid:interview_id>/persona-image")
def fetch_persona_image(interview_id: uuid.UUID) -> ResponseReturnValue:
    response = send_file(get_persona_image(interview_id), max_age=3600)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

"""HTTP layer of the preferences API: read the request, call a use case, reply."""

from flask import jsonify, request
from flask.typing import ResponseReturnValue

from app.llm.schemas import PhaseSettingsOverride
from app.preferences import preferences_bp
from app.preferences.schemas import PreferencesPublic
from app.preferences.use_cases.read_preferences import read_preferences
from app.preferences.use_cases.update_preferences import update_preferences
from app.serialization import to_json


@preferences_bp.get("")
def get_preferences() -> ResponseReturnValue:
    return jsonify(to_json(PreferencesPublic, read_preferences()))


@preferences_bp.patch("")
def patch_preferences() -> ResponseReturnValue:
    body = PhaseSettingsOverride.model_validate(request.get_json(silent=True) or {})
    return jsonify(to_json(PreferencesPublic, update_preferences(body)))

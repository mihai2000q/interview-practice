"""HTTP layer of the applications API: read the request, call a use case, reply."""

from flask import jsonify
from flask.typing import ResponseReturnValue

from app.applications import applications_bp
from app.applications.schemas import ApplicationSummary
from app.applications.use_cases.list_applications import list_applications
from app.serialization import to_json_list


@applications_bp.get("")
def get_applications() -> ResponseReturnValue:
    return jsonify(to_json_list(ApplicationSummary, list_applications()))

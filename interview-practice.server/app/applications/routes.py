"""HTTP layer of the applications API: read the request, call a use case, reply."""

import uuid

from flask import jsonify
from flask.typing import ResponseReturnValue

from app.applications import applications_bp
from app.applications.schemas import ApplicationSummary
from app.applications.use_cases.delete_application import delete_application
from app.applications.use_cases.list_applications import list_applications
from app.serialization import to_json_list


@applications_bp.get("")
def get_applications() -> ResponseReturnValue:
    return jsonify(to_json_list(ApplicationSummary, list_applications()))


@applications_bp.delete("/<uuid:application_id>")
def delete_application_by_id(application_id: uuid.UUID) -> ResponseReturnValue:
    delete_application(application_id)
    return "", 204

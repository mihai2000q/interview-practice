"""HTTP layer of the dashboard API: call the use case, reply."""

from flask import jsonify
from flask.typing import ResponseReturnValue

from app.dashboard import dashboard_bp
from app.dashboard.schemas import DashboardPublic
from app.dashboard.use_cases.compute_dashboard import compute_dashboard
from app.serialization import to_json


@dashboard_bp.get("")
def get_dashboard() -> ResponseReturnValue:
    return jsonify(to_json(DashboardPublic, compute_dashboard()))

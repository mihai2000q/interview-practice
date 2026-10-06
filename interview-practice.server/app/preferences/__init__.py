from flask import Blueprint

preferences_bp = Blueprint("preferences", __name__, url_prefix="/api/preferences")

from app.preferences import routes  # noqa: E402, F401

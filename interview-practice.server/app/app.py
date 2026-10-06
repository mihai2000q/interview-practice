import os

from flask import Flask
from flask_cors import CORS

from app import models  # noqa: F401  (registers models so Alembic sees them)
from app.applications import applications_bp
from app.dashboard import dashboard_bp
from app.documents import documents_bp
from app.errors.handlers import register_error_handlers
from app.extensions import db, migrate
from app.interviews import interviews_bp
from config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    client_host = os.environ.get("CLIENT_HOST", "localhost")
    client_port = os.environ.get("CLIENT_PORT", "8002")
    CORS(app, origins=[f"http://{client_host}:{client_port}"])

    db.init_app(app)
    migrate.init_app(app, db)

    register_error_handlers(app)
    app.register_blueprint(documents_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(interviews_bp)
    app.register_blueprint(dashboard_bp)

    return app

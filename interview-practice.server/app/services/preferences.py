"""The Preferences defaults that every LLM phase falls back to."""

from sqlalchemy import select

from app.extensions import db
from app.models import PreferencePhaseSettings


def load_preferences() -> list[PreferencePhaseSettings]:
    """The stored Preferences rows: one per phase the developer customized."""
    return list(db.session.scalars(select(PreferencePhaseSettings)))

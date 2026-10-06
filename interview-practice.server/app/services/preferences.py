"""The Preferences defaults that every LLM phase falls back to."""

from sqlalchemy import func, select

from app.extensions import db
from app.models import PreferencePhaseSettings

# An arbitrary key naming the Preferences' update lock, "pref" in hex.
_UPDATE_LOCK_KEY = 0x70726566


def lock_preferences() -> None:
    """Wait until no other update of the Preferences is running, and keep others out
    until this transaction ends.

    Updating is read, check the judge rule, write: two updates at once would each check
    against rows the other is about to change, and could both insert the row of a phase
    that has none yet. Take it before `load_preferences()`. Postgres only: it is an
    advisory lock. Readers (`create_interview`, `generate_evaluation`) don't take it on
    purpose: `load_preferences()` is one query, so it sees the Preferences either
    before or after an update, never half of one, and waiting would hold a request
    for an LLM call.
    """
    db.session.execute(select(func.pg_advisory_xact_lock(_UPDATE_LOCK_KEY)))


def load_preferences() -> list[PreferencePhaseSettings]:
    """The stored Preferences rows: one per phase the developer customized."""
    return list(db.session.scalars(select(PreferencePhaseSettings)))

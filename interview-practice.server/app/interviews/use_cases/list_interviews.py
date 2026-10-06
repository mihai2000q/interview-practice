from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Evaluation, Interview
from app.services.interview_lifecycle import settle_all_stale


def list_interviews() -> list[Interview]:
    """Every Interview, newest first, with its Evaluation if one is stored.

    Stale sessions are closed before reading (ADR 0006), so a dead one never shows as
    running. Only the Evaluation's verdict is loaded, and none is ever generated here.
    """
    settle_all_stale()
    statement = (
        select(Interview)
        .options(joinedload(Interview.evaluation).load_only(Evaluation.verdict))
        .order_by(Interview.created_at.desc())
    )
    return list(db.session.scalars(statement))

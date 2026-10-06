"""Results: the Evaluation of the candidate and the InterviewerReview, made together.

Both are asked for at once on worker threads, so the candidate waits for the slower of
the two, not for their sum. The review is a dev-facing extra: if its call fails the
Evaluation is still stored and returned, and the review is simply missing. Neither is
generated when the Interview ends, so ending it stays fast (ADR 0014).
"""

import dataclasses
import logging
import uuid
from collections.abc import Callable
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.errors.exceptions import ApiError, ConflictError, NotFoundError
from app.extensions import db
from app.interviews.shared import get_interview_or_404
from app.interviews.use_cases.generate_evaluation.evaluation import (
    EvaluationDraft,
    evaluate,
)
from app.interviews.use_cases.generate_evaluation.evaluation import (
    build_messages as evaluation_messages,
)
from app.interviews.use_cases.generate_evaluation.review import (
    ReviewDraft,
    review_interviewer,
)
from app.interviews.use_cases.generate_evaluation.review import (
    build_messages as review_messages,
)
from app.interviews.use_cases.generate_evaluation.transcript import (
    has_candidate_message,
)
from app.llm.concurrency import fan_out
from app.llm.factory import get_llm_client
from app.llm.phase_settings import phase_config
from app.llm.timing import timed
from app.models import (
    Evaluation,
    GenerationPhase,
    Interview,
    InterviewerReview,
    InterviewStatus,
)
from app.services.preferences import load_preferences

logger = logging.getLogger(__name__)


def generate_evaluation(interview_id: uuid.UUID) -> Evaluation:
    """The Interview's Evaluation, generated now if it has none yet.

    Idempotent: an Interview that has an Evaluation answers with it and calls no
    model. Two calls at once may both run the models; the first to store wins and both
    get that one. The review is not retried here once the Evaluation exists, so a
    Results page that reloads never waits on it again.
    """
    interview = get_interview_or_404(interview_id)
    if interview.evaluation is not None:
        return interview.evaluation
    _ensure_can_be_evaluated(interview)

    client = get_llm_client()
    preferences = load_preferences()
    eval_model, eval_settings = phase_config(
        GenerationPhase.evaluation, interview.phase_settings, preferences
    )
    judge_model, judge_settings = phase_config(
        GenerationPhase.interviewer_review, interview.phase_settings, preferences
    )
    # The prompts are built here, from the ORM objects: the jobs get plain data only.
    eval_prompt = evaluation_messages(interview)
    review_prompt = review_messages(interview)

    def run_evaluation() -> EvaluationDraft:
        with timed("evaluation"):
            return evaluate(client, eval_model, eval_settings, eval_prompt)

    def run_review() -> ReviewDraft | None:
        try:
            with timed("review"):
                return review_interviewer(
                    client, judge_model, judge_settings, review_prompt
                )
        except ApiError as exc:
            logger.error("Interviewer review failed (%s): %s", exc.code, exc.message)
            return None

    with timed("results"):
        jobs: list[Callable[[], EvaluationDraft | ReviewDraft | None]] = [
            run_evaluation,
            run_review,
        ]
        evaluation, review = fan_out(jobs)
    return _store(
        interview,
        cast(EvaluationDraft, evaluation),
        cast(ReviewDraft | None, review),
        eval_model=eval_model,
        judge_model=judge_model,
    )


def _ensure_can_be_evaluated(interview: Interview) -> None:
    if interview.status is InterviewStatus.in_progress:
        raise ConflictError(
            "The interview hasn't ended yet.", code="INTERVIEW_NOT_ENDED"
        )
    if not has_candidate_message(interview):
        raise ConflictError(
            "The candidate never replied, so there is nothing to evaluate.",
            code="NOTHING_TO_EVALUATE",
        )


def _store(
    interview: Interview,
    evaluation: EvaluationDraft,
    review: ReviewDraft | None,
    *,
    eval_model: str,
    judge_model: str,
) -> Evaluation:
    """Store the results, keeping any another call stored first, and return the
    Evaluation that now holds."""
    interview_id = interview.id
    try:
        db.session.execute(
            insert(Evaluation)
            .values(
                interview_id=interview_id,
                incomplete=interview.status is InterviewStatus.abandoned,
                model_used=eval_model,
                **dataclasses.asdict(evaluation),
            )
            .on_conflict_do_nothing(index_elements=["interview_id"])
        )
        if review is not None:
            db.session.execute(
                insert(InterviewerReview)
                .values(
                    interview_id=interview_id,
                    judge_model=judge_model,
                    **dataclasses.asdict(review),
                )
                .on_conflict_do_nothing(index_elements=["interview_id"])
            )
        db.session.commit()
    except IntegrityError as exc:  # the Interview was deleted while the models worked
        db.session.rollback()
        raise NotFoundError("Interview not found.") from exc

    stored = db.session.scalar(
        select(Evaluation)
        .where(Evaluation.interview_id == interview_id)
        .execution_options(populate_existing=True)
    )
    if stored is None:
        raise NotFoundError("Interview not found.")
    return stored

"""Phase 2: the interview plan, made by three independent calls run at once.

Instruction/constraint-based prompting (docs/architecture.md): the structured inputs
(difficulty, domain, seniority, interview type, role, company, phase-1 analyses) become
explicit constraints rather than worked examples. The persona, the questions and the
evaluation criteria depend only on those inputs, not on each other, so the plan takes as
long as the slowest of the three instead of one long reply. Any one failing fails the
plan, and the others are abandoned.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import cast

from app.interviews.schemas import InterviewCreate
from app.interviews.use_cases.create_interview.planning.criteria import (
    CriterionDraft,
    generate_criteria,
)
from app.interviews.use_cases.create_interview.planning.inputs import company_of
from app.interviews.use_cases.create_interview.planning.persona import (
    PersonaDraft,
    generate_persona,
)
from app.interviews.use_cases.create_interview.planning.questions import (
    QuestionDraft,
    generate_questions,
)
from app.llm.concurrency import fan_out
from app.llm.openrouter import CompletionSettings, OpenRouterClient
from app.services.document_analysis import JobContext

# For Interviews with no analyzed domain when the model gives none either.
FALLBACK_DOMAIN = "general"


@dataclass(frozen=True)
class InterviewPlan:
    domain: str  # the analyzed one, else the model's, else a placeholder
    company_name: str | None  # the candidate's, else the documents'
    persona_name: str
    persona_title: str
    persona_backstory: str
    questions: list[QuestionDraft]
    evaluation_criteria: list[CriterionDraft]


def plan_interview(
    client: OpenRouterClient,
    model: str,
    settings: CompletionSettings,
    request: InterviewCreate,
    context: JobContext,
) -> InterviewPlan:
    """Run phase 2. The domain is asked of the model only when the context has none."""
    jobs: list[Callable[[], object]] = [
        partial(generate_persona, client, model, settings, request, context),
        partial(generate_questions, client, model, settings, request, context),
        partial(generate_criteria, client, model, settings, request, context),
    ]
    results = fan_out(jobs)
    persona = cast(PersonaDraft, results[0])
    questions = cast(list[QuestionDraft], results[1])
    criteria = cast(list[CriterionDraft], results[2])
    return InterviewPlan(
        domain=context.domain or persona.domain or FALLBACK_DOMAIN,
        company_name=company_of(request, context),
        persona_name=persona.name,
        persona_title=persona.title,
        persona_backstory=persona.backstory,
        questions=questions,
        evaluation_criteria=criteria,
    )

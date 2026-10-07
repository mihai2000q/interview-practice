"""The benchmark's tasks: build each prompt with the app's own code, and score replies.

Prompts are NOT re-written here. Each task calls the real `build_messages` of the phase
(and the real Pydantic reply model), so what is measured is what the app sends. The only
edits are the experimental variants (zero-shot ask-back, evaluation without the
scratchpad), made by removing text from the real prompt and asserting the removal worked.
"""

import itertools
import re
import statistics
import sys
from pathlib import Path
from typing import Any

SERVER = Path(__file__).resolve().parent.parent / "interview-practice.server"
sys.path.insert(0, str(SERVER))

from pydantic import BaseModel  # noqa: E402

import fixtures as fx  # noqa: E402
from app.applications.use_cases.generate_progress import summary as progress_mod  # noqa: E402
from app.interviews.schemas import InterviewCreate  # noqa: E402
from app.interviews.shared.exchange import conversation as live_mod  # noqa: E402
from app.interviews.shared.exchange.pacing import ExchangeKind  # noqa: E402
from app.interviews.use_cases.create_interview.planning import (  # noqa: E402
    criteria as criteria_mod,
)
from app.interviews.use_cases.create_interview.planning import (  # noqa: E402
    persona as persona_mod,
)
from app.interviews.use_cases.create_interview.planning import (  # noqa: E402
    questions as questions_mod,
)
from app.interviews.use_cases.create_interview.planning.limits import plan_range  # noqa: E402
from app.interviews.use_cases.generate_evaluation import evaluation as eval_mod  # noqa: E402
from app.interviews.use_cases.generate_evaluation import review as review_mod  # noqa: E402
from app.interviews.use_cases.generate_helper import helper as helper_mod  # noqa: E402
from app.interviews.use_cases.get_ask_back_suggestions import (  # noqa: E402
    suggestions as askback_mod,
)
from app.llm.guard import fence  # noqa: E402
from app.models import (  # noqa: E402
    Difficulty,
    Document,
    DocumentAnalysis,
    DocumentType,
    Evaluation,
    EvaluationCriterion,
    Interview,
    InterviewCategory,
    InterviewQuestion,
    InterviewStatus,
    Message,
    MessagePhase,
    MessageRole,
    StarCompleteness,
    Verdict,
)
from app.services.document_analysis import JobContext, extraction  # noqa: E402
from tests.support import build_interview  # noqa: E402

SETUP = {s["id"]: s for s in fx.SETUPS}
DOC = {d["id"]: d for d in fx.DOCUMENTS}
EVAL = {c["id"]: c for c in fx.EVAL_CASES}


# --------------------------------------------------------------------------- helpers
def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:['-][a-z0-9]+)*", text.lower())


def jaccard(a: str, b: str) -> float:
    sa, sb = set(words(a)), set(words(b))
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else float("nan")


def pairwise_distance(texts: list[str]) -> float:
    """1 - the mean pairwise word overlap: 0 = identical, 1 = nothing in common."""
    pairs = list(itertools.combinations(texts, 2))
    return 1 - mean([jaccard(a, b) for a, b in pairs]) if pairs else float("nan")


def _msg(role: str, phase: str, text: str, number: int, clar: bool) -> Message:
    return Message(
        role=MessageRole(role),
        phase=MessagePhase(phase),
        content=text,
        sequence=number,
        is_clarification=clar,
    )


def make_interview(
    *,
    job_title: str,
    seniority: str,
    domain: str,
    difficulty: str,
    tone: str,
    itype: str,
    role: str,
    company: str | None,
    persona: tuple[str, str, str],
    messages: list[tuple[Any, ...]],
    plan: list[tuple[str, str]] | None = None,
    criteria: list[tuple[str, str]] | None = None,
    target: int = 4,
    status: InterviewStatus = InterviewStatus.completed,
    style: str = "concise",
    **extra: Any,
) -> Interview:
    """An unsaved Interview carrying the given transcript."""
    from app.models import ResponseStyle

    interview = build_interview(
        target=target,
        job_title=job_title,
        seniority=seniority,
        domain=domain,
        difficulty=Difficulty(difficulty),
        tone=tone,
        interview_type=itype,
        interviewer_role=role,
        company_name=company,
        persona_name=persona[0],
        persona_title=persona[1],
        persona_backstory=persona[2],
        status=status,
        response_style=ResponseStyle(style),
        questions=[
            InterviewQuestion(
                sequence=n, category=InterviewCategory(cat), question=text
            )
            for n, (cat, text) in enumerate(plan or [("technical", "q")], start=1)
        ],
        evaluation_criteria=[
            EvaluationCriterion(
                sequence=n, category=InterviewCategory(cat), criterion=text
            )
            for n, (cat, text) in enumerate(criteria or [], start=1)
        ],
        **extra,
    )
    for number, message in enumerate(messages, start=1):
        role_, phase, text = message[:3]
        clar = len(message) > 3 and bool(message[3])
        interview.messages.append(_msg(role_, phase, text, number, clar))
    return interview


def _document(
    kind: str,
    text: str,
    skills: list[str],
    topics: list[str],
    company: str | None,
    domain: str | None,
) -> Document:
    doc = Document(
        type=DocumentType(kind),
        name="n",
        raw_text=text,
        source_filename="f",
        file_path="x",
    )
    doc.analysis = DocumentAnalysis(
        model="m",
        skills=skills,
        likely_topics=topics,
        company_name=company,
        domain=domain,
    )
    return doc


# ------------------------------------------------------------- 1. document analysis
def doc_messages(doc: dict[str, Any]) -> list[Any]:
    return extraction.build_messages(DocumentType(doc["type"]), doc["text"])


DOC_SCHEMA = extraction._AnalysisReply


def doc_metrics(record: dict[str, Any], doc: dict[str, Any], parsed: Any) -> dict:
    from harness import parse  # noqa: F401  (kept for symmetry)

    if parsed is None:
        return {"valid": 0}
    skills = [s.strip().lower() for s in parsed.skills if s.strip()]
    topics = [t.strip().lower() for t in parsed.likely_topics if t.strip()]
    company = (parsed.company_name or "").strip()
    if company.lower() in extraction._NOT_A_COMPANY:
        company = ""
    domain = (parsed.domain or "").strip().lower()
    text = doc["text"].lower()
    out: dict[str, float] = {"valid": 1}
    if doc["gold_skills"]:
        hits = sum(
            any(g.lower() in s or s in g.lower() for s in skills)
            for g in doc["gold_skills"]
        )
        out["skill_recall"] = hits / len(doc["gold_skills"])
        stop = {"and", "the", "for", "with", "experience", "skills", "knowledge"}
        unsupported = [
            s
            for s in skills
            if not any(w in text for w in words(s) if len(w) >= 3 and w not in stop)
        ]
        out["unsupported_skills"] = len(unsupported)
    blob = " ".join([*skills, *topics, domain, company.lower()])
    out["forbidden_hit"] = int(
        any(
            re.search(r"\b" + re.escape(f.strip().lower()) + r"\b", blob)
            for f in doc["forbidden"]
        )
    )
    if doc["type"] != "cv":
        gold_company = doc["company"]
        if gold_company is None:
            out["company_ok"] = int(company == "")
        else:
            out["company_ok"] = int(gold_company.lower() in company.lower())
    out["domain_ok"] = int(
        any(k in domain for k in doc["domain_any"]) and "finance" not in domain
        if doc.get("injection")
        else any(k in domain for k in doc["domain_any"])
    )
    return out


# -------------------------------------------------------------------- 2. the plan
def create_request(setup: dict[str, Any], target: int = 5) -> InterviewCreate:
    return InterviewCreate.model_validate(
        {
            "job_title": setup["job_title"],
            "company_name": setup["company"],
            "seniority": setup["seniority"],
            "difficulty": setup["difficulty"],
            "target_question_count": target,
            "tone": setup["tone"],
            "interview_type": setup["type"],
            "interviewer_role": setup["role"],
            "response_style": "concise",
            "coaching_helpers_enabled": False,
        }
    )


def job_context(setup: dict[str, Any]) -> JobContext:
    def block(label: str, skills: list[str], topics: list[str]) -> str:
        return fence(
            label,
            f"skills: {', '.join(skills)}\ntopics: {', '.join(topics) or '(none)'}",
        )

    return JobContext(
        company_name=setup["company"],
        domain=setup["domain"],
        job_text=block("job_analysis", setup["jd_skills"], setup["jd_topics"]),
        candidate_text=block("candidate_analysis", setup["cv_skills"], []),
    )


def plan_messages(setup: dict[str, Any], target: int = 5) -> dict[str, list[Any]]:
    """The three phase-2 prompts, built exactly as the planning modules build them."""
    from app.interviews.shared.guidance import (
        DIFFICULTY_GUIDANCE,
        ROLE_GUIDANCE,
        TONE_GUIDANCE,
    )
    from app.interviews.use_cases.create_interview.planning.inputs import (
        company_of,
        setup_and_analyses,
        setup_block,
    )
    from app.llm.openrouter import ChatMessage

    request, context = create_request(setup, target), job_context(setup)
    low, high = plan_range(target)
    company = company_of(request, context)
    persona_system = persona_mod._SYSTEM_PROMPT.format(
        role=ROLE_GUIDANCE[request.interviewer_role],
        tone=TONE_GUIDANCE[request.tone],
        company=(
            " The interviewer works at the company named in the setup, so their "
            "title and backstory must fit it."
            if company
            else ""
        ),
        keys=persona_mod._DOMAIN_KEY + persona_mod._PERSONA_KEY,
    )
    questions_system = questions_mod._SYSTEM_PROMPT.format(
        low=low,
        high=high,
        target=target,
        skew=questions_mod._skew(request.interview_type),
        difficulty=DIFFICULTY_GUIDANCE[request.difficulty.value],
        role=ROLE_GUIDANCE[request.interviewer_role],
        company=(
            " At least one question must test what the candidate knows about "
            "the company and why they want to work there."
            if company
            else ""
        ),
        previous="",
    )
    return {
        "persona": [
            ChatMessage("system", persona_system),
            ChatMessage("user", setup_block(request, context)),
        ],
        "questions": [
            ChatMessage("system", questions_system),
            ChatMessage("user", setup_and_analyses(request, context)),
        ],
        "criteria": [
            ChatMessage("system", criteria_mod._SYSTEM_PROMPT),
            ChatMessage("user", setup_and_analyses(request, context)),
        ],
    }


ROLE_TITLE_WORDS = {
    "recruiter": ["recruit", "talent", "acquisition", "sourc", "hiring", "people"],
    "hr": ["hr", "people", "human", "talent", "culture", "operations"],
    "technical_screener": [
        "engineer",
        "developer",
        "architect",
        "scientist",
        "lead",
        "sre",
        "reliability",
        "analyst",
        "devops",
    ],
    "hiring_manager": ["manager", "head", "director", "lead", "vp", "chief"],
}
LOW_LEVEL = [
    "algorithm",
    "complexity",
    "big o",
    "index",
    "kafka",
    "terraform",
    "kubernetes",
    "recursion",
    "thread",
    "mutex",
    "latency",
    "sql query",
    "api design",
    "cache invalidation",
    "garbage",
]
SELF_AWARE = re.compile(
    r"fail|weakness|mistake|feedback|coachab|growth|self-aware"
    r"|learn from|ownership",
    re.I,
)


def persona_metrics(parsed: Any, setup: dict[str, Any]) -> dict[str, float]:
    if parsed is None:
        return {"valid": 0}
    p = parsed.persona
    ok = bool(p.name.strip() and p.title.strip() and p.backstory.strip())
    title = p.title.lower()
    sentences = len([s for s in re.split(r"(?<=[.!?])\s+", p.backstory.strip()) if s])
    return {
        "valid": int(ok),
        "title_fits_role": int(
            any(w in title for w in ROLE_TITLE_WORDS[setup["role"]])
        ),
        "backstory_3_5_sentences": int(3 <= sentences <= 5),
        "states_limits": int(
            bool(
                re.search(
                    r"\b(not|never|no experience|limited|outside|does n.t|doesn.t)\b",
                    p.backstory,
                    re.I,
                )
            )
        ),
    }


def questions_metrics(parsed: Any, setup: dict[str, Any], target: int = 5) -> dict:
    low, high = plan_range(target)
    if parsed is None:
        return {"valid": 0}
    qs = [q for q in parsed.questions if q.question.strip()]
    n = len(qs)
    out: dict[str, float] = {
        "valid": int(n >= low),
        "count_in_range": int(low <= n <= high),
    }
    if n:
        share = sum(q.category.value == setup["type"] for q in qs) / n
        out["skew_ok"] = int(share >= 0.7)
    if setup["company"]:
        key = setup["company"].lower().split()[0]
        out["mentions_company"] = int(any(key in q.question.lower() for q in qs))
    if setup["role"] in ("recruiter", "hr"):
        out["low_level_questions"] = sum(
            any(w in q.question.lower() for w in LOW_LEVEL) for q in qs
        )
    return out


def criteria_metrics(parsed: Any) -> dict[str, float]:
    if parsed is None:
        return {"valid": 0}
    items = [c for c in parsed.evaluation_criteria if c.criterion.strip()]
    counts = {
        cat: sum(c.category.value == cat for c in items)
        for cat in ("technical", "behavioral")
    }
    return {
        "valid": int(bool(items)),
        "counts_4_8": int(all(4 <= n <= 8 for n in counts.values())),
        "has_self_awareness": int(
            any(
                c.category.value == "behavioral" and SELF_AWARE.search(c.criterion)
                for c in items
            )
        ),
    }


# ------------------------------------------------------- 3. live interviewer turn
def live_interview(setup: dict[str, Any]) -> Interview:
    return make_interview(
        job_title=setup["job_title"],
        seniority=setup["seniority"],
        domain=setup["domain"],
        difficulty=setup["difficulty"],
        tone=setup["tone"],
        itype=setup["type"],
        role=setup["role"],
        company=setup["company"],
        persona=setup["persona"],
        messages=[],
        plan=setup["plan"],
        target=4,
        status=InterviewStatus.in_progress,
    )


def live_messages(
    setup: dict[str, Any],
    kind: str,
    asked: int,
    streak: int,
    transcript: list[tuple[str, str]],
) -> list[Any]:
    return live_mod.build_messages(
        live_interview(setup),
        [(MessageRole(r), t) for r, t in transcript],
        ExchangeKind(kind),
        asked,
        streak,
    )


LIVE_SCHEMA = live_mod._Reply


def live_metrics(parsed: Any, case: dict[str, Any], setup: dict[str, Any]) -> dict:
    if parsed is None:
        return {"valid": 0}
    msg = parsed.message.strip()
    expect = case["expect"]
    kind = ExchangeKind(case["kind"])
    contract = bool(msg) and (
        parsed.done
        if kind in live_mod._MUST_BE_DONE
        else (not parsed.done if kind in live_mod._MUST_NOT_BE_DONE else True)
    )
    out: dict[str, float] = {
        "valid": int(contract),
        "short_enough": int(len(msg) <= 2000),
        "no_ai_leak": int(
            not re.search(
                r"\b(as an ai|language model|my prompt|my instructions|question plan)\b",
                msg,
                re.I,
            )
        ),
    }
    if "done" in expect:
        out["done_ok"] = int(parsed.done is expect["done"])
    if "clarification" in expect:
        out["clarification_ok"] = int(parsed.clarification is expect["clarification"])
    if expect.get("one_question"):
        out["one_question"] = int(msg.count("?") <= 1)
    if expect.get("no_figures"):
        out["no_invented_figure"] = int(not re.search(r"\d", msg))
    if case["kind"] == "open":
        out["introduces_self"] = int(
            setup["persona"][0].split()[0].lower() in msg.lower()
        )
    return out


# ------------------------------------------------------------- 4. ask-back suggestions
ASKBACK_SCHEMA = askback_mod._SuggestionsReply
_EXAMPLE_QUESTIONS = re.findall(r'"([^"]+\?)"', askback_mod._EXAMPLES)


def askback_interview(setup: dict[str, Any]) -> Interview:
    messages: list[tuple[Any, ...]] = []
    for number, (question, answer) in enumerate(setup["qa"]):
        text = (
            "Hello, I am " + setup["persona"][0].split()[0] + ". " + question
            if number == 0
            else question
        )
        messages += [("interviewer", "qa", text), ("candidate", "qa", answer)]
    messages.append(
        (
            "interviewer",
            "ask_back",
            "That is everything I wanted to ask. Do you have any questions for me?",
        )
    )
    return make_interview(
        job_title=setup["job_title"],
        seniority=setup["seniority"],
        domain=setup["domain"],
        difficulty=setup["difficulty"],
        tone=setup["tone"],
        itype=setup["type"],
        role=setup["role"],
        company=setup["company"],
        persona=setup["persona"],
        messages=messages,
        target=2,
        status=InterviewStatus.in_progress,
        helpers=True,
    )


def askback_messages(setup: dict[str, Any], arm: str) -> list[Any]:
    from app.llm.openrouter import ChatMessage

    messages = askback_mod.build_messages(askback_interview(setup))
    if arm == "few":
        return messages
    system = messages[0].content
    stripped = re.sub(
        r"Below are examples.*?(?=Reply with a single JSON)", "", system, flags=re.S
    )
    assert stripped != system and "Example 1" not in stripped, "zero-shot edit failed"
    return [ChatMessage("system", stripped), messages[1]]


def _specificity_tokens(setup: dict[str, Any]) -> set[str]:
    bag = [
        setup["job_title"],
        setup["company"] or "",
        *setup["jd_skills"],
        *setup["jd_topics"],
        setup["domain"],
    ]
    tokens = {w for text in bag for w in words(text) if len(w) >= 4}
    answers = " ".join(a for _, a in setup["qa"])
    tokens |= {w for w in words(answers) if len(w) >= 6}
    return tokens - {"engineer", "senior", "junior", "manager"}


def askback_metrics(parsed: Any, setup: dict[str, Any]) -> dict[str, float]:
    if parsed is None:
        return {"valid": 0, "app_ok": 0}
    unique = list(
        dict.fromkeys(s.strip()[:200] for s in parsed.suggestions if s.strip())
    )
    ok = len(unique) >= askback_mod.SUGGESTION_COUNT
    five = unique[:5]
    if not five:
        return {"valid": 1, "app_ok": 0}
    tokens = _specificity_tokens(setup)
    out: dict[str, float] = {
        "valid": 1,
        "app_ok": int(ok),
        "within_25_words": mean([len(s.split()) <= 25 for s in five]),
        "question_form": mean([s.endswith("?") for s in five]),
        "copies_example": mean(
            [max(jaccard(s, ex) for ex in _EXAMPLE_QUESTIONS) >= 0.6 for s in five]
        ),
        "distinct_in_set": pairwise_distance(five),
        "specific": mean([bool(tokens & set(words(s))) for s in five]),
    }
    if setup["company"]:
        key = setup["company"].lower().split()[0]
        out["mentions_company"] = mean([key in s.lower() for s in five])
    return out


# ------------------------------------------------------------------ 5. evaluation
EVAL_SCHEMA = eval_mod._Reply


class EvalNoScratch(BaseModel):
    """`evaluation._Reply` without the `analysis` key (the no-scratchpad arm)."""

    verdict: Verdict
    reasoning: str
    strengths: list[str]
    weaknesses: list[str]
    improvement_suggestions: list[str]
    star_situation: str
    star_task: str
    star_action: str
    star_result: str
    star_completeness: StarCompleteness


def eval_interview(case: dict[str, Any]) -> Interview:
    return make_interview(
        job_title=case["job_title"],
        seniority=case["seniority"],
        domain=case["domain"],
        difficulty=case["difficulty"],
        tone=case["tone"],
        itype=case["interview_type"],
        role=case["role"],
        company=case["company"],
        persona=case["persona"],
        messages=case["messages"],
        criteria=case["criteria"],
        target=4,
        status=InterviewStatus.completed,
    )


def eval_messages(case: dict[str, Any], arm: str) -> list[Any]:
    from app.llm.openrouter import ChatMessage

    messages = eval_mod.build_messages(eval_interview(case))
    if arm == "scratch":
        return messages
    system = messages[0].content
    system2 = system.replace(
        "Think first, then answer. Reply with a single JSON object",
        "Reply with a single JSON object",
    )
    system2 = re.sub(
        r'- "analysis":.*?Not shown to the candidate\.\n', "", system2, flags=re.S
    )
    assert "analysis" not in system2 and "Think first" not in system2, "edit failed"
    return [ChatMessage("system", system2), messages[1]]


def _candidate_text(case: dict[str, Any]) -> str:
    return " ".join(m[2] for m in case["messages"] if m[0] == "candidate")


def _grounded(item: str, candidate_text: str) -> bool:
    cand = words(candidate_text)
    grams = {tuple(cand[i : i + 4]) for i in range(len(cand) - 3)}
    toks = words(item)
    if any(tuple(toks[i : i + 4]) in grams for i in range(len(toks) - 3)):
        return True
    distinct = {w for w in toks if (len(w) >= 7 or any(c.isdigit() for c in w))}
    return len(distinct & set(cand)) >= 2


def eval_metrics(parsed: Any, case: dict[str, Any]) -> dict[str, float]:
    if parsed is None:
        return {"valid": 0}
    complete = all(
        [
            parsed.reasoning.strip(),
            [s for s in parsed.strengths if s.strip()],
            [s for s in parsed.weaknesses if s.strip()],
            [s for s in parsed.improvement_suggestions if s.strip()],
            parsed.star_situation.strip(),
            parsed.star_task.strip(),
            parsed.star_action.strip(),
            parsed.star_result.strip(),
        ]
    )
    items = [*parsed.strengths, *parsed.weaknesses]
    text = _candidate_text(case)
    out: dict[str, float] = {
        "valid": int(bool(complete)),
        
        "hire": int(parsed.verdict.value == "hire"),
        "grounded_share": mean([_grounded(i, text) for i in items if i.strip()]),
    }
    if not case.get("probe"):
        out["verdict_correct"] = int(parsed.verdict.value == case["gold"])
    if case.get("probe"):
        blob = " ".join(parsed.weaknesses) + " " + parsed.reasoning
        out["cites_wrong_claim"] = int(bool(re.search(r"compiled", blob, re.I)))
        out["says_unverifiable"] = int(bool(re.search(
            r"unverif|could not (be )?verif|cannot (be )?verif|not verif|can.t verify",
            blob, re.I)))
    if "gold_star" in case:
        out["star_correct"] = int(parsed.star_completeness.value == case["gold_star"])
    return out


# ---------------------------------------------------------------- 6. coaching hint
HINT_SCHEMA = helper_mod._HintReply


def hint_messages(case: dict[str, Any]) -> list[Any]:
    setup = SETUP[case["setup"]]
    doc = DOC.get(case["doc"]) if case["doc"] else None
    cv = (
        _document("cv", doc["text"], doc["gold_skills"], [], None, None)
        if doc
        else None
    )
    jd = _document(
        "job_description",
        "job ad",
        setup["jd_skills"],
        setup["jd_topics"],
        setup["company"],
        setup["domain"],
    )
    interview = make_interview(
        job_title=setup["job_title"],
        seniority=setup["seniority"],
        domain=setup["domain"],
        difficulty=setup["difficulty"],
        tone=setup["tone"],
        itype=setup["type"],
        role=setup["role"],
        company=setup["company"],
        persona=setup["persona"],
        messages=[],
        job_description_document=jd,
        cv_document=cv,
        cover_letter_document=None,
    )
    return helper_mod.build_messages(interview, case["question"])


def hint_metrics(parsed: Any, case: dict[str, Any]) -> dict[str, float]:
    if parsed is None:
        return {"valid": 0}
    hint = parsed.hint.strip()
    out: dict[str, float] = {
        "valid": int(bool(hint)),
        "within_40_words": int(len(hint.split()) <= 40),
        "within_2_sentences": int(len(re.findall(r"[.!?](?:\s|$)", hint)) <= 2),
    }
    if case.get("must_mention_any"):
        out["names_cv_item"] = int(
            any(k in hint.lower() for k in case["must_mention_any"])
        )
    return out


# ------------------------------------------------------- 7. interviewer review (judge)
JUDGE_SCHEMA = review_mod._Reply


def judge_interview(case: dict[str, Any]) -> Interview:
    return make_interview(
        job_title="Backend Engineer",
        seniority="mid",
        domain="backend engineering",
        difficulty="easy",
        tone="friendly",
        itype="behavioral",
        role="recruiter",
        company="Northwind Logistics",
        persona=fx._JPERSONA,
        messages=case["messages"],
        plan=case["plan"],
        target=case["target"],
        status=InterviewStatus.completed,
    )


def judge_messages(case: dict[str, Any]) -> list[Any]:
    return review_mod.build_messages(judge_interview(case))


# ----------------------------------------------------------------- 8. progress summary
PROGRESS_SCHEMA = progress_mod._Reply


def progress_messages(case: dict[str, Any]) -> list[Any]:
    stages = []
    for stage in case["stages"]:
        interview = make_interview(
            job_title="Backend Engineer",
            seniority="mid",
            domain="backend engineering",
            difficulty=stage["difficulty"],
            tone=stage["tone"],
            itype=stage["type"],
            role=stage["role"],
            company="Northwind Logistics",
            persona=("A", "B", "C"),
            messages=[],
            criteria=[
                ("technical", "Explains trade-offs"),
                ("behavioral", "Gives specific examples"),
            ],
            status=(
                InterviewStatus.abandoned
                if stage["partial"]
                else InterviewStatus.completed
            ),
        )
        interview.evaluation = Evaluation(
            verdict=Verdict(stage["verdict"]),
            reasoning=stage["reasoning"],
            strengths="s",
            weaknesses="w",
            improvement_suggestions=stage["suggestion"],
            star_situation="situation",
            star_task="task",
            star_action="action",
            star_result="result",
            star_completeness=StarCompleteness(stage["star"]),
            model_used="m",
        )
        stages.append(interview)
    return progress_mod.build_messages(stages)


def progress_metrics(parsed: Any, case: dict[str, Any]) -> dict[str, float]:
    if parsed is None:
        return {"valid": 0}
    summary = parsed.summary.strip()
    low, high = case["score_range"]
    sentences = len(re.findall(r"[.!?](?:\s|$)", summary))
    roles = [s["role"].replace("_", " ") for s in case["stages"]]
    out: dict[str, float] = {
        "valid": int(bool(summary)),
        "score_in_range": int(low <= parsed.score <= high),
        "sentences_3_to_6": int(3 <= sentences <= 6),
        "second_person": int(bool(re.search(r"\byou(r)?\b", summary, re.I))),
        "names_stages": mean([r.split()[0] in summary.lower() for r in roles]),
    }
    if case["trend"] == "up":
        out["trend_ok"] = int(
            bool(
                re.search(
                    r"improv|progress|stronger|better|growth|grew|rose|step up",
                    summary,
                    re.I,
                )
            )
        )
    if case["trend"] == "down":
        out["trend_ok"] = int(
            bool(
                re.search(
                    r"declin|slip|weaker|dropped|worse|fell|regress|drop|less",
                    summary,
                    re.I,
                )
            )
        )
    return out

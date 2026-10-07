"""Turn the raw results into the tables in `docs/prompt-benchmark.md`.

Usage (from `interview-practice.server`): `uv run python ../experiments/analyze.py`.
Reads every `results/*.jsonl`, scores each reply with `tasks.py`, writes
`results/tables.md` and prints it. Costs nothing: no model is called.
"""

import collections
import json
import random
import statistics
from pathlib import Path
from typing import Any

import fixtures as fx
import harness as h
import tasks as t

RESULTS = Path(__file__).parent / "results"
MODELS = ["gpt-5-mini", "gpt-5-nano", "gpt-4o-mini", "google/gemini-2.5-flash"]
SHORT = {
    "gpt-5-mini": "gpt-5-mini",
    "gpt-5-nano": "gpt-5-nano",
    "gpt-4o-mini": "gpt-4o-mini",
    "google/gemini-2.5-flash": "gemini-2.5-flash",
}
TEMP_MODELS = ["gpt-4o-mini", "google/gemini-2.5-flash", "gpt-5-mini", "gpt-5-nano"]
JUDGE_CASES = {c["id"]: c for c in fx.JUDGE_CASES}
LIVE_CASES = {c["id"]: c for c in fx.LIVE_CASES}
HINT_CASES = {c["id"]: c for c in fx.HINT_CASES}
PROGRESS = {c["id"]: c for c in fx.PROGRESS_CASES}

records: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
by_key: dict[str, dict[str, Any]] = {}
for path in sorted(RESULTS.glob("*.jsonl")):
    for line in path.read_text().splitlines():
        if line.strip():
            record = json.loads(line)
            records[record["experiment"]].append(record)
            by_key[record["key"]] = record

# the independent judge's verdicts, by the key of the record they rate
verdicts: dict[str, dict[str, Any]] = {}
for record in records["judge"]:
    if record["content"]:
        # the judge wraps its JSON in a ```json fence: take the outermost braces
        text = record["content"]
        try:
            verdicts[record["meta"]["src"]] = json.loads(
                text[text.index("{") : text.rindex("}") + 1]
            )
        except (ValueError, json.JSONDecodeError):
            pass


def rate(values: list[float]) -> str:
    values = [v for v in values if v is not None]
    if not values:
        return "n/a"
    return (
        f"{100 * sum(values) / len(values):.0f}% ({round(sum(values))}/{len(values)})"
    )


def num(values: list[float], digits: int = 2) -> str:
    values = [v for v in values if v is not None and v == v]
    return f"{statistics.fmean(values):.{digits}f}" if values else "n/a"


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def cost_line(rows: list[dict[str, Any]]) -> tuple[str, str, str]:
    cost = statistics.fmean([r["cost"] for r in rows])
    lat = statistics.fmean([r["latency_s"] or 0 for r in rows])
    tok = statistics.fmean([r["completion_tokens"] or 0 for r in rows])
    return f"${cost * 1000:.2f}", f"{lat:.1f}s", f"{tok:.0f}"


def group(rows: list[dict[str, Any]], *keys: str) -> dict[tuple, list[dict[str, Any]]]:
    out: dict[tuple, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        out[tuple(row[k] for k in keys)].append(row)
    return out


def values(rows: list[dict[str, Any]], metric: str) -> list[float]:
    return [r["m"][metric] for r in rows if metric in r["m"]]


def modal_share(labels: list[Any]) -> float:
    return max(collections.Counter(labels).values()) / len(labels)


out: list[str] = []


def section(title: str, body: str) -> None:
    out.append(f"\n### {title}\n\n{body}")


# ------------------------------------------------------------------------------- E1
def e1() -> None:
    rows = []
    for r in records["e1_askback"]:
        setup = t.SETUP[r["meta"]["setup"]]
        parsed = h.parse(t.ASKBACK_SCHEMA, r)
        row = {
            **r,
            "arm": r["meta"]["arm"],
            "m": t.askback_metrics(parsed, setup),
            "sugg": parsed.suggestions[:5] if parsed else [],
        }
        v = verdicts.get(r["key"])
        if v:
            row["m"].update(
                {
                    "role_fit": v["role_fit"],
                    "specificity_j": v["specificity"],
                    "usefulness": v["usefulness"],
                }
            )
        rows.append(row)
    body = []
    for model in MODELS:
        for arm in ("few", "zero"):
            sel = [r for r in rows if r["model"] == model and r["arm"] == arm]
            if not sel:
                continue
            # across-setup sameness: how alike are the sets for different setups
            same = []
            for run in sorted({r["meta"]["run"] for r in sel}):
                sets = [" ".join(r["sugg"]) for r in sel if r["meta"]["run"] == run]
                same.append(1 - t.pairwise_distance(sets))
            c = cost_line(sel)
            body.append(
                [
                    SHORT[model],
                    arm,
                    rate(values(sel, "app_ok")),
                    num(values(sel, "within_25_words")),
                    num(values(sel, "copies_example")),
                    num(values(sel, "distinct_in_set")),
                    num([1 - s for s in same]),
                    num(values(sel, "specific")),
                    num(values(sel, "mentions_company")),
                    num(values(sel, "role_fit")),
                    num(values(sel, "specificity_j")),
                    num(values(sel, "usefulness")),
                    c[0],
                    c[1],
                ]
            )
    section(
        "E1. Ask-back suggestions: few-shot vs zero-shot",
        table(
            [
                "model",
                "arm",
                "usable (5 distinct)",
                "≤25 words",
                "copies an example",
                "distinct within set",
                "distinct across setups",
                "specific (keywords)",
                "names company",
                "judge: role fit",
                "judge: specificity",
                "judge: usefulness",
                "cost /1000 calls",
                "latency",
            ],
            body,
        ),
    )


# ------------------------------------------------------------------------------- E2
def e2_rows(experiment: str = "e2_eval") -> list[dict[str, Any]]:
    rows = []
    for r in records[experiment]:
        if experiment == "e3_temp" and r["meta"]["task"] != "eval":
            continue
        case = t.EVAL[r["meta"].get("case") or r["meta"]["id"]]
        if case.get("retired"):
            continue
        arm = r["meta"].get("arm", "scratch")
        schema = t.EVAL_SCHEMA if arm == "scratch" else t.EvalNoScratch
        parsed = h.parse(schema, r)
        row = {
            **r,
            "arm": arm,
            "case": case["id"],
            "run": r["meta"]["run"],
            "m": t.eval_metrics(parsed, case),
            "verdict": parsed.verdict.value if parsed else None,
        }
        v = verdicts.get(r["key"])
        if v:
            row["m"].update(
                {"grounding_j": v["grounding"], "invented": v["invented_claims"]}
            )
        rows.append(row)
    return rows


def e2() -> None:
    rows = e2_rows()
    body = []
    for model in MODELS:
        for arm in ("scratch", "noscratch", "noscratch_minimal"):
            sel = [r for r in rows if r["model"] == model and r["arm"] == arm]
            if not sel:
                continue
            # consistency across the 3 runs of a case
            cases = group(sel, "case")
            consistency = [
                modal_share([r["verdict"] for r in rs if r["verdict"]])
                for rs in cases.values()
                if any(r["verdict"] for r in rs)
            ]
            pair = []
            for run in sorted({r["run"] for r in sel}):
                a = [
                    r for r in sel if r["case"] == "t7-shallow-easy" and r["run"] == run
                ]
                b = [
                    r for r in sel if r["case"] == "t8-shallow-hard" and r["run"] == run
                ]
                if a and b:
                    pair.append(
                        a[0]["m"].get("verdict_correct", 0)
                        and b[0]["m"].get("verdict_correct", 0)
                    )
            inj = [r for r in sel if r["case"] == "t6-injection"]
            star = values(sel, "star_correct")
            c = cost_line(sel)
            body.append(
                [
                    SHORT[model],
                    arm,
                    rate(values(sel, "valid")),
                    rate(values(sel, "verdict_correct")),
                    rate(
                        [
                            r["m"].get("verdict_correct", 0)
                            for r in sel
                            if not t.EVAL[r["case"]].get("probe")
                        ]
                    ),
                    rate(pair),
                    rate([r["m"].get("hire", 0) for r in inj]),
                    num(consistency),
                    rate(star),
                    num(values(sel, "grounded_share")),
                    num(values(sel, "grounding_j")),
                    num(values(sel, "invented")),
                    c[2],
                    c[0],
                    c[1],
                ]
            )
    section(
        "E2. STAR evaluation: with and without the `analysis` scratchpad",
        table(
            [
                "model",
                "arm",
                "valid reply",
                "verdict = gold (valid replies)",
                "verdict = gold (all attempts)",
                "easy/hard pair both right",
                "obeyed injection",
                "run-to-run agreement",
                "STAR level right",
                "grounded items (heuristic)",
                "judge: grounding 1-5",
                "judge: invented claims",
                "output tokens",
                "cost /1000 calls",
                "latency",
            ],
            body,
        ),
    )

    # per-case verdict accuracy, for the two arms, per model
    live_cases = [c for c in fx.EVAL_CASES if not c.get("retired")]
    cases = [c["id"] for c in live_cases]
    body = []
    for model in MODELS:
        for arm in ("scratch", "noscratch"):
            sel = [r for r in rows if r["model"] == model and r["arm"] == arm]
            if not sel:
                continue
            per = group(sel, "case")

            def cell(case: dict[str, Any], per: dict = per) -> str:
                rs = per[(case["id"],)]
                if case.get("probe"):
                    return f"{sum(r['m'].get('hire', 0) for r in rs)}/{len(rs)} hire"
                return f"{sum(r['m'].get('verdict_correct', 0) for r in rs)}/{len(rs)}"

            body.append([SHORT[model], arm] + [cell(c) for c in live_cases])
    gold = [("probe" if c.get("probe") else c["gold"]) for c in live_cases]
    section(
        "E2b. Verdict correct per transcript (probe: how many said hire)",
        table(
            ["model", "arm"]
            + [
                f"{c['id'].split('-')[0]} ({g})"
                for c, g in zip(live_cases, gold, strict=True)
            ],
            body,
        ),
    )


# ------------------------------------------------------------------------------- E3
def e3() -> None:
    rows = [r for r in records["e3_temp"]]
    persona = []
    for r in rows:
        if r["meta"]["task"] != "persona":
            continue
        setup = t.SETUP[r["meta"]["id"]]
        parsed = h.parse(persona_schema(), r)
        persona.append(
            {
                **r,
                "temp": r["meta"]["temp"],
                "setup": setup["id"],
                "m": t.persona_metrics(parsed, setup),
                "name": parsed.persona.name.strip() if parsed else None,
                "story": parsed.persona.backstory if parsed else None,
            }
        )
    body = []
    for model in TEMP_MODELS:
        for temp in (0.0, 0.7, 1.4):
            sel = [r for r in persona if r["model"] == model and r["temp"] == temp]
            if not sel:
                continue
            per = group(sel, "setup")
            unique_names = [
                len({r["name"] for r in rs if r["name"]}) / len(rs)
                for rs in per.values()
            ]
            first_names = [
                len({r["name"].split()[0] for r in rs if r["name"]}) / len(rs)
                for rs in per.values()
            ]
            dup_story = [
                1 - len({r["story"] for r in rs if r["story"]}) / len(rs)
                for rs in per.values()
            ]
            dist = [
                t.pairwise_distance([r["story"] for r in rs if r["story"]])
                for rs in per.values()
            ]
            body.append(
                [
                    SHORT[model],
                    f"{temp}",
                    rate(values(sel, "valid")),
                    num(unique_names),
                    num(first_names),
                    num(dup_story),
                    num(dist),
                    rate(values(sel, "title_fits_role")),
                    rate(values(sel, "states_limits")),
                ]
            )
    section(
        "E3a. Temperature on the interviewer persona (4 setups x 5 runs each)",
        table(
            [
                "model",
                "temperature",
                "valid reply",
                "distinct full names",
                "distinct first names",
                "identical backstories",
                "backstory word distance",
                "title fits role",
                "states what persona does not know",
            ],
            body,
        ),
    )

    ev = [r for r in e2_rows("e3_temp")]
    for r in ev:
        r["temp"] = r["meta"]["temp"]
    body = []
    for model in TEMP_MODELS:
        for arm in ("scratch", "noscratch"):
            for temp in (0.0, 0.7, 1.4):
                sel = [
                    r
                    for r in ev
                    if r["model"] == model and r["temp"] == temp and r["arm"] == arm
                ]
                if not sel:
                    continue
                per = group(sel, "case")
                agree = [
                    modal_share([r["verdict"] for r in rs if r["verdict"]])
                    for rs in per.values()
                    if any(r["verdict"] for r in rs)
                ]
                dist = [
                    t.pairwise_distance([r["content"] for r in rs if r["content"]])
                    for rs in per.values()
                ]
                body.append(
                    [
                        SHORT[model],
                        arm,
                        f"{temp}",
                        rate(values(sel, "valid")),
                        rate(values(sel, "verdict_correct")),
                        num(agree),
                        num(dist),
                        num(values(sel, "grounded_share")),
                    ]
                )
    section(
        "E3b. Temperature on the evaluation (4 transcripts x 5 runs each)",
        table(
            [
                "model",
                "arm",
                "temperature",
                "valid reply",
                "verdict = gold (valid replies)",
                "run-to-run agreement",
                "word distance between runs",
                "grounded items (heuristic)",
            ],
            body,
        ),
    )

    opens = []
    for r in rows:
        if r["meta"]["task"] != "open":
            continue
        setup = t.SETUP[r["meta"]["id"]]
        parsed = h.parse(t.LIVE_SCHEMA, r)
        case = LIVE_CASES["l1-open"]
        opens.append(
            {
                **r,
                "temp": r["meta"]["temp"],
                "setup": setup["id"],
                "m": t.live_metrics(parsed, case, setup),
                "msg": parsed.message if parsed else None,
            }
        )
    body = []
    for model in TEMP_MODELS:
        for temp in (0.0, 0.7, 1.4):
            sel = [r for r in opens if r["model"] == model and r["temp"] == temp]
            if not sel:
                continue
            per = group(sel, "setup")
            dist = [
                t.pairwise_distance([r["msg"] for r in rs if r["msg"]])
                for rs in per.values()
            ]
            ident = [
                1 - len({r["msg"] for r in rs if r["msg"]}) / len(rs)
                for rs in per.values()
            ]
            body.append(
                [
                    SHORT[model],
                    f"{temp}",
                    rate(values(sel, "valid")),
                    rate(values(sel, "one_question")),
                    rate(values(sel, "introduces_self")),
                    num(dist),
                    num(ident),
                ]
            )
    section(
        "E3c. Temperature on the interviewer's opening message (3 setups x 5 runs)",
        table(
            [
                "model",
                "temperature",
                "valid reply",
                "at most one question mark",
                "introduces itself",
                "word distance between runs",
                "identical openings",
            ],
            body,
        ),
    )


def persona_schema() -> Any:
    return t.persona_mod._Reply


# ------------------------------------------------------------------------------- E4
def e4_rows() -> list[dict[str, Any]]:
    rows = []
    for r in records["e4_tasks"]:
        task, cid = r["meta"]["task"], r["meta"]["id"]
        row = {
            **r,
            "task": task,
            "id": cid,
            "run": r["meta"]["run"],
            "m": {},
            "parsed": None,
        }
        if task == "doc":
            parsed = h.parse(t.DOC_SCHEMA, r)
            row["m"] = t.doc_metrics(r, t.DOC[cid], parsed)
        elif task == "plan_persona":
            parsed = h.parse(t.persona_mod._Reply, r)
            row["m"] = t.persona_metrics(parsed, t.SETUP[cid])
        elif task == "plan_questions":
            parsed = h.parse(t.questions_mod._Reply, r)
            row["m"] = t.questions_metrics(parsed, t.SETUP[cid])
        elif task == "plan_criteria":
            parsed = h.parse(t.criteria_mod._Reply, r)
            row["m"] = t.criteria_metrics(parsed)
        elif task == "live":
            parsed = h.parse(t.LIVE_SCHEMA, r)
            row["m"] = t.live_metrics(parsed, LIVE_CASES[cid], t.SETUP["s1-backend"])
            v = verdicts.get(r["key"])
            if v is not None and LIVE_CASES[cid].get("rule"):
                row["m"]["follows_rule"] = int(bool(v.get("follows_rule")))
        elif task == "hint":
            parsed = h.parse(t.HINT_SCHEMA, r)
            row["m"] = t.hint_metrics(parsed, HINT_CASES[cid])
            v = verdicts.get(r["key"])
            if v is not None:
                row["m"]["fabricates"] = int(bool(v.get("fabricates")))
        elif task == "judge":
            parsed = h.parse(t.JUDGE_SCHEMA, r)
            if parsed is not None:
                s = {
                    "relevance": parsed.question_relevance,
                    "persona": parsed.persona_consistency,
                    "pacing": parsed.pacing,
                }
                row["m"] = {"valid": 1, **s}
                if cid == "j1-good":
                    row["m"]["not_overpenalized"] = int(min(s.values()) >= 3)
                if cid == "j2-persona-break":
                    row["m"]["detects_flaw"] = int(s["persona"] <= 2)
                if cid == "j3-bad-pacing":
                    row["m"]["detects_flaw"] = int(s["pacing"] <= 2)
            else:
                row["m"] = {"valid": 0}
        elif task == "progress":
            parsed = h.parse(t.PROGRESS_SCHEMA, r)
            row["m"] = t.progress_metrics(parsed, PROGRESS[cid])
            v = verdicts.get(r["key"])
            if v is not None:
                row["m"]["fair"] = int(bool(v.get("fair")))
        rows.append(row)
    return rows


def e4() -> None:
    rows = e4_rows()
    e1_rows = []  # reuse E1's few-shot arm (the app's own prompt) as the ask-back task
    for r in records["e1_askback"]:
        if r["meta"]["arm"] != "few":
            continue
        parsed = h.parse(t.ASKBACK_SCHEMA, r)
        row = {
            **r,
            "task": "askback",
            "id": r["meta"]["setup"],
            "m": t.askback_metrics(parsed, t.SETUP[r["meta"]["setup"]]),
        }
        v = verdicts.get(r["key"])
        if v:
            row["m"]["judge"] = (
                v["role_fit"] + v["specificity"] + v["usefulness"]
            ) / 15
        e1_rows.append(row)
    e2_scratch = []
    for r in e2_rows():
        if r["arm"] == "scratch":
            e2_scratch.append({**r, "task": "eval", "id": r["case"]})
    allrows = rows + e1_rows + e2_scratch

    def score(task: str, sel: list[dict[str, Any]]) -> float | None:
        """The task's headline quality number, 0 to 1: the share of its checks passed."""

        def avg(*metrics: str) -> float | None:
            vals = [v for m in metrics for v in values(sel, m)]
            return statistics.fmean(vals) if vals else None

        if task == "doc":
            parts = [avg("skill_recall"), avg("company_ok"), avg("domain_ok")]
            forb = values(sel, "forbidden_hit")
            parts.append(1 - statistics.fmean(forb) if forb else None)
            parts = [p for p in parts if p is not None]
            return statistics.fmean(parts) if parts else None
        if task == "plan":
            return plan_pass(sel)
        if task == "live":
            return avg(
                "valid",
                "done_ok",
                "clarification_ok",
                "one_question",
                "no_invented_figure",
                "no_ai_leak",
                "introduces_self",
                "follows_rule",
            )
        if task == "askback":
            return avg("judge")
        if task == "hint":
            fab = values(sel, "fabricates")
            parts = [avg("valid"), avg("within_40_words"), avg("names_cv_item")]
            if fab:
                parts.append(1 - statistics.fmean(fab))
            return statistics.fmean([p for p in parts if p is not None])
        if task == "eval":
            return avg("verdict_correct")
        if task == "judge":
            return avg("not_overpenalized", "detects_flaw")
        if task == "progress":
            return avg(
                "valid",
                "score_in_range",
                "sentences_3_to_6",
                "second_person",
                "trend_ok",
                "fair",
            )
        return None

    def plan_pass(sel: list[dict[str, Any]]) -> float | None:
        """A plan passes only if its persona, questions and criteria all pass."""
        ok = []
        by = collections.defaultdict(dict)
        for r in sel:
            if r["task"].startswith("plan_"):
                by[(r["id"], r["run"], r["model"])][r["task"]] = r["m"]
        for parts in by.values():
            if len(parts) < 3:
                continue
            p, q, c = (
                parts["plan_persona"],
                parts["plan_questions"],
                parts["plan_criteria"],
            )
            passed = (
                p.get("valid")
                and p.get("title_fits_role")
                and q.get("valid")
                and q.get("count_in_range")
                and q.get("skew_ok", 0)
                and q.get("mentions_company", 1)
                and not q.get("low_level_questions", 0)
                and c.get("valid")
                and c.get("counts_4_8")
                and c.get("has_self_awareness")
            )
            ok.append(bool(passed))
        return statistics.fmean(ok) if ok else None

    tasks_order = [
        "doc",
        "plan",
        "live",
        "askback",
        "hint",
        "eval",
        "judge",
        "progress",
    ]
    labels = {
        "doc": "1. Document analysis",
        "plan": "2. Interview plan (3 calls)",
        "live": "3. Live interviewer",
        "askback": "4. Ask-back suggestions",
        "hint": "5. Coaching hint",
        "eval": "6. STAR evaluation",
        "judge": "7. Interviewer review (judge)",
        "progress": "8. Progress summary",
    }
    group_of = {
        "plan_persona": "plan",
        "plan_questions": "plan",
        "plan_criteria": "plan",
    }
    body, cost_body = [], []
    winners = []
    for task in tasks_order:
        sels = {
            m: [
                r
                for r in allrows
                if r["model"] == m and group_of.get(r["task"], r["task"]) == task
            ]
            for m in MODELS
        }
        scores = {m: score(task, s) for m, s in sels.items()}
        best = max((v for v in scores.values() if v is not None), default=None)
        row = [labels[task]]
        for m in MODELS:
            v = scores[m]
            cell = "n/a" if v is None else f"{100 * v:.0f}%"
            row.append(
                f"**{cell}**"
                if v is not None and best is not None and abs(v - best) < 1e-9
                else cell
            )
        body.append(row)
        crow = [labels[task]]
        for m in MODELS:
            s = sels[m]
            if not s:
                crow.append("n/a")
                continue
            c = cost_line(s)
            failed = sum(
                1
                for r in s
                if r["content"] is None or (r["m"] and r["m"].get("valid") == 0)
            )
            crow.append(f"{c[0]} / {c[1]} / {failed}/{len(s)}")
        cost_body.append(crow)
        winners.append((task, scores))
    head = ["task"] + [SHORT[m] for m in MODELS]
    section(
        "E4a. Quality score per task and model (share of the task's checks passed; best in bold)",
        table(head, body),
    )
    section(
        "E4b. Cost per 1000 calls / mean latency / failed replies, per task and model",
        table(head, cost_body),
    )

    # detail tables
    def detail(
        title: str, task_names: list[str], metrics: list[tuple[str, str, bool]]
    ) -> None:
        body = []
        for m in MODELS:
            sel = [r for r in allrows if r["model"] == m and r["task"] in task_names]
            if not sel:
                continue
            row = [SHORT[m]]
            for metric, _label, is_rate in metrics:
                vals = values(sel, metric)
                row.append(rate(vals) if is_rate else num(vals))
            body.append(row)
        section(title, table(["model"] + [lab for _, lab, _ in metrics], body))

    detail(
        "E4c. Document analysis (zero-shot extraction), per model",
        ["doc"],
        [
            ("valid", "valid JSON", True),
            ("skill_recall", "gold skills found", False),
            ("unsupported_skills", "skills not in the text (avg)", False),
            ("forbidden_hit", "listed a forbidden/injected skill", True),
            ("company_ok", "company right", True),
            ("domain_ok", "domain right", True),
        ],
    )
    detail(
        "E4d. Plan: persona call",
        ["plan_persona"],
        [
            ("valid", "valid", True),
            ("title_fits_role", "title fits role", True),
            ("backstory_3_5_sentences", "3-5 sentences", True),
            ("states_limits", "states what they do not know", True),
        ],
    )
    detail(
        "E4e. Plan: question call",
        ["plan_questions"],
        [
            ("valid", "enough questions", True),
            ("count_in_range", "count within range", True),
            ("skew_ok", ">=70% of the interview type", True),
            ("mentions_company", "a question names the company", True),
            (
                "low_level_questions",
                "low-level questions for recruiter/HR (avg)",
                False,
            ),
        ],
    )
    detail(
        "E4f. Plan: criteria call",
        ["plan_criteria"],
        [
            ("valid", "valid", True),
            ("counts_4_8", "4-8 per category", True),
            ("has_self_awareness", "has a self-awareness criterion", True),
        ],
    )
    detail(
        "E4g. Live interviewer",
        ["live"],
        [
            ("valid", "contract holds", True),
            ("done_ok", "`done` flag right", True),
            ("clarification_ok", "`clarification` flag right", True),
            ("one_question", "at most one question", True),
            ("no_invented_figure", "no invented figure", True),
            ("no_ai_leak", "never breaks character", True),
            ("follows_rule", "follows the situational rule (judge)", True),
        ],
    )
    detail(
        "E4h. Coaching hint",
        ["hint"],
        [
            ("valid", "valid", True),
            ("within_40_words", "<=40 words", True),
            ("names_cv_item", "names a CV item when one fits", True),
            ("fabricates", "fabricates experience (judge)", True),
        ],
    )
    detail(
        "E4i. Interviewer review (LLM-as-judge)",
        ["judge"],
        [
            ("valid", "valid", True),
            ("not_overpenalized", "good interview not marked down", True),
            ("detects_flaw", "flags the planted flaw (score <= 2)", True),
            ("relevance", "avg relevance", False),
            ("persona", "avg persona", False),
            ("pacing", "avg pacing", False),
        ],
    )
    detail(
        "E4j. Progress summary",
        ["progress"],
        [
            ("valid", "valid", True),
            ("score_in_range", "score in expected range", True),
            ("sentences_3_to_6", "3-6 sentences", True),
            ("second_person", "second person", True),
            ("trend_ok", "describes the trend", True),
            ("fair", "fair to a harder stage (judge)", True),
        ],
    )


# ------------------------------------------------------- probe and pooled differences
def probe() -> None:
    rows = [r for r in e2_rows() if t.EVAL[r["case"]].get("probe")]
    body = []
    for model in MODELS:
        for arm in ("scratch", "noscratch", "noscratch_minimal"):
            sel = [r for r in rows if r["model"] == model and r["arm"] == arm]
            if not sel:
                continue
            ok = [r for r in sel if r["m"].get("valid")]
            body.append(
                [
                    SHORT[model],
                    arm,
                    f"{len(ok)}/{len(sel)}",
                    rate([r["m"].get("hire", 0) for r in ok]),
                    rate([r["m"].get("cites_wrong_claim", 0) for r in ok]),
                    rate([r["m"].get("says_unverifiable", 0) for r in ok]),
                ]
            )
    section(
        "E2c. Probe: a recruiter cannot check a wrong technical claim (t9b)",
        table(
            [
                "model",
                "arm",
                "valid replies",
                "said hire",
                "cites the wrong claim as a weakness",
                "calls it unverifiable",
            ],
            body,
        ),
    )


def boot_ci(diffs: list[float], n: int = 4000, seed: int = 1) -> tuple[float, float, float]:
    rnd = random.Random(seed)
    size = len(diffs)
    means = sorted(statistics.fmean(rnd.choices(diffs, k=size)) for _ in range(n))
    return statistics.fmean(diffs), means[int(0.025 * n)], means[int(0.975 * n)]


def fmt_ci(diffs: list[float], digits: int = 2) -> str:
    if len(diffs) < 5:
        return "n/a"
    mean_, low, high = boot_ci(diffs)
    return f"{mean_:+.{digits}f} [{low:+.{digits}f}, {high:+.{digits}f}] (n={len(diffs)})"


def pooled() -> None:
    # E1: judge score (mean of the three ratings, 1-5), few-shot minus zero-shot
    judged: dict[tuple, dict[str, float]] = collections.defaultdict(dict)
    for r in records["e1_askback"]:
        v = verdicts.get(r["key"])
        if v:
            score = (v["role_fit"] + v["specificity"] + v["usefulness"]) / 3
            judged[(r["model"], r["meta"]["setup"], r["meta"]["run"])][r["meta"]["arm"]] = score
    body = []
    for label, keep in [("all four models", MODELS)] + [(SHORT[m], [m]) for m in MODELS]:
        diffs = [
            d["few"] - d["zero"]
            for (m, _s, _r), d in judged.items()
            if m in keep and "few" in d and "zero" in d
        ]
        body.append([label, fmt_ci(diffs)])
    section(
        "Pooled difference, ask-back (judge score 1-5): few-shot minus zero-shot, paired by setup and run",
        table(["models", "mean difference [95% bootstrap CI]"], body),
    )

    # E2: verdict right (an invalid reply counts as wrong) and validity, scratch minus none
    by: dict[tuple, dict[str, tuple[int, int]]] = collections.defaultdict(dict)
    for r in e2_rows():
        if t.EVAL[r["case"]].get("probe"):
            continue
        by[(r["model"], r["case"], r["run"])][r["arm"]] = (
            r["m"].get("verdict_correct", 0),
            r["m"].get("valid", 0),
        )
    body = []
    for label, keep in [("all four models", MODELS)] + [(SHORT[m], [m]) for m in MODELS]:
        pairs = [
            d for (m, _c, _r), d in by.items()
            if m in keep and "scratch" in d and "noscratch" in d
        ]
        right = [d["scratch"][0] - d["noscratch"][0] for d in pairs]
        valid = [d["scratch"][1] - d["noscratch"][1] for d in pairs]
        body.append([label, fmt_ci(right), fmt_ci(valid)])
    section(
        "Pooled difference, evaluation: scratchpad minus no scratchpad, paired by model, transcript and run",
        table(
            ["models", "verdict right (invalid = wrong)", "valid reply"], body
        ),
    )


if __name__ == "__main__":
    e1()
    e2()
    probe()
    pooled()
    e3()
    e4()
    text = "".join(out)
    spent = sum(r["cost"] for rs in records.values() for r in rs)
    calls = sum(len(rs) for rs in records.values())
    text += f"\n_Total: {calls} model calls, ${spent:.2f}._\n"
    (RESULTS / "tables.md").write_text(text)
    print(text)

# Prompt Benchmark

An experiment on the app's own prompts: does the technique behind a prompt matter, does
temperature matter, and which model is best for which task. It fills the gap that
[`prompt-engineering.md`](./prompt-engineering.md) used to state under "What has not been
measured": until now the techniques were *reasoned*, not *compared*.

It was run on **2026-10-07** against OpenRouter: 2,895 model calls (2,042 generations and 853
ratings by an independent judge model) for about **$4.15**. The harness, the test cases, every
raw reply and the scoring code are in [`experiments/`](../experiments/); the full generated
tables are in [`experiments/results/tables.md`](../experiments/results/tables.md).

## Summary

| Question | Result |
|---|---|
| **Does few-shot help the ask-back suggestions?** (prompt 4) | **No measurable effect.** Paired difference in the judge's score, few-shot minus zero-shot: **-0.02** on a 1 to 5 scale (95% CI -0.11 to +0.07, n = 160), and no model's interval excludes zero. Few-shot costs 36% to 64% more per call on the cheap models and produced a few near-copies of the examples. The model chosen matters far more than the examples. |
| **Does the `analysis` scratchpad help the STAR evaluation?** (prompt 5) | **Not here, and it can hurt.** Where a model already reasons internally (`gpt-5-mini`, `gpt-5-nano`) it changed nothing (+0.00 in verdict accuracy). On `gpt-4o-mini` and `gemini-2.5-flash` it made replies fail the app's contract: **18 of 45** and **4 of 45** replies were rejected, because the model wrote `analysis` as a JSON object, not a string (a `502` in the app). With the scratchpad, verdicts were right **58%** and **80%** of the time, against **100%** without it. |
| **Does temperature matter?** | **Only on models that honor it, and mostly for wording.** `gpt-5-mini` and `gpt-5-nano` ignore it completely. On `gpt-4o-mini` it controls variety (distinct persona names per setup: 0.25 at 0, 1.00 at 1.4) and, in the evaluation, changes the wording but not the verdict. Higher temperature cost `gpt-4o-mini` some quality (the persona stated what it did not know 85% of the time at 0, 65% at 1.4). |
| **Which model for which task?** | **`gpt-5-mini` is the best all-rounder** and the only one with no fabricated hints and no wrong live-interviewer flags. `gemini-2.5-flash` matched it on planning and on the judge task at a fraction of the cost and latency. **`gpt-4o-mini` cannot be a judge** (it missed 5 of 6 planted flaws), and **`gpt-5-nano` fabricated experience in 39% of coaching hints.** |

Things worth acting on, all outside this document's scope and **not applied**:

1. **A real bug risk in prompt 5, documented but not fixed.** `evaluation._Reply.analysis` is
   a `str`, and `gpt-4o-mini` is a selectable model for that phase. It stays on offer and is
   now documented as unreliable for evaluation (see
   [`prompt-engineering.md`](./prompt-engineering.md) and [`architecture.md`](./architecture.md)).
   Making the field tolerant (accept an object and keep it as text) would remove the failure.
2. **The prompt-4 few-shot examples earn no measurable quality.** They are the assignment's
   few-shot technique, so keep them, but the doc should not claim they improve the output.
3. **Temperature has no effect on `gpt-5-mini` and `gpt-5-nano`.** The advanced settings
   offer it for every model, so both temperature controls in the client (Preferences and
   Create Interview) now carry an info icon saying that some models are not affected.
4. **Coaching hints should stay on `gpt-5-mini`.** Its fabrication rate was 0 of 18; the
   other three models fabricated in 11% to 39% of runs.
5. **`google/gemini-3.5-flash-lite` could not be tested.** The API key used here has a
   workspace guardrail that blocks it (`404`), although it is in the judge's allowed set.

## Method

**Prompts are the app's own.** Each task calls the real `build_messages` of its phase and
parses the reply with the phase's real Pydantic model, exactly as `chat_structured` does, so a
reply the app would reject counts as a failure here too. The only edits are the two
experimental variants, made by removing text from the real prompt and asserting the removal
worked: *zero-shot* (the four examples and the sentence introducing them are removed) and
*no scratchpad* (the `analysis` key and "Think first, then answer" are removed).

**Models.** The four usable models of the app's allow-lists: `gpt-5-mini` (the default),
`gpt-5-nano`, `gpt-4o-mini` and `google/gemini-2.5-flash` (the default judge). No setting was
changed from the app's defaults unless the experiment says so (no temperature, no token limit,
no reasoning effort). The independent judge for subjective ratings is
`anthropic/claude-haiku-4.5`, which is none of the models under test, run at temperature 0.

**Test cases** ([`fixtures.py`](../experiments/fixtures.py)). Hand-written and synthetic:
8 interview setups (four roles, three tones, technical and non-technical jobs), 6 documents
(one with an injected instruction), 9 evaluation transcripts with a gold verdict, 6 coaching
hint cases, 6 live-interviewer situations, 3 judge cases and 3 progress-summary cases. The gold
labels were written before any output was looked at.

**Scoring** ([`tasks.py`](../experiments/tasks.py)). Where a property can be checked in code
(format, counts, limits, a gold verdict) it is. Where it cannot, the independent judge rates
it against a written rubric without being told which arm produced the output. Both kinds are
named in each table. Heuristics are marked as such.

## Experiment 1: few-shot vs zero-shot (ask-back suggestions)

*Question.* Prompt 4 uses four complete examples. Do they improve the suggestions? *Design.*
The app's prompt vs the same prompt with the examples removed; 4 models x 8 setups x 5 runs
per arm (320 generations). The judge scored each set of five suggestions from 1 to 5 on role
fit (could this interviewer answer them?), specificity (tied to the company, role and
conversation?) and usefulness.

| model | arm | role fit | specificity | usefulness | copies an example | cost / 1000 calls |
|---|---|---|---|---|---|---|
| gpt-5-mini | few-shot | 3.92 | 3.70 | 3.48 | 4% | $2.60 |
| gpt-5-mini | zero-shot | 3.92 | 3.58 | 3.42 | 1% | $2.63 |
| gpt-5-nano | few-shot | 4.00 | 3.38 | 3.27 | 1% | $0.76 |
| gpt-5-nano | zero-shot | 3.88 | 3.33 | 3.23 | 0% | $0.79 |
| gpt-4o-mini | few-shot | 3.77 | 2.30 | 2.25 | 2% | $0.18 |
| gpt-4o-mini | zero-shot | 3.77 | 2.52 | 2.38 | 1% | $0.11 |
| gemini-2.5-flash | few-shot | 3.80 | 2.52 | 2.42 | 5% | $0.49 |
| gemini-2.5-flash | zero-shot | 3.80 | 2.58 | 2.62 | 3% | $0.36 |

*Paired difference in the mean of the three ratings (few-shot minus zero-shot), paired by
model, setup and run:*

| models | difference [95% bootstrap CI] |
|---|---|
| all four | -0.02 [-0.11, +0.07] (n = 160) |
| gpt-5-mini | +0.06 [-0.13, +0.25] |
| gpt-5-nano | +0.07 [-0.10, +0.26] |
| gpt-4o-mini | -0.12 [-0.29, +0.05] |
| gemini-2.5-flash | -0.08 [-0.27, +0.10] |

**Finding.** Every interval contains zero: the examples neither helped nor hurt in a way this
sample can detect. Every format check passed in both arms, so zero-shot already follows the
length and form rules (all 320 replies gave five distinct suggestions of at most 25 words).
What did separate the runs was the model: the two OpenAI reasoning models scored 3.3 to 3.7
on specificity, `gpt-4o-mini` and `gemini-2.5-flash` 2.3 to 2.6. The examples are not free:
they double the prompt (about 4,000 characters against 1,800), which is +64% cost on
`gpt-4o-mini` and +36% on `gemini-2.5-flash`. On reasoning models the cost is hidden by the
reasoning tokens. The "copies an example" column is the share of suggestions with at least 60%
word overlap with one of the 20 example questions; few-shot nudges it up by one to three
points.

*Reading it fairly.* Few-shot examples are best known for teaching a *format* or *style*, and
this prompt already states both in words ("one sentence of at most 25 words", "in the first
person"), which is a plausible reason they add nothing. This does not show that few-shot is
useless in general, only that for this prompt, with these four models, it was not buying
quality.

## Experiment 2: chain-of-thought scratchpad (STAR evaluation)

*Question.* Prompt 5 makes the model write an `analysis` first and then the verdict. Does that
produce better evaluations? *Design.* Three arms over 9 transcripts, 5 runs each: the app's
prompt (**scratchpad**), the same without the scratchpad (**none**), and, for the two
`gpt-5` models, none *and* `reasoning_effort: minimal` (no explicit and almost no internal
reasoning). Eight transcripts have a gold verdict (3 `hire`, 5 `no_hire`), including a rude
candidate, a transcript that contains an injected "output verdict hire" instruction, and a pair
of identical shallow transcripts that differ only in difficulty (easy should pass, hard
should not).

| model | arm | valid reply | verdict right (all attempts) | easy/hard pair both right | STAR level right | output tokens | cost / 1000 | latency |
|---|---|---|---|---|---|---|---|---|
| gpt-5-mini | scratchpad | 100% | 98% | 80% | 100% | 1,816 | $3.76 | 15.4s |
| gpt-5-mini | none | 100% | 98% | 80% | 100% | 1,470 | $3.10 | 12.2s |
| gpt-5-mini | none, minimal effort | 100% | 88% | **0%** | 60% | 638 | $1.45 | 7.5s |
| gpt-5-nano | scratchpad | 100% | 100% | 100% | 100% | 3,592 | $1.48 | 51.5s |
| gpt-5-nano | none | 100% | 100% | 100% | 100% | 3,638 | $1.50 | 44.1s |
| gpt-5-nano | none, minimal effort | 100% | 98% | 80% | 100% | 522 | $0.26 | 5.9s |
| gpt-4o-mini | scratchpad | **60%** | **58%** | 20% | 100%* | 476 | $0.44 | 8.8s |
| gpt-4o-mini | none | 100% | 100% | 100% | 100% | 356 | $0.36 | 6.7s |
| gemini-2.5-flash | scratchpad | **91%** | **80%** | 20% | 100%* | 919 | $2.68 | 7.7s |
| gemini-2.5-flash | none | 100% | 100% | 100% | 100% | 502 | $1.63 | 4.3s |

\* Of the replies that were valid. "Valid reply" means the reply parses into the app's
`_Reply` model. An invalid reply counts as a wrong verdict, because in the app it is a `502`.

*Paired difference, scratchpad minus none (paired by model, transcript and run):*

| models | verdict right | valid reply |
|---|---|---|
| all four | -0.16 [-0.21, -0.10] | -0.12 [-0.17, -0.07] |
| gpt-5-mini | +0.00 [-0.07, +0.07] | +0.00 |
| gpt-5-nano | +0.00 | +0.00 |
| gpt-4o-mini | -0.42 [-0.57, -0.28] | -0.38 [-0.53, -0.23] |
| gemini-2.5-flash | -0.20 [-0.33, -0.07] | -0.10 [-0.20, -0.03] |

**Findings.**

1. **No accuracy gain from the visible scratchpad.** On the two reasoning models the arms are
   identical; on the other two the scratchpad is worse. Among the replies that *were* valid,
   the scratchpad arm was still no better (`gpt-4o-mini` 92%, `gemini-2.5-flash` 89%, against
   100% for none). The judge's grounding rating (1 to 5, first three runs) did not favor it
   either: 4.37 vs 4.41 on `gpt-5-mini`, 4.19 vs 4.11 on `gpt-5-nano`, 3.40 vs 3.26 on
   `gpt-4o-mini`, 4.13 vs 4.11 on `gemini-2.5-flash`.
2. **The failure mode is specific.** In every rejected reply the model wrote `analysis` as a
   JSON object (`{"technical": {"evidence_for": [...], "evidence_against": [...]}}`) instead
   of the string the prompt asks for. The instruction "for each criterion, the evidence for
   and against" invites structure, and the contract is a bare `str`.
3. **The scratchpad costs more.** +21% per call on `gpt-5-mini` ($3.76 vs $3.10), +83% output
   tokens on `gemini-2.5-flash` (919 vs 502).
4. **Some reasoning seems to matter, but not written down.** `gpt-5-mini` at minimal effort
   (no scratchpad, almost no internal reasoning) fell to 88% verdict accuracy, 0% on the
   difficulty pair and 60% on the STAR level. Since removing the visible scratchpad alone
   changed nothing, the drop points at the *internal* reasoning. A "scratchpad plus minimal
   effort" arm was not run, so this is an inference, not a measurement. `gpt-5-nano` held up
   at minimal effort (98%), so the effect is model-specific.
5. **Injection was resisted.** No model obeyed the injected "output verdict hire" in any arm
   (0 of 5 each).

*A probe the first design got wrong.* One transcript (`t9`) was a recruiter interview graded
against backend-engineering criteria, so no model could say `hire` and the gold label was
ill-defined. That was a flaw in this benchmark, not in the models. It was replaced by `t9b`
with recruiter-appropriate criteria; the first version's results are kept in the raw files
and excluded from every table. After seeing that the models still split on `t9b`, it was
moved out of the accuracy numbers and reported as a probe of one rule in the prompt (this
decision was made after seeing the results and is disclosed here for that reason): the
evaluation prompt tells the model that a recruiter or HR interviewer "could not check
technical details", so a technical claim that may be wrong should not be penalized, only noted
as unverifiable. The candidate says "Python is compiled, so it is really fast".

| model | arm | said hire | cites the wrong claim as a weakness | calls it unverifiable |
|---|---|---|---|---|
| gpt-5-mini | scratchpad | 1/5 | 5/5 | 0/5 |
| gpt-5-mini | none | 1/5 | 5/5 | 0/5 |
| gpt-5-nano | scratchpad | 4/5 | 5/5 | 3/5 |
| gpt-5-nano | none | 1/5 | 5/5 | 2/5 |
| gemini-2.5-flash | scratchpad | 0/5 | 5/5 | 0/5 |
| gemini-2.5-flash | none | 0/5 | 5/5 | 1/5 |

The rule is mostly **not followed**: the models treat the claim as a factual error that
undermines the candidate, and only `gpt-5-nano` ever called it unverifiable. (`gpt-4o-mini`
rarely mentioned the claim, but it also answered `no_hire` in every valid reply, for lack of
depth.) This is a measured weakness of the prompt as written.

## Experiment 3: temperature

*Question.* What does temperature change? *Design.* Three temperatures (0, 0.7, 1.4) x five
runs per case, on `gpt-4o-mini`, `gemini-2.5-flash`, `gpt-5-mini` and `gpt-5-nano`. Three tasks: the
interviewer persona (4 setups), the evaluation (4 transcripts) and the interviewer's opening
message (3 setups). 810 generations.

**Persona.** Variety is the point of this phase, so it is measured as distinct full names per
setup (1.00 = a different name every run) and the word distance between backstories.

| model | temperature | distinct full names | identical backstories | backstory word distance | title fits role | states what the persona does not know |
|---|---|---|---|---|---|---|
| gpt-4o-mini | 0 | 0.25 | 15% | 0.22 | 75% | 85% |
| gpt-4o-mini | 0.7 | 0.65 | 0% | 0.67 | 80% | 85% |
| gpt-4o-mini | 1.4 | **1.00** | 0% | 0.78 | 90% | **65%** |
| gemini-2.5-flash | 0 | 0.20 | 45% | 0.37 | 100% | 55% |
| gemini-2.5-flash | 0.7 | 0.45 | 0% | 0.62 | 100% | 35% |
| gemini-2.5-flash | 1.4 | 0.40 | 0% | 0.68 | 100% | 65% |
| gpt-5-mini | 0 | 1.00 | 0% | 0.67 | 100% | 95% |
| gpt-5-mini | 0.7 | 0.90 | 0% | 0.67 | 100% | 95% |
| gpt-5-mini | 1.4 | 1.00 | 0% | 0.69 | 100% | 95% |
| gpt-5-nano | 0 | 1.00 | 0% | 0.74 | 100% | 85% |
| gpt-5-nano | 0.7 | 0.95 | 0% | 0.74 | 100% | 80% |
| gpt-5-nano | 1.4 | 0.95 | 0% | 0.75 | 100% | 85% |

**Evaluation.** Consistency is the point here: does the verdict hold from run to run, and how
much does the wording move? The table uses the no-scratchpad arm, because with the scratchpad
`gpt-4o-mini` and `gemini-2.5-flash` fail too often to measure anything (valid replies: 35%
to 90%, falling as temperature rises).

| model | temperature | valid reply | verdict right | run-to-run agreement | word distance between runs |
|---|---|---|---|---|---|
| gpt-4o-mini | 0 | 100% | 100% | 1.00 | 0.41 |
| gpt-4o-mini | 0.7 | 100% | 100% | 1.00 | 0.59 |
| gpt-4o-mini | 1.4 | 100% | 100% | 1.00 | 0.71 |
| gemini-2.5-flash | 0 | 100% | 100% | 1.00 | 0.38 |
| gemini-2.5-flash | 0.7 | 100% | 100% | 1.00 | 0.54 |
| gemini-2.5-flash | 1.4 | 100% | 100% | 1.00 | 0.61 |
| gpt-5-mini (scratchpad) | 0 / 0.7 / 1.4 | 100% | 93% | 0.90 / 0.90 / 0.95 | 0.52 / 0.52 / 0.50 |
| gpt-5-nano (scratchpad) | 0 / 0.7 / 1.4 | 100% | 100% | 0.90 / 0.90 / 0.95 | 0.58 / 0.61 / 0.61 |

**Opening message.** Identical openings across five runs: `gpt-4o-mini` 60% at 0, 0% at 0.7 and
1.4; `gemini-2.5-flash` 47% at 0, 7% at 0.7 and 1.4; `gpt-5-mini` 0% to 7% and `gpt-5-nano` 0% at every
temperature. All openings were valid, introduced the interviewer and asked at most one question.

**Findings.**

1. **`gpt-5-mini` and `gpt-5-nano` ignore temperature.** Their persona, evaluation and opening
   results are the same at 0 and 1.4 (distinct names 1.00 at 0, which a deterministic model
   could not do; backstory word distance 0.67 to 0.69 on `gpt-5-mini` and 0.74 to 0.75 on
   `gpt-5-nano` across all three settings). This matches the OpenAI reasoning models' fixed
   temperature.
2. **On the models that honor it, temperature trades variety against faithfulness.** More
   variety in names and backstories, but the persona that "states what it does not know"
   (a rule of prompt 2 that later keeps the interviewer inside its knowledge) fell from 85% to
   65% on `gpt-4o-mini` at 1.4. `gemini-2.5-flash` was noisier on that check at every setting.
3. **For the evaluation, temperature moved the wording, not the verdict.** With clear-cut
   transcripts the verdict agreement was 1.00 at every temperature, while the word distance
   between runs rose from 0.41 to 0.71. A low temperature gives a more repeatable text, which
   fits the guidance already in `prompt-engineering.md`, but this benchmark's transcripts are
   not borderline enough to show whether a high temperature would flip a close verdict.
4. **High temperature also hurts format on the weaker models.** With the scratchpad, valid
   replies on `gemini-2.5-flash` fell from 90% at 0 to 75% at 1.4.

## Experiment 4: which model for which task

*Question.* Every task on every model, with the app's defaults. 8 tasks (the image prompt
is excluded): ask-back and evaluation are experiments 1 and 2 (the app's own prompts), the
rest were run for this experiment (432 generations). Each task's score is the share of its
checks that passed, so it compares models *within* a task; a score is not comparable across
tasks. Best in bold.

| task | gpt-5-mini | gpt-5-nano | gpt-4o-mini | gemini-2.5-flash |
|---|---|---|---|---|
| 1. Document analysis | **100%** | 99% | 99% | **100%** |
| 2. Interview plan (3 calls) | **100%** | 67% | 50% | **100%** |
| 3. Live interviewer | **100%** | 89% | 89% | 95% |
| 4. Ask-back suggestions (judge) | **74%** | 71% | 55% | 58% |
| 5. Coaching hint | **100%** | 90% | 94% | 97% |
| 6. STAR evaluation (verdict right) | 98% | **100%** | 92% | 89% |
| 7. Interviewer review (judge) | **100%** | **100%** | 44% | **100%** |
| 8. Progress summary | 98% | **100%** | 87% | 98% |

Cost per 1,000 calls / mean latency, same order:

| task | gpt-5-mini | gpt-5-nano | gpt-4o-mini | gemini-2.5-flash |
|---|---|---|---|---|
| 1. Document analysis | $1.93 / 14.7s | $0.75 / 27.9s | $0.11 / 2.3s | $0.39 / 2.5s |
| 2. Interview plan (3 calls) | $3.42 / 35.7s | $1.27 / 38.0s | $0.21 / 4.0s | $0.99 / 3.9s |
| 3. Live interviewer | $1.08 / 16.4s | $0.44 / 19.7s | $0.16 / 1.6s | $0.50 / 4.2s |
| 4. Ask-back suggestions | $2.60 / 12.3s | $0.76 / 27.1s | $0.18 / 2.5s | $0.49 / 2.6s |
| 5. Coaching hint | $1.50 / 8.1s | $0.51 / 17.4s | $0.09 / 2.1s | $0.24 / 2.4s |
| 6. STAR evaluation | $3.76 / 15.4s | $1.48 / 51.5s | $0.44 / 8.8s | $2.68 / 7.7s |
| 7. Interviewer review | $2.52 / 22.0s | $1.24 / 69.1s | $0.25 / 3.5s | $0.78 / 2.7s |
| 8. Progress summary | $2.62 / 11.6s | $1.32 / 71.3s | $0.21 / 3.6s | $0.89 / 3.5s |

What drives each result:

1. **Document analysis.** All four are equivalent: every gold skill found, the company and
   domain right, and none of the replies to the CV that contains an injected instruction
   (3 per model) listed a planted skill (`Kubernetes`, `Rust`, ...). The cheapest model is enough (`gpt-4o-mini`, a
   seventeenth of `gpt-5-mini`'s cost). The extraction prompt is zero-shot and nothing in
   this data says it needs more.
2. **Interview plan.** The strict composite counts a plan as passed only if the persona, the
   questions and the criteria all pass. `gpt-5-mini` and `gemini-2.5-flash` passed every one;
   `gpt-4o-mini` titled a technical screener "Technical Screener" (the role's label, not a job
   title) and missed the criteria counts in some runs. `gemini-2.5-flash` is 3.5x cheaper and
   9x faster than `gpt-5-mini` for the same score, but it is not in the interview phases'
   allowed models today.
3. **Live interviewer.** `gpt-5-mini` set the `clarification` flag correctly 12 of 12 times and
   followed the situational rule (stay on the question after an off-topic or rude reply, do
   not invent a salary, decline to teach) 12 of 12. `gpt-5-nano` and `gpt-4o-mini` got the
   flag right only 6 of 12 times, and followed the rules 58% and 75% of the time.
4. **Ask-back.** As in experiment 1, a gap between the OpenAI reasoning models and the rest on
   specificity, not on form.
5. **Coaching hint.** The prompt's absolute rule ("never invent experience") is where models
   differ. The judge flagged fabricated experience in **0 of 18** `gpt-5-mini` hints,
   **2/18** on `gemini-2.5-flash`, **4/18** on `gpt-4o-mini` and **7/18** on `gpt-5-nano`.
   The flagged hints typically told the candidate to present a team of 8 as "larger-scale
   capability" when asked about 50 people, or to frame Docker/ECS work as Kubernetes
   experience.
6. **STAR evaluation.** With the scratchpad, `gpt-5-nano` and `gpt-5-mini` are accurate (100%
   and 98%); the other two lose points to invalid replies (see experiment 2), not to wrong
   verdicts. `gpt-5-nano` is 2.5x cheaper than `gpt-5-mini` but 3x slower.
7. **Interviewer review.** `gpt-5-mini`, `gpt-5-nano` and `gemini-2.5-flash` rated the planted
   flaws (a recruiter explaining the GIL and saying "as an AI language model", and an
   interview that asked 8 questions for a target of 3) at 2 or below every time, and did not
   mark down the good interview. `gpt-4o-mini` flagged **1 of 6** and gave the broken persona
   5 out of 5. It is not in the judge's allowed set (ADR 0009), and this is a measured reason
   for that. `gemini-2.5-flash` is the cheapest and fastest of the three that work, which
   supports it being the default judge.
8. **Progress summary.** All models stayed in the right score range and in second person;
   `gpt-4o-mini` broke the 3 to 6 sentence limit in 3 of 9 runs and was the only one that
   treated a harder stage as a worse performance (1 of 3 runs).

**Recommendation by task** (quality first, then cost):

| task | choice | why |
|---|---|---|
| Document analysis | `gpt-4o-mini` | same quality as the rest, cheapest and fastest |
| Interview plan | `gpt-5-mini` (or `gemini-2.5-flash` if allowed) | the other two fail constraints |
| Live interviewer | `gpt-5-mini` | the only model with correct flags and rule-following in every run |
| Ask-back, coaching hint | `gpt-5-mini` | best specificity; the only model with no fabrication |
| Evaluation | `gpt-5-mini` | `gpt-5-nano` is as accurate but slower; the others need the scratchpad removed or tolerated |
| Interviewer review | `gemini-2.5-flash` | detects the flaws, cheapest and fastest |
| Progress summary | `gpt-5-mini` | accurate and 6x faster than `gpt-5-nano` |

This agrees with the app's current defaults (`gpt-5-mini` everywhere, `gemini-2.5-flash` for
the judge).

## What this does and does not show

- **The test cases are small and synthetic.** 8 setups, 9 transcripts, 3 judge cases. Most
  transcripts are clear-cut, so many cells sit at 100% and cannot separate models that differ
  only on borderline cases. The judge and progress-summary cases have few runs per model
  (9 each). Intervals are shown where a paired comparison was run; most other numbers are
  counts out of a small total, given as fractions.
- **The gold labels and rubrics are the author's.** They were written before the outputs were
  read, with the exceptions disclosed above (the `t9` fixture and its reclassification as a
  probe, and three checks that were corrected after the first run: the judge's JSON parsing,
  an "exactly one question" check that counted `?` and so failed openings phrased as "tell me
  about...", and a forbidden-skill check that matched `Go ` inside `Django `). Corrections
  changed only scoring, never the replies.
- **The independent judge is a model.** `claude-haiku-4.5` can be wrong or biased, so it rates
  only what code cannot check (usefulness, specificity, grounding, fabrication, rule-following),
  blind to the arm. The extra evaluation runs beyond the first three per case were not rated
  by the judge (to stay in budget); the judge columns for experiment 2 cover the first three.
- **Some metrics are heuristics.** "Grounded items" (a 4-word overlap with the candidate, or
  two distinctive shared words), "title fits role" (keywords) and "skills not in the text" are
  rough. They are the same for both arms of each comparison, so they are used only to compare
  arms, never as an absolute quality number.
- **One provider, one day.** Results come from OpenRouter on 2026-10-07 with default settings;
  a model version or routing change can move them. `google/gemini-3.5-flash-lite` could not be
  tested (blocked by a workspace guardrail on the key).
- **The app's own guard is not exercised.** The injected-instruction cases test the *prompt's*
  "treat as data" rule. In the app the security guard would usually reject such text before it
  reaches a model.

## Reproducing it

From `interview-practice.server` (the key is read from `OPENROUTER_API_KEY`; nothing is
stored in the repo):

```bash
uv run python ../experiments/run.py e1 e2 e3 e4 judge   # makes the calls; resumable
uv run python ../experiments/analyze.py                  # rebuilds results/tables.md, free
```

Every call is cached in `experiments/results/*.jsonl`, so analysis costs nothing and a run can
be stopped and resumed. The runner stops at `BENCH_BUDGET_USD` (default 4.2). A later change to
a prompt can be checked against the same cases: edit the prompt, re-run the affected stage, and
compare with `tables.md`.

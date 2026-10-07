# Architecture

See [`overview.md`](./overview.md) for the product flow, [`domain-model.md`](./domain-model.md)
for the entities referenced throughout this document, the repo-root
[`CONTEXT.md`](../CONTEXT.md) for canonical vocabulary, and [`adr/`](./adr/) for the
reasoning behind decisions only gestured at here.

## Stack

- **Frontend**: `interview-practice.client` — Angular 22 SPA, standalone components,
  zoneless, Angular Router. Talks only to the Flask API; never calls OpenRouter directly.
  (Flask + Angular over the assignment's suggested Streamlit/Next.js — see
  [ADR 0001](./adr/0001-flask-and-angular-over-streamlit-or-nextjs.md).) UI components via
  **Spartan** (+ Tailwind CSS) — see
  [ADR 0010](./adr/0010-spartan-for-ui-components.md). Request/response shapes validated
  client-side with **Zod**. The server's base URL lives in `environment.apiUrl`
  (`src/environments/environment.ts` / `environment.development.ts`, already scaffolded as
  empty stubs, swapped by `angular.json`'s `fileReplacements` per build config) — **not** an
  OS-level env var, since Angular ships as a static build with no `process.env` at runtime
  in the browser. `environment.development.ts` points at the local Flask dev server (a
  different origin — `http://localhost:8001/api`, i.e. `SERVER_PORT`, hitting real cross-origin CORS);
  `environment.ts` (production, used in the Docker build) is just `/api` — a relative path,
  same-origin behind nginx's reverse proxy (see `deployment.md`), where CORS doesn't
  actually apply at all.
- **Backend**: `interview-practice.server` — Flask, managed with `uv`, structured as an
  **application factory** (`create_app()`) with **Blueprints** per domain area
  (`interviews`, `documents`, `applications`, `preferences`, `dashboard` — see `api-design.md`). Owns
  every OpenRouter call and the security guard. The OpenRouter API key and all prompt
  construction stay server-side — the client never sees a system prompt or an API key. A
  **Pydantic v2** validation layer sits between the API routes and the app's internals —
  parses/validates every request body (and the LLM replies) before it reaches
  business logic. Chosen over Marshmallow for tighter type-hint integration with the
  project's existing mypy-strict setup, and because its `model_validator` mechanism is the
  natural place to enforce cross-field invariants like ADR 0009's judge-model exclusion
  rule, declaratively rather than as scattered manual checks.
- **Database**: Postgres via SQLAlchemy, migrations via **Flask-Migrate**. `config.py`
  assembles `SQLALCHEMY_DATABASE_URI` from the discrete `POSTGRES_*` variables, and the
  models live in `app/models/` (see `database-schema.md`, including its Migrations
  section for how to create and apply migrations).
- **File storage**: local disk, under the Flask app's `instance/` folder (see "Persona
  image generation" and "Document file storage & download" below) — fine since deployment
  is single-host Docker Compose, not multi-instance (see `deployment.md`), as long as that
  folder is a persisted volume.
- **Deployment**: Docker Compose, single-host — see `deployment.md`.
- **Logging/observability**: some logging exists on the server, but there is **no logging
  strategy** yet (levels, format, destination, retention are undecided), and no
  observability beyond that. What exists: the OpenRouter client, the security guard (the
  category of a rejection goes to the log, never to the client), the error handlers (an
  unexpected 500 is logged with its traceback), the live conversation (for example a model
  that tried to end an interview without a warning), and a per-step timing log under the
  `app.timing` logger (`app/llm/timing.py`). Not a hidden gap: decide the strategy before
  this goes anywhere beyond a local prototype.
- **Testing**: the server has automated tests for its critical parts (security guard,
  OpenRouter client, pacing, planning, lifecycle and staleness, results, phase settings,
  preferences, concurrency, the progress summary), DB-free and against a fake LLM transport;
  coverage is partial, not complete. The client has no tests, deliberately. See the Testing
  Decisions in `spec.md`.

## Routes

| Route | Guard |
|---|---|
| `/` | — |
| `/interviews/new` | `CanDeactivate` leave-confirmation |
| `/interviews/:id` | `CanDeactivate` leave-confirmation |
| `/interviews/:id/results` | — |
| `/preferences` | `CanDeactivate` leave-confirmation, only while the model defaults have unsaved edits |
| `/applications/:id` | — |

## UI layout & navigation

Split so the topbar and sidebar each own a distinct job, rather than both offering
navigation:

- **Topbar** — present on every route, unconditional, and sticky. On the left the app mark
  and name linking Home (passes through the leave-confirmation guard below when mid-flow),
  which is the first step of a **breadcrumb trail** saying where the candidate is: each route
  declares its own trail ("New interview", "Interview", "Interview › Results"), earlier steps
  link back, the current page does not. On the right, tools that apply everywhere: a
  **light/dark theme toggle** (remembered in the browser; dark by default). It is the *only*
  place Home navigation lives — neither sidebar duplicates it. Deliberately *not* here: an
  "Abandon" action — see the Interviewer sidebar below for why that never belonged on the
  topbar — nor the "+ New Interview" CTA and the Preferences link, which the History sidebar
  owns for the reason given there.
- **History sidebar** (left) — built with Spartan's `sidebar`: a panel beside the page on wide
  screens and a drawer on narrow ones, shown and hidden by a trigger at the left of the topbar
  (only on the pages that have the sidebar). Visible on Home, Results, Preferences and the
  Application Overview, hidden on Create Interview and Interview Session (keeps those
  flows free of distraction and of the temptation to jump into an unrelated past result
  mid-task). A route opts in with `data: showsHistory()`. Anchored to the top: a **"+ New Interview"**
  CTA, and below it a **Preferences** link (icon *and* text, not either/or) to the
  **Preferences page** (`/preferences`). The history list fills the rest, below both.
  Putting the Preferences link here rather than in the topbar means its availability just
  falls out of the sidebar's existing show/hide rule — mid-flow, the whole sidebar (and the
  Preferences link with it) disappears, instead of the topbar needing its own condition.
  - The history list groups Interviews under their `JobApplication` when they belong to one
    (e.g. "Acme Corp — Senior Software Engineer" as a group header, showing each pipeline
    stage's status at a glance — done/in progress/not started), falling back to a flat,
    ungrouped entry for standalone Interviews with no Application. Each Interview entry
    still opens straight into its own Results page. Groups are collapsible, and each stage
    shows an outcome icon, its interviewer role and its date.
  - The group header itself is clickable, opening `/applications/:id` (the Application
    Overview page — see the Progress summary section below). Its context menu has two ways
    in: a kebab/menu icon that only reveals on hover (not always-visible, but always visible
    on touch screens, which have neither hover nor right-click), and right-click, both
    opening the same menu. It offers **delete** only — **rename** is a known limitation,
    see `overview.md`. A standalone Interview's entry has the same menu. Delete cascades to every
    Interview under it — see
    [ADR 0008](./adr/0008-jobapplication-delete-cascades-to-interviews.md) — so the UI
    needs its own confirmation prompt here, separate from the leave-confirmation guard
    below (that one guards navigating *away mid-session*, not destructive actions taken
    *from* the sidebar).
- **Interviewer sidebar** (right, Interview Session only) — the persona panel from the
  original design, focused purely on interviewer identity: portrait image, `persona_name` +
  `persona_title`, a tone badge (Friendly/Strict/Neutral), `company_name` when one is set
  (nothing shown when it isn't — same optional-field pattern as everywhere else it's used),
  a question-progress count against `target_question_count` (e.g. "Question 3 of ~8" —
  informational pacing, not a clock; distinct from the session-timer idea already
  declined), and an explicit **"Abandon interview"** action. No bio blurb (declined). The
  interviewer-voice toggle sits in the chat header (a per-message replay button is not built). This is the only place Abandon lives: Create Interview has nothing
  persisted yet to abandon (no `Interview` row exists until submission — its
  leave-confirmation guard is only protecting unsaved form input, a different concern), so
  a topbar-level Abandon action never actually made sense there. Abandon here runs through
  the same guard/status-update path as quitting any other way (marks the Interview
  `abandoned`; the Results page then asks for the Evaluation) — a deliberate, discoverable in-app affordance rather
  than something that only works if the candidate hits browser-back.
- **Phase indicator** (main Interview Session content, not the sidebar) — a small
  persistent label pinned above the conversation transcript ("Q&A Phase" / "Ask-Back
  Phase"), kept out of the interviewer sidebar since that panel is about *who* the
  interviewer is, not *where* the candidate is in the flow.
- Both Create Interview and Interview Session are guarded with a **leave-confirmation
  prompt** (`CanDeactivate`, "are you sure you want to leave?") before navigating away,
  whether that navigation comes from the topbar, browser back, or closing the tab.
  The **Preferences page** has the same guard, but only while its model defaults have
  unsaved edits (a clean page leaves without asking), because it is the one page with a
  Save / Discard draft. It covers in-app navigation only: closing or reloading the tab
  does not warn there, unlike on Create Interview and Interview Session.
- The **Preferences page** (see its own section below) sets, per phase, the default
  model, temperature, max tokens and reasoning effort. The judge's model is separate from
  the interview's. The system prompts are fixed in the server and not editable.

## The 5 system prompts / phases

The assignment requires at least 5 system prompts using different prompting techniques.
Each one corresponds to a distinct backend phase of the interview lifecycle, rather than to
5 separate standalone tools:

All five run on **`gpt-5-mini`** by default (selectable among the allowed OpenRouter
chat models via Preferences), using 5 deliberately distinct techniques:

1. **JD/CV analysis** (requested by the client right after a Document is
   uploaded, via `PUT /api/documents/:id/analysis`, using the default model; Create Interview
   runs it at submit only for a Document with no analysis, or when the Interview overrides
   the `jd_analysis` model) — one small call **per Document**
   (job description, CV, cover letter; run in parallel at submit): extracts skills, likely topics,
   the role's domain (job description / CV) and the employer's name (job description /
   cover letter). The result is stored as that Document's `DocumentAnalysis` and reused by
   every later Interview that uses the Document, unless that Interview's `jd_analysis`
   model differs, in which case it is re-run and overwritten — see
   [ADR 0012](./adr/0012-document-analysis-cached-per-document-and-model.md). The
   Interview's `domain` is proposed by the job description's analysis, else the cover letter's, else the CV's, but phase 2 checks the proposal against the job title and company and ignores it when it makes no sense (a software CV for a barista job); the cover letter's analysis therefore also holds a `domain`.
   Technique: **zero-shot** extraction with a structured JSON output contract. Plain context-injection, not RAG —
   see [ADR 0004](./adr/0004-job-description-context-is-not-rag.md).
2. **Question-plan & persona generation** — produces the interviewer persona (name, job
   title, tone, and a knowledge scope/backstory shaped by `interviewer_role`), the question
   plan (skewed
   technical vs. behavioral by `interview_type`: at least 70% of the questions are of the
   interview's own type; the plan holds `target_question_count` core questions plus 3 to `3 + target/4`
   reserves (never more than the target), in all 5→8-9, 10→13-15, 20→23-28, 30→33-41: the interviewer asks only the target number and swaps in a
   reserve when a core question no longer fits, e.g. after a rude candidate, so it never ends on
   salary expectations), and a
   structured set of **Evaluation criteria**
   (technical + behavioral criteria, stored as `EvaluationCriterion` rows; the question plan
   as `InterviewQuestion` rows) — the assignment's
   "generate interviewer guidelines" optional task, folded into this same phase rather
   than a separate one. Seeded by `difficulty`, `domain`, `seniority`, `interview_type`,
   `interviewer_role`, `company_name`, and the JD/CV analysis output. A new stage under an
   existing Application also gets the questions actually asked in that Application's **completed**
   stages (the interviewer's non-clarification messages, not the plans, which hold unasked reserves) (fenced as data, question call only). It may revisit a few of them, reworded (at most a quarter of its questions, so none under 4), but never most or all.
   Technique:
   **instruction/constraint-based prompting** — driven by the explicit structured inputs
   (difficulty/domain/seniority/analysis output) rather than worked examples, which is what
   actually distinguishes it from phase 4's few-shot prompt. The rubric is dev/interviewer
   -side only — not shown to the candidate — and is later fed into phase 5 as grounding so
   the STAR evaluation is judged against the same criteria the plan was built around.
   The phase is **three independent calls run at once** — the persona (`name`, `title`,
   `backstory`), the questions, and the evaluation criteria — because none depends on
   another, only on the shared inputs; so it takes as long as the slowest one, not one
   long reply (reasoning effort is deliberately not lowered to save time). Each reply is
   validated before anything is stored; an incomplete persona, no usable criteria, or
   fewer questions than the target plus 3 reserves (extra reserves are just dropped) fails the
   request with `502` and
   creates nothing, and the other calls are abandoned. The persona call also returns the
   Interview's `domain`, but only when no analyzed Document supplied one; the persona call
   sees only the setup, while the questions and criteria also get the JD/CV analyses. The backstory is stored as
   `Interview.persona_backstory`. The persona's `tone` is an input chosen by the candidate,
   not generated. The model comes from the Interview's `question_plan` setting (default
   `gpt-5-mini`).
3. **Live interviewer conversation** (one call per Q&A turn) — role-plays the generated
   persona, asks the next question, and decides pacing/follow-ups and whether it has
   gathered enough signal to end the Q&A phase early (bounded above by
   `target_question_count`). Technique: **role/persona prompting**. `Interview.response_style`
   (concise/detailed) shapes how elaborate the interviewer's phrasing is. The model gets
   the persona (name, title, backstory), the role, tone, the question plan and the
   transcript, and returns `{message, done, end_interview}`; the server decides what kind of
   turn it is (open, ask, wrap up, answer, close) and enforces the budget. `end_interview`
   is how it ends the whole interview, with no ask-back phase, on a rude or abusive
   candidate: it is honored only after the interviewer has first warned the candidate
   (inside a clarification), and ignored (and logged) otherwise — see
   [ADR 0013](./adr/0013-live-conversation-is-server-paced-and-atomic-per-exchange.md). The
   evaluation criteria are deliberately not shown to it. The model comes from the
   Interview's `live_conversation` setting.
4. **Candidate ask-back suggestions** — generates tailored "questions to ask the
   interviewer" the candidate can accept, edit, or ignore during the ask-back phase, aware
   of `interviewer_role` so suggestions fit what that persona would actually know (e.g. not
   suggesting deep architecture questions to a recruiter persona), and of `company_name`
   when set, so suggestions are genuinely company-specific rather than generic — directly
   matching the assignment's own "questions to ask the interviewer" starter idea. Technique:
   **few-shot**, using example good closing questions as guidance: the prompt carries four
   complete input-to-output examples (one per interviewer role, five suggestions each) and
   the model is asked for five suggestions (fewer than five usable ones is a `502`; extras are trimmed). It also sees the conversation so
   far, so suggestions can build on what was discussed. It is offered only when the
   Interview's coaching-helpers toggle (`coaching_helpers_enabled`, the same one as the
   coaching hints) is on, and runs on the Interview's `coaching_helpers` model and settings,
   the same phase as the coaching hints (one phase for both, as the one toggle governs both).
   Unlike
   the coaching hint, the candidate asks for it, so a failure is a normal error, not a
   missing card.
5. **STAR evaluation** — scores the full transcript (both phases) against the STAR
   framework and the Interview's `EvaluationCriterion` rows (phase 2's criteria, weighted toward
   whichever half — technical or behavioral — matches `interview_type`), and produces a
   verdict
   (`hire`/`no_hire`), reasoning, strengths, weaknesses, and improvement suggestions. The
   verdict's bar scales with the Interview's `difficulty`: lenient on `easy` (an acceptable
   performance passes, only a very poor or disrespectful one doesn't), balanced on `medium`,
   demanding on `hard`. What the interviewer could check also matters: a recruiter or HR
   interviewer can't judge technical details, so a possibly wrong technical claim isn't
   penalized (and is noted as unverified), while rudeness, nonsense and ignoring the question
   always count against the candidate, and drifting off-topic and returning when asked doesn't.
   Technique:
   **chain-of-thought** reasoning constrained to a structured JSON output;
   `Interview.response_style` shapes how long/detailed the reasoning and improvement
   suggestions are. Runs on the `evaluation` phase's model (the Interview's override, else Preferences, else
   the built-in `gpt-5-mini`, recorded on the Evaluation as `model_used` for reproducibility) — see
   [ADR 0003](./adr/0003-self-grading-evaluation-vs-decoupled-interviewer-review.md) for why
   that's deliberate rather than decoupled like the Interviewer Performance Review below.

## Coaching helpers

An optional coaching-hint card shown alongside each Q&A-phase question (e.g. "Talk about
your experience with JavaScript"). Controlled by a single boolean the candidate sets at
Create Interview time (`Interview.coaching_helpers_enabled`, default `false`) — not a live
in-session toggle.

- **Call design**: the hint is its own LLM call, made *after* the question exists and
  *given that exact question* as context (plus the CV/cover letter text and JD analysis
  output, when available), but not as part of the exchange. The interviewer's reply
  (`POST .../messages`, `PUT .../opening`) comes back with `helperText` null, and the session
  page then calls `PUT /api/interviews/:id/messages/:messageId/helper`, so the question is
  on screen after one call and the card arrives while the candidate reads it. It is
  idempotent (a stored hint is returned without calling the model) and takes no turn claim, so
  answering is never blocked by a hint in flight. It was first a second call chained inside
  the exchange, which made every question wait for two sequential reasoning calls; a merged
  prompt or a hint pre-generated from the question plan were considered and not chosen (the
  first mixes two voices and sends the CV to the interviewer; the second depends on the
  interviewer reporting which planned question it asked).
- **Grounding & no-fabrication constraint**: the hint should reference the candidate's
  actual CV/cover letter content where a relevant match exists — but since the right answer
  to a given question won't always be findable in those documents, the prompt must state
  the no-fabrication rule as an absolute, not a soft balance: it may **never** invent
  experience, projects, or skills that aren't actually present in the source text, full
  stop. When there's no grounded match, the fallback below applies instead of inventing
  one. Same plain-text context-injection approach as the JD/CV analysis phase — see
  [ADR 0004](./adr/0004-job-description-context-is-not-rag.md) — just applied to hint
  generation instead of extraction.
- **No CV/cover letter uploaded, or no grounded match found**: falls back to a generic,
  non-personalized coaching hint (e.g. "think of a specific project that demonstrates
  this") rather than fabricating a personal detail or omitting the card entirely.
- Persisted as `Message.helper_text` (see `domain-model.md` / `database-schema.md`) —
  populated only on interviewer messages in the `qa` phase when helpers are enabled; the
  `ask_back` phase has no helper concept, since the candidate is the one asking there. In
  practice that is the interviewer's opening question and every `ask` turn that asks a
  question; the wrap-up message that invites the candidate's questions is already stored as
  an `ask_back` message and gets none.
- **Inputs and settings**: the exact question, the role, the job description's analysis
  (skills and topics), and the CV and cover letter text, each fenced as data. It runs on
  the Interview's `coaching_helpers` model and settings (the phase shared with the ask-back
  suggestions). The hint is capped at 300 characters.
- **Failure**: the hint is a nicety, so if its call fails (provider error, empty reply) the
  message keeps `helper_text` null, the endpoint answers `200` with it, and the card is
  simply not shown; nothing else fails. This is different from "no grounded match", which still gets a generic hint.

## Per-interview advanced settings (nice to have)

A collapsed "advanced settings" section on Create Interview lets the candidate override LLM
settings **per phase**, for just that Interview. Anything not overridden keeps using the
global Preferences defaults (`gpt-5-mini`, Preferences' temperature, etc.).

- Stored as `InterviewPhaseSettings` rows (`interview_phase_settings`), one per overridden
  phase — `jd_analysis`, `question_plan`, `live_conversation`, `coaching_helpers`,
  `evaluation`, plus `interviewer_review` (see below) — each with optional `{model, temperature,
  max_tokens, reasoning_effort}` columns. Any field, or any phase with no row, falls back
  to the global Preferences default. A child table rather than a column per phase per
  setting, which would be a wide, mostly-null `interviews` table; the API still takes and
  returns the nested `phaseSettingsOverride` object.
- **Model choice**: for the 5 candidate-facing phases, the chat models (`gpt-5-mini`,
  `gpt-5-nano`, `gpt-4o-mini`).
- **`interviewer_review`'s model choice is deliberately a different, narrower set**:
  `google/gemini-2.5-flash` (the default — see below), `google/gemini-3.5-flash-lite`,
  `gpt-5-mini`, `gpt-5-nano`. No `gpt-4o-mini` here — the OpenAI options exist as quick, cheap
  experimentation, not an expected path; Gemini stays the recommendation. This is intentionally asymmetric with the
  other 5 phases, not an oversight: the judge's whole point is being a different vendor
  from the interview model, so its override set centers on that instead of mirroring the
  candidate-facing phases' allow-list.
- **`typesafe/jev-1.13` is deliberately not offered, for any phase.** It was considered as a
  judge, being a decisions model (typed questions in, typed answers with probabilities out),
  but OpenRouter refuses it on `/chat/completions`, the only endpoint the server's client
  uses (`400`: "a decisions model and cannot be used with the chat/completions endpoint",
  use `/api/alpha/decisions`). Offering it would have made every review fail, and silently,
  since a judge failure is logged and dropped rather than shown. Supporting it would mean a
  second client for that alpha endpoint and mapping the judge's three scores onto typed
  decisions; not worth it while four chat models already work.
- **Anti-collision rule**: whichever model actually produced this Interview's `question_plan`
  and `live_conversation` phases (accounting for their own per-phase overrides, if set) is
  always excluded from the `interviewer_review` model choices here — so picking, say,
  `gpt-5-nano` for the interview and then also for the judge simply isn't offered. See
  [ADR 0009](./adr/0009-judge-model-excludes-the-interview-model.md).
- This closes the assignment's "all model settings tunable" medium optional task in full —
  Preferences alone only exposed model + temperature; this adds max tokens, reasoning
  effort, and per-phase model choice on top.
- Kept as a collapsed/advanced section rather than a default-visible field, consistent with
  the "keep LLM settings away from the main candidate UX" principle behind the Preferences
  dialog.

## Interviewer performance review (LLM-as-judge)

A sixth, dev-facing prompt beyond the 5 required candidate-facing ones. Where phase 5 (STAR
evaluation) judges the *candidate*, this judges the *AI interviewer's own conduct* for a
given Interview — question relevance/quality, persona consistency, pacing — and is what
actually satisfies the assignment's Hard optional task "assess the performance of your
prompt and/or model via LLM-as-a-judge." Not shown on the candidate-facing Results page by
default; it's a reflection/debugging tool for the developer.

The judge knows the interviewer may stay on a question (a clarification, marked in the
transcript): re-asking or steering back is right when the candidate left part of the question
unanswered, drifted or contradicted themselves, and counts against relevance only when the
question had already been answered or it goes on past two in a row. It also knows the plan
has unasked reserves and that an interview the interviewer ended early shouldn't be
penalized for pacing.

- Runs against the separate **interviewer-judge model**, default `google/gemini-2.5-flash`
  — selected in Preferences (see below) globally, or overridable per-interview via the
  `interviewer_review` key in advanced settings above. Deliberately a different vendor from
  whichever model actually ran this Interview's question-plan generation and live
  conversation, since it's judging output those produced — never the *same* model, by
  construction (see [ADR 0009](./adr/0009-judge-model-excludes-the-interview-model.md)), and
  already a model this project trusts for something else (the persona portrait uses
  `google/gemini-2.5-flash-image`).
- Persisted as `InterviewerReview` (see `domain-model.md` / `database-schema.md`), one per
  Interview.
- **Trigger**: the same call as `Evaluation` (`PUT /api/interviews/:id/evaluation`, made by
  the Results page once the Interview has ended), run **in parallel** with it, so no manual step
  is needed and the candidate waits for the slower of the two, not both. Best effort: a
  failed judge call leaves the review missing and never fails the Evaluation. See
  [ADR 0014](./adr/0014-results-are-generated-on-demand-by-an-idempotent-put.md).
- **Score shape**: `{ question_relevance, persona_consistency, pacing: 1-5 }` plus a
  `reasoning` text field — simple numeric scoring, not a full rubric.

## Progress summary (JobApplication)

A 1-5 aggregate score plus its accompanying narrative, comparing the candidate's
performance across a `JobApplication`'s stages — e.g. score `4`, "you're doing great as
usual on X, better now on Y, a bit worse this time on Z" — surfaced once there's more than
one data point to compare. Both outputs come from the same call and are always
regenerated together; the score isn't derived separately from the narrative or vice versa.

- **Trigger**: on demand, by the idempotent `PUT /api/applications/:id/progress` that the
  Application Overview page calls when the summary is missing or `progressOutdated` — see
  [ADR 0015](./adr/0015-progress-summary-is-generated-on-demand-from-existing-evaluations.md).
  Before it, the page grades every ended stage that has no `Evaluation` through the existing
  `PUT /api/interviews/:id/evaluation` (in parallel; `NOTHING_TO_EVALUATE` stages are skipped,
  `in_progress` ones left alone). Nothing is generated until 2+ stages have an Evaluation.
  Each generation overwrites the previous pair, so it always reflects the full picture so far.
- **Model**: the `evaluation` phase's model and settings from Preferences (an Application has
  no overrides of its own); no seventh phase.
- **Inputs**: every stage's `Evaluation` under that `JobApplication`, oldest stage first
  (`reasoning`, `improvement_suggestions`, the STAR fields, the verdict, `incomplete`, plus the
  stage's role, type, difficulty and evaluation criteria) — deliberately not raw transcripts,
  since the comparison is about assessed performance, not re-reading every conversation.
- **Output**: one structured-JSON call, `{score, summary}`. The score is the overall level across
  the stages so far (1-5); the summary carries the trend.
- **Display**: the `/applications/:id` Application Overview page, reachable from the
  sidebar's `JobApplication` group header (see UI layout & navigation above) — lists every
  stage with its status/link to Results, plus the score and summary once they exist. While a
  summary is being refreshed the page keeps showing the previous one, marked as updating; if
  the refresh fails it says so and offers a retry.
- Persisted as `JobApplication.progress_score` / `progress_summary` / `progress_basis` (see `domain-model.md` /
  `database-schema.md`) rather than a separate entity, since it's a single regenerated pair
  of fields, not a history of past summaries.

## Per-prompt cost tracking (nice to have, not built)

Compute and report the cost of each OpenRouter call (input/output tokens × that model's
price, from OpenRouter's models/pricing endpoint), satisfying the assignment's "calculate
and provide the price of the prompt" optional task, aggregated per Interview. There is **no
Excel export** (dropped) and how the figure would be shown is undecided; a live
running-cost display is real UI work that isn't core to the candidate experience.

State today: the OpenRouter client already reads the `prompt_tokens` and `completion_tokens`
of every response, but nothing stores or uses them, and there is no price lookup.

## Security guard

A single, centralized Flask service that **every** outbound prompt passes through before
reaching OpenRouter — not per-endpoint checks scattered across routes. Applies to:

- Uploaded CV / cover letter / job description text (at Document ingest)
- Live Q&A chat messages
- Ask-back questions

Checks include input length limits, prompt-injection pattern detection, and off-topic/abuse
detection, optionally backed by a cheap classification call. **Built so far**
(`app/llm/guard.py`): length limits (checked first, so the scan is bounded) and
prompt-injection pattern detection that also catches common disguises (invisible
characters, accents, look-alike letters, leetspeak, spaced-out letters); a rejection is a
`422 INPUT_REJECTED`. Wired into Document upload, Create Interview and every chat message
(`POST /api/interviews/:id/messages`, which also carries the candidate's ask-back
questions). Off-topic/abuse detection and the classification call are not built. Bare
"developer mode" is deliberately allowed (mobile developers write about it). Being one
reusable module makes it independently testable and gives a single place to reason about
coverage — important since this is a required part of the assignment, not optional.

**Fencing.** Alongside the guard, `fence()` wraps untrusted text in tags with every angle
bracket escaped, so a prompt can mark it as data. The rule: anything that comes from the
candidate or from a Document, or is derived from them (the job title and company, the
analyzed skills and topics, the CV and cover letter text, the conversation so far), goes
into a fenced block in the *user* message, and the system prompt tells the model to treat
tagged text as data and never follow instructions in it. **One documented exception**: the
live-conversation system prompt (phase 3) states the persona's name, title and backstory,
the role, domain, company, job title and the question plan directly, unfenced, because they
are what defines the interviewer. They are mitigated rather than fenced: the candidate's
own fields pass the guard at the API, and the persona, domain and plan are model output
that is length-bounded and tidied before it is stored (ADR 0012). Fencing them, or moving
them into the user message, would change what the model sees and so needs a real run to
compare interview quality; revisit then. The candidate's replies reach this prompt only as
chat history, never inlined.

## Preferences page

A route (`/preferences`), reachable from the sidebar's Preferences trigger, organized into
tabs. Kept separate from the candidate-facing flow so the practice-interview experience
itself stays simple for a non-technical user.

### Model & Prompts tab

For each of the six phases (JD/CV analysis, question plan, live conversation, coaching
helpers, evaluation, interviewer review), the defaults every Interview starts from:

- **Model**, from the allowed set for the phase (default `gpt-5-mini`, and
  `google/gemini-2.5-flash` for the interviewer review). The five candidate-facing phases
  share one allow-list and the judge has its own narrower, different one, see "Per-interview
  advanced settings". The interview model and the judge are never the same model: the
  judge's choices exclude whichever model the question plan or live conversation is set
  to, and the server refuses the combination (see
  [ADR 0009](./adr/0009-judge-model-excludes-the-interview-model.md))
- **Temperature**, **max tokens** and **reasoning effort**, each optional (unset means the
  provider's default)

An Interview's own advanced settings override these field by field. The system prompts are
not part of Preferences: they stay in the server, so the client never sees one.

### Documents tab

All Document management lives here, not on Create Interview — that page stays a pure
select-existing-or-upload-new control, with no inline management actions of its own:

- View every saved Document (CV, cover letter, job description)
- Rename, delete
- Download the original uploaded file back (see `Document.file_path`, the "Document file
  storage & download" section below)

## Text-to-speech

The interviewer's questions are read aloud using the browser-native **Web Speech API**
(`SpeechSynthesis`), entirely client-side in the Angular app — no backend involvement, no
extra API cost. When a new interviewer `Message` is shown during the Q&A or ask-back phase,
the client speaks its `content` using the browser's available voices/default voice. Only the
message that has just arrived is read, never the history loaded with the page; replying, switching
the voice off or leaving the page silences it. Long text is read in pieces of a sentence or two,
because Chrome stops a long utterance after about 15 seconds.

The voice is **off by default** and switched by a toggle that appears in two places: the chat
header of the Interview Session page and right next to the Tone toggle group in Create
Interview. It is one browser preference (kept in `localStorage`), not part of the Interview: it
isn't sent to the server, so there's no API or schema change, and it applies to every interview
in that browser.

This is a read-aloud of the same transcript text already stored in `messages.content` — it
does not produce or persist a separate audio asset, so it has no schema impact
(`database-schema.md` is unaffected). Voice/rate selection isn't configurable yet (open item
in `overview.md`), and voice availability depends on the user's browser/OS; some browsers
also require a user gesture (e.g. a click) before they'll play audio, which the Interview
Session UI needs to account for on first load.

## Speech-to-text

Letting the candidate answer by voice instead of typing, with **browser-native
`SpeechRecognition`** (Web Speech API) — same client-only pattern as the TTS above. In the
reply box the microphone button takes the place of the send button while there is nothing to
send (which would otherwise sit disabled), and stays while it is listening so it can be
stopped. The live transcript, interim words included, fills the reply box; typing takes over
from dictation, and the candidate reviews/edits before sending as a normal `Message`. Starting
it silences the interviewer's voice so the microphone doesn't hear it. While it listens, a live meter of the microphone's frequency bands (Web Audio API, an
`AnalyserNode`; no package) shows under the box instead of the word "Listening…". It opens the
microphone a second time next to the recognition, so it is best effort: on phones (which usually
can't share the microphone), with reduced motion, or without permission it stays out and the
"Listening…" text shows. Where the browser has no `SpeechRecognition` the send button works as
before. No backend change.

Caveat, accepted rather than solved: support is solid in Chrome/Edge, effectively
unsupported in Firefox, spotty in Safari — and recognition is typically performed by the
browser vendor's own servers (not local), worth being explicit about even for a prototype.
The alternative (record audio, transcribe server-side — more portable, more work, real
per-call cost, a new dependency outside the assignment's OpenRouter allow-list) stays a
later upgrade if cross-browser reliability becomes a real requirement, not the v1 plan.

## Persona image generation

Generated once, when the session page asks for it (`PUT /api/interviews/:id/persona-image`;
not by Create Interview, so the candidate isn't kept waiting) — using
`google/gemini-2.5-flash-image` through OpenRouter's dedicated image endpoint,
`POST /images` (`{model, prompt, n: 1}`; the image comes back base64-encoded in
`data[0].b64_json`). This replaces the earlier `/chat/completions` with `modalities` plan:
OpenRouter's current docs describe only the image endpoint for image generation. The prompt
is built from the persona's name, title and tone (a realistic head-and-shoulders headshot of
a fictional person, no text or logos). The result is stored on **local disk**, under the
Flask app's `instance/` folder (`instance/uploads/personas/<uuid>.<png|jpg|webp>`) —
`Interview.persona_image_path` holds that relative path — rather than regenerated on each
view, so Results and the history sidebar can display it without another API call. The file
type is decided from the image's own bytes, not the provider's `media_type`, and anything
other than PNG, JPEG or WebP (SVG included) is refused.

The portrait is cosmetic, so a failure to generate it (provider error, unusable image)
affects nothing else: the call returns the error, `persona_image_path` stays null, the
client shows a fallback avatar and may retry. The session page requests it in parallel with
the opening message. It is served by `GET /api/interviews/:id/persona-image`.

Note: the assignment's Sprint 1 allow-list only names this one model for image generation,
so there isn't actually a "cheapest option" to pick between within scope — using a
different, cheaper image model would mean stepping outside what's sanctioned for this
sprint. If a real cost figure is needed later, that should come from OpenRouter's live
pricing endpoint (the same mechanism as the per-prompt cost tracking nice-to-have above)
rather than a number quoted here, since model pricing changes over time.

## Document file storage & download

Same local-disk storage as the persona image above (`instance/uploads/documents/<uuid>.<ext>`),
applied to uploaded Documents — see
[ADR 0007](./adr/0007-original-uploaded-file-kept-for-download.md) for why the original
file is kept at all. Served through a simple Flask file-serving endpoint; `source_filename`
supplies the suggested filename on download. Local disk is a deliberate choice, backed by
a persisted Docker volume in deployment — see `deployment.md`.

## Interview lifecycle (sequence)

```
Create Interview
  → security guard checks input
  → JD/CV analysis prompt (per Document; skipped for Documents already analyzed by the
    Interview's `jd_analysis` model — normally done at upload time)
  → question-plan & persona generation prompt
  → Interview row created (status = in_progress)
  → redirect to Interview Session
  → the session page, in parallel: PUT opening (phase 3, first exchange) and
    PUT persona-image

Interview Session
  each Message → updates last_activity_at
  Q&A phase:
    loop: interviewer prompt → candidate reply (guard-checked) → ...
    ends when: target_question_count reached, OR interviewer judges enough signal,
               OR candidate quits explicitly (→ status = abandoned, skip to Evaluation),
               OR interviewer ends it for a rude/abusive candidate, after a warning
               (→ status = completed with no ask-back phase, skip to Evaluation)
  Ask-back phase (always offered, declinable):
    optional: candidate-question-suggestions prompt
    candidate asks 0+ questions (guard-checked) or declines
  → status = completed (or abandoned, if quit earlier)
  → ended_at set
  → Results page asks for the Evaluation (PUT .../evaluation)

[No graceful exit: Alt+F4 / process kill / crash / power loss — see ADR 0006]
  → status is left at in_progress, last_activity_at stops advancing
  → next time this Interview is read (history list, reopening it) and
    last_activity_at is older than the staleness timeout (30 minutes):
    → status = abandoned, ended_at = last_activity_at, then the same Evaluation request
    (same path as an explicit quit, just detected lazily instead of live)

Evaluation
  → STAR evaluation prompt over full transcript (qa + ask_back)
  → incomplete = true if status was abandoned (explicit quit or stale-detected)
  → Evaluation row created
  → redirect to Results
```

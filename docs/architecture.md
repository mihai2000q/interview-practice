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
  (`interviews`, `documents`, `applications`, `preferences` — see `api-design.md`). Owns
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
- **Logging/observability**: not designed yet — genuinely absent, not an oversight being
  hidden. Revisit before this goes anywhere beyond a local prototype.
- **Testing**: no testing strategy designed yet either side (client or server); explicitly
  deferred, not part of this documentation pass.

## Routes

| Route | Guard |
|---|---|
| `/` | — |
| `/interviews/new` | `CanDeactivate` leave-confirmation |
| `/interviews/:id` | `CanDeactivate` leave-confirmation |
| `/interviews/:id/results` | — |
| `/preferences` | — |
| `/applications/:id` | — |

## UI layout & navigation

Split so the topbar and sidebar each own a distinct job, rather than both offering
navigation:

- **Topbar** — present on every route, unconditional: just the app name/logo, left-aligned,
  linking Home (passes through the leave-confirmation guard below when mid-flow). This is
  the *only* place Home navigation lives — neither sidebar duplicates it. No "Abandon"
  action here — see the Interviewer sidebar below for why that never belonged on the
  topbar in the first place.
- **History sidebar** (left) — visible only on Home and Results, hidden on Create Interview
  and Interview Session (keeps those flows free of distraction and of the temptation to
  jump into an unrelated past result mid-task). Anchored to the top: a **"+ New Interview"**
  CTA, and below it a **Preferences** link (icon *and* text, not either/or) to the
  **Preferences page** (`/preferences`). The history list fills the rest, below both.
  Putting the Preferences link here rather than in the topbar means its availability just
  falls out of the sidebar's existing show/hide rule — mid-flow, the whole sidebar (and the
  Preferences link with it) disappears, instead of the topbar needing its own condition.
  - The history list groups Interviews under their `JobApplication` when they belong to one
    (e.g. "Acme Corp — Senior Software Engineer" as a group header, showing each pipeline
    stage's status at a glance — done/in progress/not started), falling back to a flat,
    ungrouped entry for standalone Interviews with no Application. Each Interview entry
    still opens straight into its own Results page. Exact grouped-list visual treatment
    (collapsible groups vs. a simple label prefix) is an open item — see `overview.md`.
  - The group header itself is clickable, opening `/applications/:id` (the Application
    Overview page — see the Progress summary section below). Its context menu (**rename**,
    **delete**) has two ways in: a kebab/menu icon that only reveals on hover (not
    always-visible), and right-click, both opening the same menu. Delete cascades to every
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
  declined), and an explicit **"Abandon interview"** action. No bio blurb (declined). TTS
  controls (replay/mute) are planned here too but deferred until TTS/STT are actually
  built, not now. This is the only place Abandon lives: Create Interview has nothing
  persisted yet to abandon (no `Interview` row exists until submission — its
  leave-confirmation guard is only protecting unsaved form input, a different concern), so
  a topbar-level Abandon action never actually made sense there. Abandon here runs through
  the same guard/status-update path as quitting any other way (marks the Interview
  `abandoned`, triggers Evaluation) — a deliberate, discoverable in-app affordance rather
  than something that only works if the candidate hits browser-back.
- **Phase indicator** (main Interview Session content, not the sidebar) — a small
  persistent label pinned above the conversation transcript ("Q&A Phase" / "Ask-Back
  Phase"), kept out of the interviewer sidebar since that panel is about *who* the
  interviewer is, not *where* the candidate is in the flow.
- Both Create Interview and Interview Session are guarded with a **leave-confirmation
  prompt** (`CanDeactivate`, "are you sure you want to leave?") before navigating away,
  whether that navigation comes from the topbar, browser back, or closing the tab.
- The **Preferences page** (see its own section below) exposes model selection for the
  interview itself (default `gpt-5-mini`), a *separate* model selection for the Interviewer
  Performance Review judge, temperature, and the per-phase system prompts.

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
   Interview's `domain` comes from the job description's (else the CV's) analysis.
   Technique: **zero-shot** extraction with a structured JSON output contract. Plain context-injection, not RAG —
   see [ADR 0004](./adr/0004-job-description-context-is-not-rag.md).
2. **Question-plan & persona generation** — produces the interviewer persona (name, job
   title, tone, and a knowledge scope/backstory shaped by `interviewer_role`), the question
   plan (skewed
   technical vs. behavioral by `interview_type`: at least 70% of the questions are of the
   interview's own type, and exactly `target_question_count` of them are planned), and a
   structured **evaluation rubric**
   (technical + behavioral criteria, stored as `EvaluationCriterion` rows; the question plan
   as `InterviewQuestion` rows) — the assignment's
   "generate interviewer guidelines" optional task, folded into this same call rather than a
   separate one. Seeded by `difficulty`, `domain`, `seniority`, `interview_type`,
   `interviewer_role`, `company_name`, and the JD/CV analysis output. Technique:
   **instruction/constraint-based prompting** — driven by the explicit structured inputs
   (difficulty/domain/seniority/analysis output) rather than worked examples, which is what
   actually distinguishes it from phase 4's few-shot prompt. The rubric is dev/interviewer
   -side only — not shown to the candidate — and is later fed into phase 5 as grounding so
   the STAR evaluation is judged against the same criteria the plan was built around.
   The model returns JSON with the persona (`name`, `title`, `backstory`), the questions
   and the criteria, validated before anything is stored; an incomplete plan, or a
   question count other than `target_question_count`, fails the request with `502` and
   creates nothing. It also returns the Interview's `domain`,
   but only when no analysed Document supplied one. The backstory is stored as
   `Interview.persona_backstory`. The persona's `tone` is an input chosen by the candidate,
   not generated. The model comes from the Interview's `question_plan` setting (default
   `gpt-5-mini`).
3. **Live interviewer conversation** (one call per Q&A turn) — role-plays the generated
   persona, asks the next question, and decides pacing/follow-ups and whether it has
   gathered enough signal to end the Q&A phase early (bounded above by
   `target_question_count`). Technique: **role/persona prompting**. `Interview.response_style`
   (concise/detailed) shapes how elaborate the interviewer's phrasing is. The model gets
   the persona (name, title, backstory), the role, tone, the question plan and the
   transcript, and returns `{message, done}`; the server decides what kind of turn it is
   (open, ask, wrap up, answer, close) and enforces the budget — see
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
   Interview's interview-helpers toggle (`coaching_helpers_enabled`, the same one as the
   coaching hints) is on, and runs on the Interview's `ask_back` model and settings. Unlike
   the coaching hint, the candidate asks for it, so a failure is a normal error, not a
   missing card.
5. **STAR evaluation** — scores the full transcript (both phases) against the STAR
   framework and the Interview's `EvaluationCriterion` rows (phase 2's rubric, weighted toward
   whichever half — technical or behavioral — matches `interview_type`), and produces a
   verdict
   (`hire`/`no_hire`), reasoning, and improvement suggestions. Technique:
   **chain-of-thought** reasoning constrained to a structured JSON output;
   `Interview.response_style` shapes how long/detailed the reasoning and improvement
   suggestions are. Runs on the same model as the rest of the pipeline (`gpt-5-mini`,
   recorded on the Evaluation as `model_used` for reproducibility) — see
   [ADR 0003](./adr/0003-self-grading-evaluation-vs-decoupled-interviewer-review.md) for why
   that's deliberate rather than decoupled like the Interviewer Performance Review below.

## Answer helpers

An optional coaching-hint card shown alongside each Q&A-phase question (e.g. "Talk about
your experience with JavaScript"). Controlled by a single boolean the candidate sets at
Create Interview time (`Interview.coaching_helpers_enabled`, default `false`) — not a live
in-session toggle.

- **Call design**: one client request per Q&A turn still hits a single backend endpoint, but
  when helpers are enabled the backend makes **two sequential, chained LLM calls** rather
  than merging both into one structured response: first phase 3 generates the interviewer's
  question as usual, then a second call generates the helper hint *given that exact
  question* as context (plus the CV/cover letter text and JD analysis output, when
  available). Both results return to the client in one HTTP response. This roughly doubles
  OpenRouter calls during the Q&A phase, but only when helpers are enabled for that
  Interview.
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
  the Interview's `live_conversation` model and settings (there is no separate phase
  setting for it). The hint is capped at 300 characters.
- **Failure**: the hint is a nicety, so if its call fails (provider error, empty reply) the
  message is stored with `helper_text` null and the card is simply not shown; the turn does
  not fail. This is different from "no grounded match", which still gets a generic hint.

## Per-interview advanced settings (nice to have)

A collapsed "advanced settings" section on Create Interview lets the candidate override LLM
settings **per phase**, for just that Interview. Anything not overridden keeps using the
global Preferences defaults (`gpt-5-mini`, Preferences' temperature, etc.).

- Stored as `InterviewPhaseSettings` rows (`interview_phase_settings`), one per overridden
  phase — `jd_analysis`, `question_plan`, `live_conversation`, `ask_back`, `evaluation`,
  plus `interviewer_review` (see below) — each with optional `{model, temperature,
  max_tokens, reasoning_effort}` columns. Any field, or any phase with no row, falls back
  to the global Preferences default. A child table rather than a column per phase per
  setting, which would be a wide, mostly-null `interviews` table; the API still takes and
  returns the nested `phaseSettingsOverride` object.
- **Model choice**: for the 5 candidate-facing phases, all allowed models (`gpt-5-mini`,
  `gpt-5-nano`, `gpt-4o-mini`, `typesafe/jev-1.13`). The picker mechanism is already generic
  per-phase, so there was no remaining reason to keep it artificially restricted.
- **`interviewer_review`'s model choice is deliberately a different, narrower set**:
  `google/gemini-2.5-flash` (the default — see below), `gpt-5-mini`, `gpt-5-nano`,
  `typesafe/jev-1.13`. No `gpt-4o-mini` here — the OpenAI options exist as quick, cheap
  experimentation, not an expected path; Gemini stays the recommendation. This is intentionally asymmetric with the
  other 5 phases, not an oversight: the judge's whole point is being a different vendor
  from the interview model, so its override set centers on that instead of mirroring the
  candidate-facing phases' allow-list.
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
- **Trigger**: automatic, at the same point `Evaluation` runs (session end) — keeps the two
  symmetric, and guarantees the data exists for retrospective review without a manual step.
- **Score shape**: `{ question_relevance, persona_consistency, pacing: 1-5 }` plus a
  `reasoning` text field — simple numeric scoring, not a full rubric.

## Progress summary (JobApplication)

A 1-5 aggregate score plus its accompanying narrative, comparing the candidate's
performance across a `JobApplication`'s stages — e.g. score `4`, "you're doing great as
usual on X, better now on Y, a bit worse this time on Z" — surfaced once there's more than
one data point to compare. Both outputs come from the same call and are always
regenerated together; the score isn't derived separately from the narrative or vice versa.

- **Trigger**: regenerated whenever an Interview under a `JobApplication` completes
  (`completed` or `abandoned`) *and* that Application then has 2+ Interviews with an
  `Evaluation` — not before, since there's nothing to compare against on the first stage.
  Overwrites the previous score/summary each time, so it always reflects the full picture
  so far rather than accumulating stale commentary.
- **Inputs**: every completed stage's `Evaluation` under that `JobApplication` (`reasoning`,
  `improvement_suggestions`, the STAR fields, plus the evaluation criteria each stage was
  judged against) — deliberately not raw transcripts, since the comparison is about
  assessed performance, not re-reading every conversation.
- **Display**: the `/applications/:id` Application Overview page, reachable from the
  sidebar's `JobApplication` group header (see UI layout & navigation above) — lists every
  stage with its status/link to Results, plus the score and summary once they exist.
- Persisted as `JobApplication.progress_score` / `progress_summary` (see `domain-model.md` /
  `database-schema.md`) rather than a separate entity, since it's a single regenerated pair
  of fields, not a history of past summaries.

## Per-prompt cost tracking (nice to have)

Compute and report the cost of each OpenRouter call (input/output tokens × that model's
price, from OpenRouter's models/pricing endpoint), satisfying the assignment's "calculate
and provide the price of the prompt" optional task. Aggregate per Interview and export as an
Excel report — reusing the same reporting format the assignment suggests for jailbreak-test
results, so both nice-to-haves can share one export mechanism. **Export-only** for v1 — a
live running-cost display is real UI work that isn't core to the candidate experience, and
the Excel export alone satisfies the assignment's optional task.

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
`422 INPUT_REJECTED`. Wired into Document upload and Create Interview; the chat and
ask-back endpoints should call it when they are built. Off-topic/abuse detection and the
classification call are not built. Alongside it, `fence()` wraps untrusted text in
tags with every angle bracket escaped, so the prompt can mark it as data. Bare
"developer mode" is deliberately allowed (mobile developers write about it). Being one reusable module makes
it independently testable and gives a single place to reason about coverage — important
since this is a required part of the assignment, not optional.

## Preferences page

A route (`/preferences`), reachable from the sidebar's Preferences trigger, organized into
tabs. Kept separate from the candidate-facing flow so the practice-interview experience
itself stays simple for a non-technical user.

### Model & Prompts tab

- **Interview model** selection (from the allowed OpenRouter chat models, default
  `gpt-5-mini`) — used for all 5 candidate-facing phases above: JD/CV analysis,
  question-plan/persona generation, live conversation, ask-back suggestions, and STAR
  evaluation
- **Interviewer-judge model** selection, default `google/gemini-2.5-flash` — a *separate*
  selector used only for the Interviewer Performance Review (see below), independent of the
  interview model above. This page-level picker supports any OpenRouter chat model, not
  just the interview's 3-model allow-list, since this judge is a distinct, swappable role —
  the narrower 3-choice picker in per-interview advanced settings is a quick override layer
  on top of this global default, not a replacement for it. Whichever model is currently
  selected as **Interview model** above is excluded from this list — the two can never be
  set to the same model, globally or per-interview (see
  [ADR 0009](./adr/0009-judge-model-excludes-the-interview-model.md))
- Temperature
- Viewing/editing the per-phase system prompts

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
extra API cost. When a new interviewer `Message` renders during the Q&A or ask-back phase,
the client speaks its `content` using the browser's available voices/default voice.

This is a read-aloud of the same transcript text already stored in `messages.content` — it
does not produce or persist a separate audio asset, so it has no schema impact
(`database-schema.md` is unaffected). Voice/rate selection isn't configurable yet (open item
in `overview.md`), and voice availability depends on the user's browser/OS; some browsers
also require a user gesture (e.g. a click) before they'll play audio, which the Interview
Session UI needs to account for on first load.

## Speech-to-text (nice to have)

Letting the candidate answer by voice instead of typing. Not built yet, but the approach is
committed: **browser-native `SpeechRecognition`** (Web Speech API) — same client-only
pattern as the TTS above: a mic button starts recognition, the live transcript fills the
reply box, the candidate reviews/edits before sending as a normal `Message`. Small addition
on top of what's already planned, no backend change.

Caveat, accepted rather than solved: support is solid in Chrome/Edge, effectively
unsupported in Firefox, spotty in Safari — and recognition is typically performed by the
browser vendor's own servers (not local), worth being explicit about even for a prototype.
The alternative (record audio, transcribe server-side — more portable, more work, real
per-call cost, a new dependency outside the assignment's OpenRouter allow-list) stays a
later upgrade if cross-browser reliability becomes a real requirement, not the v1 plan.

## Persona image generation

Generated once, at Create Interview time, alongside the question plan/persona — using
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

The portrait is cosmetic, so a failure to generate it (provider error, unusable image) does
**not** fail the Interview: it is logged and `persona_image_path` stays null, and the client
shows a fallback avatar. It is generated in parallel with the interviewer's opening message,
since both need only the persona. It is served by `GET /api/interviews/:id/persona-image`.

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
  → JD/CV analysis prompt (per Document; skipped for Documents already analysed by the
    Interview's `jd_analysis` model — normally done at upload time)
  → question-plan & persona generation prompt
  → persona image generation (stored)
  → interviewer's opening message (phase 3, first turn)
  → Interview row created (status = in_progress)
  → redirect to Interview Session

Interview Session
  each Message → updates last_activity_at
  Q&A phase:
    loop: interviewer prompt → candidate reply (guard-checked) → ...
    ends when: target_question_count reached, OR interviewer judges enough signal,
               OR candidate quits explicitly (→ status = abandoned, skip to Evaluation)
  Ask-back phase (always offered, declinable):
    optional: candidate-question-suggestions prompt
    candidate asks 0+ questions (guard-checked) or declines
  → status = completed (or abandoned, if quit earlier)
  → ended_at set
  → triggers Evaluation

[No graceful exit: Alt+F4 / process kill / crash / power loss — see ADR 0006]
  → status is left at in_progress, last_activity_at stops advancing
  → next time this Interview is read (history list, reopening it) and
    last_activity_at is older than the staleness timeout (TBD):
    → status = abandoned, ended_at = last_activity_at, triggers Evaluation
    (same path as an explicit quit, just detected lazily instead of live)

Evaluation
  → STAR evaluation prompt over full transcript (qa + ask_back)
  → incomplete = true if status was abandoned (explicit quit or stale-detected)
  → Evaluation row created
  → redirect to Results
```

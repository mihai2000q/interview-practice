# Domain Model

See [`overview.md`](./overview.md) for the product-level flow this data model supports,
[`database-schema.md`](./database-schema.md) for the concrete table definitions, and the
repo-root [`CONTEXT.md`](../CONTEXT.md) for the plain-language definition of each term
used here.

This is a single-implicit-user prototype (see [ADR 0002](./adr/0002-single-user-prototype-no-auth.md))
— no `User` entity exists yet. Every entity below is implicitly scoped to "the" user.

## Document

A reusable piece of candidate-supplied text: a CV, a cover letter, or a job description.

- `type`: `cv` | `cover_letter` | `job_description`
- `name`: display name (e.g. original filename, or a name the user gives it)
- `raw_text`: extracted text content (uploads are PDF only, max `MAX_UPLOAD_MB`, default 10 MB, parsed server-side on ingest) —
  what the LLM phases actually read
- `source_filename`: original uploaded filename, used both for reference and as the
  suggested filename when downloading the file back (see `file_path`)
- `file_path`: reference to the original uploaded file on **local disk** (under the Flask
  app's `instance/` folder — see `architecture.md`), kept alongside `raw_text` rather than
  discarded after parsing — see
  [ADR 0007](./adr/0007-original-uploaded-file-kept-for-download.md). Same storage
  mechanism as `Interview.persona_image_path`.
- `saved`: boolean, `true` when a CV or cover letter is uploaded and `false` for a job
  description (a job description is usually specific to one role). The candidate can toggle
  "save for later" right after the upload, which updates it (`PATCH /api/documents/:id`). A
  Document row is *always* created on upload (an Interview's FK needs
  something to point at regardless), but only `saved = true` Documents appear in the
  select-existing list or the Preferences Documents tab — an unsaved one is effectively a
  one-off, used for just that Interview. Because the file is uploaded when it's picked,
  before the Interview is submitted, a candidate who abandons the form leaves an unsaved,
  unreferenced Document behind — accepted for now, see
  [ADR 0011](./adr/0011-documents-are-uploaded-before-the-interview-is-created.md).
- `analysis`: the Document's `DocumentAnalysis`, once phase 1 has run on it (see below)
- `created_at`

## DocumentAnalysis

What phase 1 (JD/CV analysis) extracted from one Document, stored with it and reused by
every Interview that uses the Document — see
[ADR 0012](./adr/0012-document-analysis-cached-per-document-and-model.md). Created lazily
the first time an Interview needs it, not at upload.

- `document_id`: FK → Document (unique — one analysis per Document)
- `model`: the model that produced it. An Interview whose `jd_analysis` model differs
  re-analyzes the Document and overwrites the row
- `domain`: nullable — the role's field; extracted from job descriptions and CVs
- `company_name`: nullable — the employer, extracted from job descriptions and cover
  letters only (a CV lists *past* employers), null when the document doesn't name one
- `skills`: list of text — concrete skills/tools the role calls for (job description) or
  the candidate lists (CV), most important first; empty for a cover letter
- `likely_topics`: list of text — subjects an interviewer would probe; for a CV, what its
  experience invites questions on; empty for a cover letter
- `created_at`

## JobApplication

Groups multiple Interview sessions that represent stages of the same real-world hiring
pipeline (e.g. "Acme Corp — Senior Software Engineer"), so `company_name`/`job_title`/
documents don't need re-entering per stage, and the history sidebar can show pipeline
progress (recruiter ✓, technical screener ✓, hr in progress, hiring manager not started)
instead of a flat, disconnected list of sessions.

Managed directly from its sidebar group header via a context menu — rename and delete,
not a Preferences tab like Document management, since a `JobApplication` is just two text
fields plus optional doc links, nothing uploaded to manage. **Delete cascades**: removing
a `JobApplication` removes all of its `Interview`s with them (and everything hanging off
each — `Message`, `Evaluation`, `InterviewerReview`), not just the grouping — see
[ADR 0008](./adr/0008-jobapplication-delete-cascades-to-interviews.md). The sidebar group
header is also the click target into the `/applications/:id` Application Overview page
(see `architecture.md`).

- `seniority`: e.g. junior / mid / senior; set from the Interview that creates the Application, since the candidate's level doesn't change across the stages of one hiring process. A new stage under it copies its `seniority` from here, and the Create Interview field is locked while the Application is selected, like the job title
- `company_name`: free text, optional — when a stage creates the Application without one, it is read from the job description or cover letter if either names a company
- `job_title`: free text
- `job_description_document_id`: optional FK → Document (`type = job_description`)
- `cv_document_id`: optional FK → Document (`type = cv`)
- `cover_letter_document_id`: optional FK → Document (`type = cover_letter`)
- `progress_score`: nullable integer, 1-5 — an aggregate rating of the candidate's overall
  level across this Application's graded Interview stages, same scale as
  the `InterviewerReview` scores for consistency. Generated together with, and always
  regenerated alongside, `progress_summary` below — the two are one feature's output, not
  independently updatable.
- `progress_summary`: nullable text — the narrative accompanying `progress_score`, which
  carries the trend (e.g. "you're doing great as usual on X, better now on Y, a bit worse
  this time on Z"). Generated on demand once 2+ stages have an Evaluation, and again whenever
  that set changes — see `architecture.md`'s Progress summary section and ADR 0015.
- `progress_basis`: nullable text — fingerprint of the Evaluations the pair above was built
  from; internal, never returned by the API (it surfaces only as `progressOutdated`)
- `created_at`

## Interview

One mock interview session, from creation through evaluation.

- `job_application_id`: optional FK → JobApplication. Nullable — a standalone one-off
  practice session doesn't require setting up an Application first. When creating a new
  stage under an existing Application, Create Interview pre-fills `company_name`/
  `job_title`/documents from it as a convenience; Interview keeps its own copies of those
  fields regardless, so it stays self-contained even if the parent Application is later
  edited or removed
- `job_title`: free text, as entered by the candidate
- `company_name`: free text, optional. The candidate's, or when none is given the one the job description or cover letter names (as for a new Application), else null. Real
  interviews near-universally test whether the candidate researched the company ("what do
  you know about us", "why do you want to work here"); without this field there'd be no
  company identity at all when the JD upload is skipped (it's optional). Feeds persona
  generation (phase 2), the live conversation (phase 3), and — directly matching the
  assignment's own "questions to ask the interviewer" starter idea, which explicitly wants
  a company name — the ask-back suggestions (phase 4)
- `domain`: taken at creation from the job description's `DocumentAnalysis` (else the
  CV's), e.g. "backend engineering"; with no analyzed document, phase 2 supplies it from
  `job_title`/`seniority`. Not a form field, so the candidate never has to categorize their
  own role. Stored on the Interview and fed to the later prompts
- `seniority`: e.g. junior / mid / senior
- `difficulty`: easy | medium | hard — a *preset* that seeds `target_question_count`, `tone`,
  `interview_type`, `response_style`, `coaching_helpers_enabled` and question complexity (the client applies the first five). Each of those remains independently editable after the preset is
  applied, and `difficulty` itself is still passed to the question-plan prompt as its own
  signal (it isn't just a UI shortcut that gets discarded once other fields are tweaked)
- `tone`: strict | neutral | friendly — the interviewer persona's style; a fixed set in the
  client form, stored as plain text so adding one later needs no migration; defaults from
  `difficulty` and `interviewer_role` (last pick wins), independently overridable
- `interview_type`: `technical` | `behavioral` (the API's `InterviewType`; stored as plain text
  like `tone`, so adding one later needs no DB migration) — skews the question plan and which half of
  the `EvaluationCriterion` rows of each category carry more weight at evaluation time
- `interviewer_role`: `recruiter` | `technical_screener` | `hr` | `hiring_manager` (initial set, same
  extensible-text treatment as `tone`) — who the persona *is*, not just their tone:
  - `recruiter` — first-contact screen; shallow technical/company knowledge, broad
    background/motivation questions. Also the natural home for logistics/compensation
    questions (salary expectations, availability, work authorization, remote/hybrid
    preference) — these are near-universal in real recruiter screens and were previously
    missing from the question repertoire entirely
  - `technical_screener` — the first technical interview (a real pipeline often pairs two technical
    interviewers here; modeling only one is out of scope for now); real technical depth,
    and typically the most rigorous/critical stage, since technical screens are prone to
    interviewer bias
  - `hr` — culture/values/soft-skills fit, more procedural in tone
  - `hiring_manager` — real technical depth plus organizational context; framed (as flavor,
    not literal cross-session memory) as the final, more-familiar stage
  Feeds persona generation (phase 2), the live conversation (phase 3), and which ask-back
  questions make sense to suggest (phase 4) — see `architecture.md`. Presented in the UI as
  a select whose options are ordered `recruiter` → `technical_screener` → `hr` → `hiring_manager` to mirror the real-world
  pipeline order, even though one Interview only ever represents a single stage.

  **Default cascade** — `interviewer_role` seeds `interview_type` and `tone` the same way
  `difficulty` seeds `tone`/question count elsewhere: changing `interviewer_role` re-applies
  its row below to `interview_type` and `tone`, even overwriting a prior manual override on
  those two fields — but both remain independently editable again afterward, same as
  `difficulty`'s cascade behavior. `difficulty` and `interviewer_role` both seed `tone` and
  `interview_type`, so the last pick wins. The cascade runs in the client form; the API
  receives the final values.

  | `interviewer_role` | default `interview_type` | default `tone` |
  |---|---|---|
  | `recruiter` | behavioral | friendly |
  | `technical_screener` | technical | strict |
  | `hr` | behavioral | neutral |
  | `hiring_manager` | technical | friendly |
- `target_question_count`: integer, 1–30; a soft cap for the Q&A phase, not a hard requirement,
  since the interviewer can end the phase early. The 30 ceiling is enforced on both client and
  server, so a typo can't produce an hours-long interview
- `status`: `in_progress` | `completed` | `abandoned` — `abandoned` either when the
  candidate explicitly quits mid-session, or when the session goes stale (see
  `last_activity_at` below); evaluation still runs in both cases but is flagged incomplete
- `turn_started_at`: nullable timestamptz — set while a turn is being processed so a second reply is refused with `TURN_IN_PROGRESS`, cleared when the turn ends, and treated as expired after 5 minutes if its request died (see ADR 0013). An Interview with a live marker is never marked stale
- `last_activity_at`: timestamptz, updated on every new `Message`. Staleness timeout: **30
  minutes** — long enough that a candidate thinking mid-answer isn't falsely flagged, short
  enough that history doesn't show obviously-dead "in progress" sessions. The second path
  into `abandoned`, alongside the explicit quit — see
  [ADR 0006](./adr/0006-lazy-staleness-detection-not-a-background-job.md) for why this is
  lazy rather than a background job, and why a graceful client-side signal can't be relied
  on at all.
- `persona_name`: generated interviewer persona's display name
- `persona_title`: generated job title string shown alongside the name (e.g. "Talent
  Acquisition Partner" for a `recruiter`, "Staff Engineer" for a `hiring_manager`) —
  produced by the same phase 2 call as `persona_name`, not a separate generation step
- `persona_backstory`: generated text (3-5 sentences) — the persona's background and
  knowledge scope (what they know well and what they don't), shaped by `interviewer_role`.
  Produced by the same phase 2 call and stored so the live conversation (phase 3) keeps the
  persona consistent every turn, and so the judge can score persona consistency. Never
  shown to the candidate
- `persona_image_path`: nullable — local-disk path to the generated portrait image, under
  the Flask app's `instance/` folder (see `architecture.md` — generated once, stored, not
  regenerated). Null until the portrait is generated (the session page asks for it), and for good if
  generation fails or is switched off: the portrait is cosmetic, so nothing waits for it
- `job_description_document_id`: optional FK → Document (`type = job_description`)
- `cv_document_id`: optional FK → Document (`type = cv`)
- `cover_letter_document_id`: optional FK → Document (`type = cover_letter`)
- `coaching_helpers_enabled`: boolean, set by the candidate at creation, default `false` — whether
  Q&A-phase questions come with a coaching-hint card (see `architecture.md`)
- `response_style`: `concise` | `detailed`, default `concise` — affects the live
  interviewer's phrasing (phase 3) and the evaluation write-up's length/depth (phase 5)
- `phase_settings`: the per-phase advanced-settings overrides, as `InterviewPhaseSettings`
  rows (below)
- `created_at`, `ended_at`

## InterviewPhaseSettings

One phase's LLM overrides for one Interview — the Create Interview "advanced settings".
Belongs to exactly one Interview; a row exists only for a phase the candidate overrode.

- `interview_id`: FK → Interview
- `phase`: `jd_analysis` | `question_plan` | `live_conversation` |
  `coaching_helpers` | `evaluation` | `interviewer_review` (the 5 candidate-facing phases plus
  the judge; `coaching_helpers` covers both the coaching hints and the ask-back suggestions)
- `model`, `temperature`, `max_tokens`, `reasoning_effort`: each nullable; a null field
  falls back to the global Preferences default. See `architecture.md` for the allowed
  models and the judge-model rule.

## InterviewQuestion

One entry of the question plan generated in phase 2: what the interviewer intends to ask
or cover. Belongs to exactly one Interview (created with it, deleted with it) and is not
shown to the candidate.

- `interview_id`: FK → Interview
- `sequence`: order within the plan, from 1. The first `target_question_count` are the core
  questions, the rest reserves the interviewer may swap in (the plan holds the target plus
  reserves: 5→10, 10→15, 20→28)
- `category`: `technical` | `behavioral` — the plan is skewed between the two by
  `Interview.interview_type`
- `question`: text

## EvaluationCriterion

One of the Interview's Evaluation criteria, generated alongside the
question plan in phase 2 and used to ground the STAR evaluation (phase 5). Belongs to
exactly one Interview; not shown to the candidate. The `behavioral` criteria explicitly
include a self-awareness/coachability signal — *how* the candidate talks about a past
failure or weakness (ownership, growth mindset), not just whether their STAR story is
complete — since real interviewers weigh this as much as the story itself.

- `interview_id`: FK → Interview
- `sequence`: order within the Interview's criteria, from 1
- `category`: `technical` | `behavioral`
- `criterion`: text, e.g. "correctly reasons about time complexity tradeoffs"

## Message

One turn in the interview transcript. Ordered, phase-tagged, role-tagged.

- `interview_id`: FK → Interview
- `phase`: `qa` | `ask_back`
- `role`: `interviewer` | `candidate`
- `content`: text
- `helper_text`: nullable text — a coaching-hint card, populated only for `interviewer` /
  `qa`-phase messages when `Interview.coaching_helpers_enabled` is true, and written after the
  message exists, so it is null until the session page asks for it (see `architecture.md`)
- `is_clarification`: boolean, default false — an `interviewer` / `qa` message that stays on the
  previous question (answers the candidate's question or asks them to clarify) instead of asking
  a new one. Not counted toward `target_question_count`; at most two in a row (ADR 0013)
- `sequence`: ordering index within the interview, from 1. The first message of every
  Interview is the interviewer's opening, created when the session page first asks for it (an
  Interview may briefly have no messages). The Interview's current phase is
  the phase of its last message (`qa` before any)
- `created_at`

## Evaluation

The outcome of an Interview. One-to-one with Interview, created once the session ends
(whether `completed` or `abandoned`).

- `interview_id`: FK → Interview (unique)
- `verdict`: `hire` | `no_hire`
- `reasoning`: explanation for the verdict
- `strengths`, `weaknesses`: what went well and where it fell short, one per line; at least
  one of each
- `improvement_suggestions`: what the candidate should work on
- `star_situation`, `star_task`, `star_action`, `star_result`: one short assessment per
  STAR letter, aggregated across the whole interview (not per-question)
- `star_completeness`: `strong` | `partial` | `weak` — the overall STAR completeness rating
- `incomplete`: boolean — true when the Interview was `abandoned`; the evaluation is still
  produced, but explicitly caveated as based on a partial transcript
- `model_used`: the OpenRouter model id actually used to produce this evaluation — what the
  `evaluation` phase resolved to (the Interview's override, else Preferences, else the
  built-in `gpt-5-mini`, see `architecture.md`), recorded here for reproducibility even
  though it isn't decoupled from the interview model
- `created_at`

## InterviewerReview

A separate, dev-facing assessment of how well the **AI interviewer itself** performed in a
given Interview (question relevance/quality, persona consistency, pacing) — distinct from
the candidate-facing `Evaluation` above. This is what actually satisfies the assignment's
"LLM-as-a-judge to assess the performance of your prompt/model" optional task; `Evaluation`
grades the *candidate*, `InterviewerReview` grades the *interviewer*. Runs automatically at
the same call as `Evaluation` (made once the session has ended, in parallel with it), keeping the two symmetric. See
`architecture.md`.

- `interview_id`: FK → Interview
- `judge_model`: the OpenRouter model id used to run this review, default
  `google/gemini-2.5-flash` (selectable globally in Preferences, or overridable per
  Interview via the `interviewer_review` `InterviewPhaseSettings` row's `model`, restricted there to
  `google/gemini-2.5-flash` / `google/gemini-3.5-flash-lite` / `gpt-5-mini` / `gpt-5-nano` / `typesafe/jev-1.13`) — deliberately independent of
  whichever model produced this Interview's question-plan/persona generation (phase 2) and
  live conversation (phase 3): that model is always excluded from the judge-model choices,
  in both Preferences and advanced settings, so the two can never collide — see
  [ADR 0009](./adr/0009-judge-model-excludes-the-interview-model.md)
- `score_question_relevance`, `score_persona_consistency`, `score_pacing`: integers 1-5 —
  simple numeric scoring, not a full rubric
- `reasoning`: free-text explanation of the scores
- `created_at`

Note: evaluation considers the **entire** transcript, including the `ask_back` phase — what
the candidate chooses to ask (or that they decline to ask anything) is itself a signal, the
same way it would read as one to a real interviewer.

## Relationships

```
Document 1──0..* JobApplication   (as job_description_document_id)
Document 1──0..* JobApplication   (as cv_document_id)
Document 1──0..* JobApplication   (as cover_letter_document_id)
JobApplication 1──0..* Interview
Document 1──0..* Interview   (as job_description_document_id)
Document 1──0..* Interview   (as cv_document_id)
Document 1──0..* Interview   (as cover_letter_document_id)
Interview 1──1..* Message
Interview 1──0..1 Evaluation
Interview 1──0..1 InterviewerReview
```

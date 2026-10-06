# API Design

The REST contract between `interview-practice.client` (Angular) and
`interview-practice.server` (Flask). See [`domain-model.md`](./domain-model.md) for full
field definitions — this document only repeats what's needed to understand each endpoint's
shape, not the entities themselves. See [`architecture.md`](./architecture.md) for the
5+1 LLM phases each endpoint triggers.

## Backend structure

Flask **application factory** (`create_app()`) with one **Blueprint** per domain area:
`interviews`, `documents`, `applications`, `preferences`. Each blueprint owns its own
Pydantic request/response models, colocated with its routes (e.g.
`app/interviews/schemas.py`). No blueprint per Evaluation/InterviewerReview/Message — those
are sub-resources of `interviews`, not independent areas.

All routes are under `/api`. JSON throughout, except file upload (`multipart/form-data`)
and file download (binary response) endpoints, called out explicitly below. No
authentication (see [ADR 0002](./adr/0002-single-user-prototype-no-auth.md)) — every route
is open.

## JSON casing

JSON keys are **camelCase** on the wire; Python code and the database stay snake_case. The
conversion happens once, on the server: every Pydantic request/response schema inherits a
shared `ApiModel` base (`alias_generator=to_camel`), so `source_filename` is sent as
`sourceFilename` and incoming `camelCase` is read back into snake_case fields. Only *keys*
are converted. Enum values (`technical_screener`, `in_progress`, `cover_letter`), error
`code`s (`FILE_TOO_LARGE`) and query-string values stay as they are. The Angular client
uses the JSON as-is.

## Error contract

Every error response: `{"error": {"code": "<SNAKE_CASE_CODE>", "message": "<human-readable>", "details"?: {...}}}`.

| Status | When | Example `code` |
|---|---|---|
| 400 | Pydantic validation failure (malformed/missing fields, a value over its length limit), a Document id of the wrong type for its slot, or a model Preferences does not allow for a phase (`MODEL_NOT_ALLOWED`, `details` = `{phase, model, allowed}`), or a reasoning effort it does not allow (`REASONING_EFFORT_NOT_ALLOWED`) | `VALIDATION_ERROR` (for a validation failure, `details` = `{"errors": [...]}`, one entry per failing field: Pydantic's `type`, `loc`, `msg` and `input`) |
| 404 | Resource doesn't exist, including a Document id sent in a request body (`POST /api/interviews`) that matches no Document | `NOT_FOUND` |
| 413 | Upload exceeds the size limit (`MAX_UPLOAD_MB`, default 10) | `FILE_TOO_LARGE` |
| 422 | Well-formed request, but the uploaded file can't be used (not a readable PDF, encrypted, or no extractable text) | `UNPROCESSABLE_FILE` |
| 409 | Request is well-formed but violates a business rule/current state | `JUDGE_MODEL_COLLISION`, `INTERVIEW_ALREADY_ENDED`, `TURN_IN_PROGRESS`, `HELPERS_DISABLED`, `NOT_IN_ASK_BACK_PHASE`, `NOT_A_QUESTION`, `INTERVIEW_NOT_ENDED`, `NOTHING_TO_EVALUATE`, `NOT_ENOUGH_STAGES` |
| 422 | The security guard (or the provider's moderation) refused the text: it looks like prompt injection or is over its length limit. `details` = `{reason}` (plus `field`, the request field, for the JSON bodies) with `reason` one of `prompt_injection` (+ `excerpt`, the matched wording, so the candidate can find it in a long document), `too_long` (+ `maxLength`), `moderation`; the message never names the rule that matched. Applies to `POST /api/documents` (the extracted text, max 50,000 characters; `too_long` possible), `POST /api/interviews` (the free-text fields, `prompt_injection` or `moderation` only: they are capped at 200 characters first, and a longer one is a `400 VALIDATION_ERROR`) and `POST /api/interviews/:id/messages` (the reply, max 2,000 characters; `too_long` possible). Nothing is persisted and no interview state changes, so the client keeps the user's input and lets them edit and resend | `INPUT_REJECTED` |
| 502 | The model provider failed, was unreachable, or returned an unusable/contract-breaking response | `LLM_UPSTREAM_ERROR` |
| 503 | The provider can't serve us right now (rate limit, credits, key); `details.retryAfterSeconds` when known | `LLM_UNAVAILABLE` |
| 504 | The provider took too long | `LLM_TIMEOUT` |
| 500 | Unexpected server error | `INTERNAL_ERROR` (no internals leaked in `message`) |

## `interviews` blueprint — `/api/interviews`

### `POST /api/interviews`

Create Interview submission. Request:

```jsonc
{
  "jobTitle": "string",
  "companyName": "string?",
  "seniority": "string",
  "difficulty": "easy" | "medium" | "hard",
  "targetQuestionCount": "integer",   // 1–30; the client seeds it from difficulty, then sends the final value
  "tone": "strict" | "neutral" | "friendly",  // the client seeds it from difficulty / interviewerRole (last pick wins), then sends the final value
  "interviewType": "technical" | "behavioral",  // the client seeds it from difficulty / interviewerRole (last pick wins), then sends the final value
  "interviewerRole": "recruiter" | "technical_screener" | "hr" | "hiring_manager",
  "responseStyle": "concise" | "detailed",  // the client seeds it from difficulty (hard → detailed), then sends the final value
  "coachingHelpersEnabled": false,  // the client seeds it from difficulty (on for easy), then sends the final value
  "jobDescriptionId": "uuid" | null,
  "cvId": "uuid" | null,
  "coverLetterId": "uuid" | null,
  "jobApplication": { "id": "uuid" } | { "createNew": true } | null,  // null = standalone
  "phaseSettingsOverride": { /* see database-schema.md, camelCased — optional, includes interviewerReview */ }
}
```

- Free-text fields (`jobTitle`, `companyName`, `seniority`) are 1–200
  characters after trimming. A longer value is a `400 VALIDATION_ERROR`, not a guard
  rejection.
- `jobDescriptionId`/`cvId`/`coverLetterId` — always the id of an existing `Document` of the
  matching type (`404 NOT_FOUND` for an unknown id, `400` for a Document of the wrong type), never an inline
  file: this request is plain JSON. A new file is uploaded earlier, the moment the
  candidate picks it, via `POST /api/documents` below, and the returned `id` goes here —
  see [ADR 0011](./adr/0011-documents-are-uploaded-before-the-interview-is-created.md).
  The server reads `Document.raw_text` from the database for the JD/CV analysis phase;
  the client never re-sends the file.
- `jobApplication` — `null` for a fully standalone Interview (no `JobApplication` at
  all); `{id}` to add this Interview as the next stage of an existing one (pre-fills
  `companyName`/`jobTitle`/documents from it, per `workflow.md`); `{createNew: true}`
  creates a fresh `JobApplication` from this request's `companyName`/`jobTitle` and
  attaches this Interview as its first stage. If `companyName` is absent, the
  Application's company is read from the job description or cover letter (left null if
  neither names one).
  The Interview's own `companyName` is resolved the same way: the one given, else the one
  the job description or cover letter names, else null. The persona, the live interviewer
  and the ask-back suggestions all use that resolved value.

The call runs phase 1 (JD/CV analysis, normally already cached from the upload) and phase 2
(question plan, persona and evaluation criteria), stores the Interview and returns. It does
**not** create the interviewer's opening message or the portrait: the session page asks for
those when it loads, with the two idempotent calls below, so the candidate reaches the
session without waiting for them. A failure of analysis or plan returns the usual
`502`/`503`/`504` and creates nothing.

Response `201`: the created `Interview` (id, `status: "in_progress"`, `personaName`,
`personaTitle`, `personaImageUrl` (`null` until the portrait exists), `targetQuestionCount`,
etc., and `phaseSettingsOverride`: the overrides stored for the Interview, in the same
camelCase shape the request takes, `{coachingHelpers: {model, maxTokens}}`, with only the
phases and settings that were set) — **not** the question plan or the evaluation criteria,
which stay hidden from the candidate. It has no messages yet.

### `PUT /api/interviews/:id/opening`

No body. Creates the interviewer's opening message (a greeting and the first question, phase
`qa`; its coaching helper is asked for separately) and returns it as a `Message`
(`{id, phase, role, content, helperText, sequence, createdAt}`). **Idempotent**: an
Interview that already has messages returns its first message and calls no model. Two calls
at once run the model once; the other gets `409 TURN_IN_PROGRESS`, and the client should
re-read the Interview. A failure (`502`/`503`/`504`) leaves the Interview untouched, and
the client retries. `409 INTERVIEW_ALREADY_ENDED` if it is no longer `in_progress` and has
no messages yet (one that already has messages returns its first message, ended or not).
Replying before the opening exists is refused with `409 INTERVIEW_NOT_OPENED`.
See [ADR 0013](./adr/0013-live-conversation-is-server-paced-and-atomic-per-exchange.md).

### `PUT /api/interviews/:id/persona-image`

No body. Generates the persona's portrait (see "Persona image generation" in
`architecture.md`) and returns `{personaImageUrl}`. **Idempotent**: an Interview that has a
portrait returns its URL and calls no model. `personaImageUrl` is `null` when portrait
generation is switched off (`PORTRAIT_GENERATION_ENABLED=false`). A failure of the image
service is a `502`/`503`/`504` that affects nothing else; the client keeps its fallback
avatar and may retry. Two calls at once may both generate an image, but only one is kept.

### `GET /api/interviews`

Every Interview, newest first (`createdAt` descending), as a summary — what the history
sidebar needs to draw each entry without opening it: `{id, jobTitle, companyName,
interviewerRole, status, verdict, jobApplicationId, createdAt, endedAt}`. `companyName` is
the Interview's resolved company (or `null`), `jobApplicationId` is `null` for a standalone
Interview, `endedAt` is `null` while it is `in_progress`, and `verdict` (`"hire"` |
`"no_hire"`) is `null` until an `Evaluation` exists — it is read, never generated here (the
Results page makes it, see ADR 0014). Stale `in_progress` Interviews are closed as they are
read, as everywhere else ([ADR 0006](./adr/0006-lazy-staleness-detection-not-a-background-job.md)),
so a dead session never shows as running. Response `200`, an empty array when there are none.
The client groups the entries under their Application with `GET /api/applications`
(entries with `jobApplicationId: null` are listed on their own).

### `GET /api/interviews/:id`

Fetch an Interview plus its `Message`s (ordered by `sequence`), for rendering the session
or resuming one already in progress. Response `200`: the Interview fields (as in the create
response, plus `endedAt`), `phase` (`"qa"` | `"ask_back"`, the phase of the last message)
and `messages: [{id, phase, role, content, helperText, sequence, createdAt}]`. An
`in_progress` Interview with no activity for 30 minutes is flipped to `abandoned` as it is
read ([ADR 0006](./adr/0006-lazy-staleness-detection-not-a-background-job.md)). `404` for
an unknown id.

### `GET /api/interviews/:id/persona-image`

The persona's portrait: the stored PNG/JPEG/WebP file (`X-Content-Type-Options: nosniff`,
cached for an hour). `404` for an unknown Interview, one with no portrait, or a missing file.

### `POST /api/interviews/:id/messages`

Candidate submits a reply during the Q&A or ask-back phase. Request: `{"content": "string"}`
(1-2,000 characters, passed through the security guard: `422 INPUT_REJECTED` with
`details.field = "content"`).

Response `200`: `{candidateMessage, interviewerMessage, phase, status}`: the stored
candidate `Message` and the next interviewer `Message` (its `helperText` is always `null`
here: the coaching helper is asked for with `PUT .../helper` below), both generated and
stored in the same call, the current `phase`
(`"qa"` | `"ask_back"`) and `status`. See
[ADR 0013](./adr/0013-live-conversation-is-server-paced-and-atomic-per-exchange.md) for how a
turn works: the server counts the interviewer's questions against `target_question_count`
and forces the wrap-up when the budget is spent; the interviewer message that ends the Q&A
phase is the first `ask_back` message (it invites the candidate's questions); the Interview
becomes `completed` when the interviewer closes the ask-back phase. A turn is
all-or-nothing: if the model fails, nothing is stored and the candidate can send the reply
again. `409 INTERVIEW_ALREADY_ENDED` if the Interview is no longer `in_progress`, and
`409 TURN_IN_PROGRESS` if the previous reply is still being answered (the client should wait
for it, not resend). The Evaluation and InterviewerReview are not made here: the Results
page asks for them with `PUT .../evaluation` below.

### `PUT /api/interviews/:id/messages/:messageId/helper`

No body. Writes the coaching helper (the hint card) for an interviewer's Q&A question and
returns the `Message` with `helperText` set. The session page calls it for each new
question when the Interview's helpers toggle is on, so the question appears at once and the
card follows while the candidate reads. It runs on the Interview's `live_conversation` model
and settings. **Idempotent**: a message that already has a helper returns it and calls no
model; two calls at once run the model twice, the first to store wins and both get that
text. It does not take the turn claim, so the candidate can answer while it is written.
A hint the model could not write is not an error: `200` with `helperText: null`, and the
card is left out. `404` for an unknown Interview or message, `409 HELPERS_DISABLED` if the
toggle is off, `409 NOT_A_QUESTION` for a candidate message or one outside the Q&A phase
(the wrap-up and ask-back messages have none), `409 INTERVIEW_ALREADY_ENDED` once the
Interview is over and the message has no helper.

### `GET /api/interviews/:id/ask-back-suggestions`

Phase 4 call. Ephemeral — returns candidate-question suggestions the client can offer, but
nothing is persisted until the candidate actually sends one via `POST .../messages`.

Response `200`: `{"suggestions": [string, ...]}` (five; the server trims extras). `409`
`HELPERS_DISABLED` if the Interview's coaching-helpers toggle is off, `409`
`NOT_IN_ASK_BACK_PHASE` before the Q&A phase has ended, `409` `INTERVIEW_ALREADY_ENDED`
once the Interview is over; `502`/`503`/`504` when the provider fails (no suggestions is an
error, not an empty list). A `GET` because it has no side effects on the Interview.

### `POST /api/interviews/:id/abandon`

No body. The Interviewer-sidebar "Abandon interview" action. Marks `status: "abandoned"`,
`endedAt`, returns the Interview like `GET /api/interviews/:id` (`409 INTERVIEW_ALREADY_ENDED`
if it already ended). Like a completed Interview, it is then evaluated by `PUT .../evaluation`
(with `incomplete: true`).

### `DELETE /api/interviews/:id`

Deletes one Interview and everything hanging off it (`Message`s, question plan, evaluation
criteria, phase settings, `Evaluation`, `InterviewerReview`), plus its stored persona portrait
file (best effort, after the rows are gone). The sidebar offers it for a **standalone**
Interview (one with no Application); for an Interview inside an Application the whole
Application is deleted instead (`DELETE /api/applications/:id`), though the endpoint itself does
not forbid deleting a single stage. The client confirms first; the API performs no
confirmation step. Documents are not deleted. Response `204`, no body; `404` for an unknown
Interview. Allowed in any status, including `in_progress`.

### `PUT /api/interviews/:id/evaluation`

Results page call. No body. Makes the Interview's `Evaluation` (phase 5) **and** its
`InterviewerReview` (the judge) from the stored transcript, **in parallel** on the models of
the `evaluation` and `interviewer_review` phases, stores both and returns the Evaluation, same
shape as `GET` below. Nothing is made when an Interview ends, so ending one (the last
`POST .../messages`, `POST .../abandon`) stays fast; see
[ADR 0014](./adr/0014-results-are-generated-on-demand-by-an-idempotent-put.md).
**Idempotent**: an Interview that has an Evaluation answers with it at once and calls no
model; two calls at once may both run the models, the first to store wins and both get that
text. The review is a dev-facing extra: if the judge's call fails, the Evaluation is still
stored and returned, the review is simply missing, and it is not retried by later calls.

`409 INTERVIEW_NOT_ENDED` while the Interview is `in_progress`, `409 NOTHING_TO_EVALUATE` if
the candidate never sent a message (an abandoned Interview with only the opening),
`409 JUDGE_MODEL_COLLISION` if Preferences changed since the Interview was created so that the
judge now resolves to an interviewer model ([ADR 0009](./adr/0009-judge-model-excludes-the-interview-model.md);
nothing is generated, and it works again once the Preferences are fixed), `404` for an
unknown Interview, `502`/`503`/`504` when the Evaluation's model call fails (nothing is
stored; the client retries).

### `GET /api/interviews/:id/evaluation`

The stored `Evaluation` (Results page data), never generates one:
`{verdict, reasoning, improvementSuggestions, starBreakdown, incomplete}`. `verdict` is
`"hire"` | `"no_hire"`; `improvementSuggestions` is text with one suggestion per line;
`starBreakdown` is `{situation, task, action, result, completeness}` where `completeness` is
`"strong"` | `"partial"` | `"weak"`; `incomplete` is `true` when the Interview was abandoned
(the evaluation then says it rests on a partial interview). `404` until `PUT` has made it.

### `GET /api/interviews/:id/interviewer-review`

The `InterviewerReview` — dev-facing, for the reflection/debugging use case. The Results page
asks for it once the `PUT` has returned and shows it in its own section, set apart from the
candidate's results and marked as being about the interviewer, not the candidate:
`{judgeModel, scores: {questionRelevance, personaConsistency, pacing}, reasoning}`, scores
from 1 to 5. Made by the same `PUT .../evaluation` call. `404` until then, and also if the
judge's call failed there (the page then says there is no review).

## `documents` blueprint — `/api/documents`

### `GET /api/documents?type=cv|cover_letter|job_description`

List saved Documents (`saved = true` only), newest first — backs both the Create Interview
select-existing control and the Preferences Documents tab. Response `200`: an array of
`{id, type, name, sourceFilename, saved, analysisModel, createdAt}`. `analysisModel` is the model
that made the Document's cached `DocumentAnalysis`, or `null` if it has none, so Create Interview
can say whether the interview will reuse it or analyze the Document again (the analysis is kept
per Document and model, see ADR 0012). `raw_text` and `file_path` (database columns) are
deliberately not returned (the first is large and only the LLM phases need it; the second
is a server filesystem path). An unknown `type` value is a `400`.

### `POST /api/documents`

`multipart/form-data`: `file`, `type`, `name?`, `save: boolean`. A row is always created
regardless of `save` (see `domain-model.md`'s `saved` field) — parses the upload
server-side into `raw_text`, stores the original on local disk (`file_path`, relative to
the Flask `instance/` folder). `name` defaults to the uploaded filename. Called as soon as
the candidate picks a file in Create Interview (or uploads from the Preferences Documents
tab). Create Interview uploads with `save: true` for a CV or cover letter and `save: false` for a
job description; the "save for later" checkbox, shown after the upload, changes it
through `PATCH`.

**PDF only, max `MAX_UPLOAD_MB` (default 10 MB).** `400` for a missing file, a non-`.pdf` filename, or invalid
fields; `413 FILE_TOO_LARGE` over the limit; `422 UNPROCESSABLE_FILE` if the file isn't a
readable PDF, is encrypted, or has no text layer (scanned PDFs — there is no OCR).
Response `201`: the created Document, same shape as the list items.

### `PUT /api/documents/:id/analysis`

Runs phase 1 (JD/CV analysis, see `architecture.md`) on the Document and stores the result
as its `DocumentAnalysis`. The optional JSON body is the `jdAnalysis` entry of
`phaseSettingsOverride` (`{model?, temperature?, maxTokens?, reasoningEffort?}`, the same
shape as in `POST /api/interviews`); without it the default `jd_analysis` model is used. A
`PUT` because it is **idempotent**: if the Document already has an analysis from the model
that applies it answers at once, without calling the LLM.

The client calls it **right after an upload** in Create Interview, showing the
attachment with an "Analyzing document…" indicator and keeping the Start button disabled
meanwhile. For a Document the candidate picks (a saved one, or one an Application pre-fills) it
does not call it on its own: each shows "Document analyzed!" when its `analysisModel` is the
model the interview will use (the form's `jdAnalysis` model override, else the default), "Document
not analyzed" when it is `null`, and "Document analyzed with a different model" when it differs.
The last two offer an "Analyze now" / "Analyze again" button, which makes this call with the form's
`jdAnalysis` override (Start is disabled while it runs). If one still doesn't match at submit,
`POST /api/interviews` analyzes it then. There is no cancel: the candidate stops the analysis by removing the
attachment, which abandons the request and deletes the Document. The attachment shows the
outcome: "Document analyzed!" once it has an analysis from the model the interview will use. A failure is handled by
who is at fault: if the Document itself is rejected (`422 INPUT_REJECTED`), the client
deletes it and tells the candidate to use a different file; for any other failure (provider
unavailable, timeout, network), which is not the Document's fault, the client keeps the
Document and shows "Document not analyzed" with an "Analyze now" button that calls this
endpoint again; if the candidate doesn't, the analysis runs at submit. See
[ADR 0012](./adr/0012-document-analysis-cached-per-document-and-model.md).

Response `200`: `{model, domain, companyName, skills, likelyTopics}` (`domain` and
`companyName` may be `null`). `404 NOT_FOUND` for an unknown Document; `502`/`503`/`504`
(`LLM_UPSTREAM_ERROR`/`LLM_UNAVAILABLE`/`LLM_TIMEOUT`) when the provider fails. Abandoning
the request is client-side only: the server finishes the call and caches the result, unless
the Document was deleted in the meantime.

### `GET /api/documents/:id/download`

Binary response (the original uploaded file), `Content-Disposition` filename from
`source_filename` (the stored column).

### `PATCH /api/documents/:id`

`{"name"?: "string", "saved"?: boolean}` — at least one; `name` is 1–200 characters after
trimming. Rename comes from the Preferences Documents tab; `saved` from the "save for later"
checkbox in Create Interview. `400` if neither is given. Response `200`: the updated
Document.

### `DELETE /api/documents/:id`

Hard delete: removes the row and the stored file from disk. Interviews and Job Applications
that referenced the Document are kept and just lose the link (`ON DELETE SET NULL`, see
`database-schema.md`). Response `204`.

## `applications` blueprint — `/api/applications`

### `GET /api/applications`

List, newest first: `id`, `companyName`, `jobTitle`, `seniority`, the optional documents
`jobDescription`/`cv`/`coverLetter` — each `{id, name, analysisModel}` or `null`, so Create Interview can
pre-fill a new stage and show an attached document by name even when it isn't `saved` — and
`interviews` — each stage's `id`, `interviewerRole` and `status`, oldest first (a stage
that went stale is closed as it is read, so it shows `abandoned`, per
[ADR 0006](./adr/0006-lazy-staleness-detection-not-a-background-job.md)). Backs the
sidebar's grouped history and the application select in Create Interview. Response `200`,
an empty array when there are none.

### `GET /api/applications/:id`

Application Overview page data: `id`, `companyName`, `jobTitle`, `seniority`, the documents
`jobDescription`/`cv`/`coverLetter` (each `{id, name, analysisModel}` or `null`, as in the list),
`progressScore`/`progressSummary` (both `null` until generated), `progressOutdated` (`true` when
2+ stages have an Evaluation and the stored pair was not built from exactly those), `createdAt`, and `interviews` —
every stage oldest first, each `{id, interviewerRole, status, verdict, createdAt, endedAt}`.
`verdict` is read off the stored Evaluation and is `null` until one exists; the client links a
stage to its Results (or, while `in_progress`, to the session). A stage that went stale is closed as
it is read ([ADR 0006](./adr/0006-lazy-staleness-detection-not-a-background-job.md)). `404` for an
unknown Application.

### `PUT /api/applications/:id/progress`

Makes the progress summary if it is missing or outdated, and returns it:
`{progressScore, progressSummary}`. Idempotent: when the Application's Evaluations still match
the ones the stored pair was built from, it answers with it and calls no model. It only reads
Evaluations that exist; the client first grades the ended stages that have none, through
`PUT /api/interviews/:id/evaluation`
([ADR 0015](./adr/0015-progress-summary-is-generated-on-demand-from-existing-evaluations.md)).
`404` for an unknown Application, `409 NOT_ENOUGH_STAGES` with fewer than two Evaluations.
The model call runs on the `evaluation` phase's Preferences settings; a failure (`502`/`504`)
leaves any previous summary in place.

### `PATCH /api/applications/:id`

`{"companyName": "string", "jobTitle": "string"}` — sidebar context-menu rename. **Not built**:
renaming is a known limitation (see `overview.md`); the sidebar menu only deletes.

### `DELETE /api/applications/:id`

Cascades to every Interview under it and everything hanging off each (see
[ADR 0008](./adr/0008-jobapplication-delete-cascades-to-interviews.md)) — the client must
confirm before calling this; the API itself performs no confirmation step. The Documents the
Application and its Interviews point at are **not** deleted (they are managed on their own),
but each Interview's stored persona portrait file is removed from disk, best effort and after
the rows are gone, so a missing file never fails the call. Response `204`, no body. `404` for
an unknown Application. Deleting is also allowed while one of its Interviews is `in_progress`
(the confirmation says so); a model call still running for it simply finds nothing to store.

## `preferences` blueprint — `/api/preferences`

Singleton resource, no `:id`. The app-wide defaults for the six LLM phases, which an
Interview's `phaseSettingsOverride` is layered on top of: each setting resolves from the
Interview's override, else Preferences, else the built-in default (`gpt-5-mini`, and
`google/gemini-2.5-flash` for `interviewerReview`). The system prompts are not
configurable and never leave the server.

Both endpoints speak one shape, keyed by the same six phases as `phaseSettingsOverride`
(`jdAnalysis`, `questionPlan`, `liveConversation`, `coachingHelpers`, `evaluation`,
`interviewerReview`), each `{model, temperature, maxTokens, reasoningEffort}`.

### `GET /api/preferences`

Response `200`: **every** phase, with what it runs on by default. `model` is always a
string (the built-in default if none was chosen); `temperature`, `maxTokens` and
`reasoningEffort` are `null` when unset, meaning the provider's own default.

### `PATCH /api/preferences`

Partial update: only the phases named are touched, and within a phase only the settings
named, e.g. `{"evaluation": {"temperature": 0.2}}`. An explicit `null` resets: a setting
sent as `null` goes back to the built-in default, and a phase sent as `null` resets all
of its settings. `temperature` is 0–2, `maxTokens` at least 1. Response `200`: the whole
resource, same as `GET`.

- `400 VALIDATION_ERROR` for an unknown phase or setting, an out-of-range value, or an
  empty body.
- `400 MODEL_NOT_ALLOWED` if a `model` is not one the phase may run on: `gpt-5-mini`,
  `gpt-5-nano` or `gpt-4o-mini` for the five candidate-facing phases; `google/gemini-2.5-flash`,
  `google/gemini-3.5-flash-lite`, `gpt-5-mini`, `gpt-5-nano` or `typesafe/jev-1.13` for
  `interviewerReview` (see `architecture.md`). `POST /api/interviews` and
  `PUT /api/documents/<id>/analysis` answer it too, for the `model` of their overrides.
- `400 REASONING_EFFORT_NOT_ALLOWED` if a `reasoningEffort` is not `minimal`, `low`, `medium`
  or `high` (`details` = `{reasoningEffort, allowed}`). `POST /api/interviews` and
  `PUT /api/documents/<id>/analysis` answer it too, for the `reasoningEffort` of their overrides.
- `409 JUDGE_MODEL_COLLISION` if the result would give `interviewerReview` the same model as
  `questionPlan` or `liveConversation` ([ADR 0009](./adr/0009-judge-model-excludes-the-interview-model.md)).
  It is checked on the defaults *as they will be*, so both models can be swapped in one
  request, and nothing is saved when it fails. `POST /api/interviews` runs the same check
  with the Interview's overrides on top.

## `dashboard` blueprint — `/api/dashboard`

### `GET /api/dashboard`

Aggregate numbers for the Home page, so the client does not crunch a full Interview list
itself. Its own tiny blueprint. Response `200`:

```json
{
  "totalInterviews": 12,
  "byStatus": { "inProgress": 1, "completed": 9, "abandoned": 2 },
  "outcomes": { "hire": 5, "noHire": 3, "awaitingEvaluation": 2 },
  "recent": [
    {
      "id": "…", "jobTitle": "Senior Engineer", "companyName": "Acme",
      "interviewerRole": "recruiter", "status": "completed", "verdict": "hire", "endedAt": "2026-10-06T09:10:00Z"
    }
  ]
}
```

- `totalInterviews` counts every Interview ever created; `byStatus` splits it (the three
  always add up to the total). Stale `in_progress` Interviews are closed first
  ([ADR 0006](./adr/0006-lazy-staleness-detection-not-a-background-job.md)), so the counts
  agree with the history list.
- `outcomes.hire` / `outcomes.noHire` count stored `Evaluation`s by `verdict`.
  `outcomes.awaitingEvaluation` counts Interviews that have ended and in which the candidate
  sent at least one message, but have no `Evaluation` yet — results are only made when the
  Results page is opened ([ADR 0014](./adr/0014-results-are-generated-on-demand-by-an-idempotent-put.md)),
  so this is the "go and open your results" number. An abandoned Interview with nothing to
  grade (`NOTHING_TO_EVALUATE`) is in none of the three outcomes.
- `recent` is the (up to) 5 Interviews that ended most recently, newest `endedAt` first, each
  `{id, jobTitle, companyName, interviewerRole, status, verdict, endedAt}` with `verdict` `null` when it has no
  `Evaluation`. This is the "trend" the Home page draws.
- All counts are `0` and `recent` is `[]` when there is nothing yet (the Home page then shows
  its onboarding state). The endpoint only reads: it never generates an `Evaluation`.

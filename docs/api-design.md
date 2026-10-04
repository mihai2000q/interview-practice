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
| 400 | Pydantic validation failure (malformed/missing fields) | `VALIDATION_ERROR` (`details` = Pydantic's per-field errors) |
| 404 | Resource doesn't exist | `NOT_FOUND` |
| 413 | Upload exceeds the size limit (`MAX_UPLOAD_MB`, default 10) | `FILE_TOO_LARGE` |
| 422 | Well-formed request, but the uploaded file can't be used (not a readable PDF, encrypted, or no extractable text) | `UNPROCESSABLE_FILE` |
| 409 | Request is well-formed but violates a business rule/current state | `JUDGE_MODEL_COLLISION`, `INTERVIEW_ALREADY_ENDED`, `TURN_IN_PROGRESS`, `HELPERS_DISABLED`, `NOT_IN_ASK_BACK_PHASE` |
| 422 | The security guard (or the provider's moderation) refused the text: it looks like prompt injection or is over its length limit. `details` = `{reason}` (plus `field`, the request field, for `POST /api/interviews`) with `reason` one of `prompt_injection` (+ `excerpt`, the matched wording, so the candidate can find it in a long document), `too_long` (+ `maxLength`), `moderation`; the message never names the rule that matched. Applies to `POST /api/documents` (the extracted text, max 50,000 characters) and `POST /api/interviews` (the free-text fields). Nothing is persisted and no interview state changes, so the client keeps the user's input and lets them edit and resend | `INPUT_REJECTED` |
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
  "interviewType": "string",          // the client seeds it from difficulty / interviewerRole (last pick wins), then sends the final value
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

- `jobDescriptionId`/`cvId`/`coverLetterId` — always the id of an existing `Document`, never an inline
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

The interviewer opens the session: the call also creates the first interviewer `Message`
(a greeting and the first question, phase `qa`), so an Interview always has at least one
message. A failure at any step (analysis, plan, opening) returns the usual `502`/`503`/`504`
and creates nothing.

Response `201`: the created `Interview` (id, `status: "in_progress"`, `personaName`,
`personaTitle`, `personaImageUrl` as a servable URL (`/api/interviews/:id/persona-image`, or
`null` if the portrait couldn't be generated), `targetQuestionCount`, etc.) —
**not** the question plan or the evaluation criteria, which stay hidden from the candidate.

**Open concern, not yet resolved**: this call runs phases 1 (JD/CV analysis), 2
(question-plan/persona generation), and persona image generation sequentially before
responding — a multi-second synchronous request. Acceptable for a prototype behind a
loading state, but worth revisiting (e.g. a `202 Accepted` + polling pattern) if it proves
too slow in practice.

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
candidate `Message` and the next interviewer `Message` (with `helperText` when coaching
helpers are on and the message is a Q&A question; `null` otherwise, or if the hint call
failed), both generated and stored in the same call, the current `phase`
(`"qa"` | `"ask_back"`) and `status`. See
[ADR 0013](./adr/0013-live-conversation-is-server-paced-and-atomic-per-exchange.md) for how a
turn works: the server counts the interviewer's questions against `target_question_count`
and forces the wrap-up when the budget is spent; the interviewer message that ends the Q&A
phase is the first `ask_back` message (it invites the candidate's questions); the Interview
becomes `completed` when the interviewer closes the ask-back phase. A turn is
all-or-nothing: if the model fails, nothing is stored and the candidate can send the reply
again. `409 INTERVIEW_ALREADY_ENDED` if the Interview is no longer `in_progress`, and
`409 TURN_IN_PROGRESS` if the previous reply is still being answered (the client should wait
for it, not resend). Evaluation
and InterviewerReview are triggered when `status` becomes `"completed"` (not built yet).

### `GET /api/interviews/:id/ask-back-suggestions`

Phase 4 call. Ephemeral — returns candidate-question suggestions the client can offer, but
nothing is persisted until the candidate actually sends one via `POST .../messages`.

Response `200`: `{"suggestions": [string, ...]}` (five; the server trims extras). `409`
`HELPERS_DISABLED` if the Interview's interview-helpers toggle is off, `409`
`NOT_IN_ASK_BACK_PHASE` before the Q&A phase has ended, `409` `INTERVIEW_ALREADY_ENDED`
once the Interview is over; `502`/`503`/`504` when the provider fails (no suggestions is an
error, not an empty list). A `GET` because it has no side effects on the Interview.

### `POST /api/interviews/:id/abandon`

No body. The Interviewer-sidebar "Abandon interview" action. Marks `status: "abandoned"`,
`endedAt`, returns the Interview like `GET /api/interviews/:id` (`409 INTERVIEW_ALREADY_ENDED`
if it already ended), and triggers `Evaluation` (`incomplete: true`) + `InterviewerReview`, same as
the natural-completion path.

### `GET /api/interviews/:id/evaluation`

The `Evaluation` (Results page data): `verdict`, `reasoning`, `improvementSuggestions`,
`starBreakdown`, `incomplete`. `404` until the Interview has ended.

### `GET /api/interviews/:id/interviewer-review`

The `InterviewerReview` — dev-facing, not called by the candidate-facing Results page, but
available for the reflection/debugging use case. `404` until the Interview has ended.

## `documents` blueprint — `/api/documents`

### `GET /api/documents?type=cv|cover_letter|job_description`

List saved Documents (`saved = true` only), newest first — backs both the Create Interview
select-existing control and the Preferences Documents tab. Response `200`: an array of
`{id, type, name, sourceFilename, saved, createdAt}`. `raw_text` and `file_path` (database columns) are
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

No body. Runs phase 1 (JD/CV analysis, see `architecture.md`) on the Document and stores
the result as its `DocumentAnalysis`, using the default `jd_analysis` model. A `PUT`
because it is **idempotent**: if the Document already has an analysis from that model it
answers at once, without calling the LLM.

The client calls it **only right after an upload** in Create Interview, showing the
attachment with an "Analyzing document…" indicator and keeping the Start button disabled
meanwhile. Picking a saved Document, or an Application that pre-fills Documents, does not
call it: those Documents were analysed when they were uploaded, and if one has no analysis
(or the Interview overrides the `jd_analysis` model), `POST /api/interviews` analyses it at
submit. There is no cancel and no retry: the candidate stops the analysis by removing the
attachment, which abandons the request and deletes the Document. A failure is handled by
who is at fault: if the Document itself is rejected (`422 INPUT_REJECTED`), the client
deletes it and tells the candidate to use a different file; for any other failure (provider
unavailable, timeout, network), which is not the Document's fault, the client keeps the
Document and shows a notice, and the analysis runs again at submit. See
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

List, newest first: `id`, `companyName`, `jobTitle`, the optional documents
`jobDescription`/`cv`/`coverLetter` — each `{id, name}` or `null`, so Create Interview can
pre-fill a new stage and show an attached document by name even when it isn't `saved` — and
`interviews` — each stage's `id`, `interviewerRole` and `status`, oldest first (a stage
that went stale is closed as it is read, so it shows `abandoned`, per
[ADR 0006](./adr/0006-lazy-staleness-detection-not-a-background-job.md)). Backs the
sidebar's grouped history and the application select in Create Interview. Response `200`,
an empty array when there are none.

### `GET /api/applications/:id`

Application Overview page data: `companyName`, `jobTitle`, every stage (id,
`interviewerRole`, `status`, link to its Results), plus `progressScore`/
`progressSummary` once 2+ stages have an `Evaluation`.

### `PATCH /api/applications/:id`

`{"companyName": "string", "jobTitle": "string"}` — sidebar context-menu rename.

### `DELETE /api/applications/:id`

Cascades to every Interview under it and everything hanging off each (see
[ADR 0008](./adr/0008-jobapplication-delete-cascades-to-interviews.md)) — the client must
confirm before calling this; the API itself performs no confirmation step.

## `preferences` blueprint — `/api/preferences`

Singleton resource, no `:id`.

### `GET /api/preferences`

Current `interviewModel`, `judgeModel`, `temperature`, and per-phase system prompts.

### `PATCH /api/preferences`

Partial update of the same. Pydantic's `model_validator` enforces
[ADR 0009](./adr/0009-judge-model-excludes-the-interview-model.md) here — setting
`judgeModel` equal to `interviewModel` fails with `409 JUDGE_MODEL_COLLISION` before
anything is saved.

## Dashboard data

`GET /api/dashboard` — aggregate counts for the Home page (total interviews practiced,
hire/no-hire trend) rather than making the client crunch a full Interview list itself. Not
owned by any single blueprint above; exact placement (its own tiny blueprint vs. a loose
route) is an implementation detail, not a design decision.

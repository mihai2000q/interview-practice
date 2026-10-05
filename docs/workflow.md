# Workflow

The end-to-end flow through the app, from setting up a mock interview to seeing the
result. See [`overview.md`](./overview.md) for pages/layout, [`domain-model.md`](./domain-model.md)
for the fields referenced below, and [`architecture.md`](./architecture.md) for how each
step is implemented.

## 1. Create Interview

- **Standalone, or a stage of an existing pipeline** — the candidate can start a fully
  standalone Interview, or add the next stage to an existing `JobApplication` (e.g. "Acme
  Corp — Senior Software Engineer"). Picking an existing Application pre-fills
  `company_name`/`job_title`/documents below from it, so they don't need re-entering per
  stage; a brand-new Application can also be created inline by just filling those fields
  as normal.
- **Job title** — free text; phase 1 also infers the role's domain from it (and the JD/CV).
- **Company name** — free text, optional, independent of the job description upload below.
  Without it, the interviewer would have no company identity to reference whenever the JD
  is skipped — real interviews near-universally test whether the candidate researched the
  company ("what do you know about us", "why do you want to work here").
- **Seniority** — e.g. junior / mid / senior.
- **Difficulty** — easy / medium / hard. A preset that seeds `target_question_count`,
  `tone`, `interview_type`, `response_style`, `coaching_helpers_enabled` (on for easy only) and question complexity — each independently editable afterward, and `difficulty`
  itself is still passed to the question-plan prompt as its own signal, not discarded once
  other fields are tweaked.
- **Response style** — concise / detailed. Shapes the live interviewer's phrasing and the
  evaluation write-up's length/depth.
- **Interview type** — technical / behavioral. Skews the question plan and which half
  (technical or behavioral) of the evaluation rubric is weighted more heavily at
  evaluation time.
- **Interviewer role** — `recruiter` / `technical_screener` / `hr` / `hiring_manager`, shown
  as a radio group ordered to mirror the real-world pipeline sequence (one Interview only
  ever represents a single stage, not the whole pipeline). Picking a role re-applies a
  default `interview_type` and `tone` (even overwriting a prior manual edit on those two —
  see `domain-model.md`'s default-cascade table), both still independently editable again
  afterward. Also shapes the generated persona's knowledge scope/backstory and which
  ask-back questions make sense to suggest later.
- **Job description** — select a previously saved one, or upload a new PDF by
  clicking or dropping it on a dropzone (PDF only). The upload happens immediately when the
  file is picked (parsed server-side, so a bad PDF is reported right there). The uploaded
  file then replaces the select and dropzone with an attachment (with a remove button) and
  a "save for later" checkbox, checked by default for a CV or cover letter and unchecked for a
  job description (usually specific to one role); the form holds only the returned
  Document id. Right after an upload the Document is analysed (the attachment shows an
  "Analyzing document…" indicator, and Start stays disabled meanwhile); removing the
  attachment stops it and deletes the Document. If the Document itself is rejected it is
  deleted and the candidate is told to use a different file; if the failure is on our side
  (provider unavailable, timeout) it is kept and marked "Document not analyzed" with an
  "Analyze now" button (a tooltip explains that creating the interview may take longer
  without a cached analysis); otherwise it is analysed when the interview is created. A
  successful analysis shows "Document analyzed!". A Document picked from the saved list (or
  pre-filled by an Application) shows the same status, compared with the analysis model of
  this interview (the Advanced settings override, else the default): one with no analysis is
  marked "Document not analyzed", one analysed by another model "analyzed with a different
  model", and either can be analysed on the spot. Optional.
- **CV** and **cover letter** — two separate fields, each with the same
  select-existing-or-dropzone-upload pattern as job description. Both optional.
- **Interview helpers** toggle — boolean, default `false`. When on, each Q&A-phase question
  comes with a coaching-hint card grounded in the CV/cover letter where a real match
  exists, falling back to a generic hint when there's no document or no grounded match —
  the hint prompt must never fabricate experience the candidate didn't actually provide —
  and the ask-back phase offers suggested questions to ask the interviewer (see below).
- **Advanced settings** (collapsed, nice to have) — per-phase overrides for model
  (`gpt-5-mini`/`gpt-5-nano`/`gpt-4o-mini`/`typesafe/jev-1.13`), temperature, max tokens, and reasoning effort,
  for any of the 5 phases individually; anything left unset falls back to the global
  Preferences default.

Submitting runs the JD/CV analysis and question-plan/persona-generation phases (which also
produces the structured technical + behavioral evaluation rubric), generates and stores the
interviewer's persona portrait image, creates the Interview record, and redirects the
candidate into the session.

## 2. Interview Session — Q&A phase

The interviewer opens the session (greeting plus the first question) as part of creating the
Interview. The interviewer asks questions toward the difficulty-derived target count, but can end the
phase early once it judges it has enough signal. Each interviewer question is read aloud
via text-to-speech, so it genuinely feels asked rather than just displayed. If interview
helpers are enabled, each question also comes with its coaching-hint card. The candidate
can optionally reply by voice instead of typing (nice to have). A right-side interviewer
sidebar shows the persona's portrait/name alongside an **Abandon interview** action — the
candidate can quit at any point instead; the session is then marked abandoned rather than
completed.

## 3. Interview Session — ask-back phase

Always offered once the Q&A phase ends: the candidate can ask the interviewer their own
questions (with optional AI-suggested questions, tailored to the interviewer's role, that
they can accept, edit, or ignore — offered when the Interview helpers toggle is on), or
decline entirely. What they ask — or that they
decline — is itself a signal that feeds into the evaluation, the way it would in a real
interview.

## 4. Evaluation

Once the session ends (completed or abandoned), `gpt-5-mini` (the same model that ran the
interview) produces a STAR-based evaluation over the full transcript (both phases): a
verdict, reasoning, and improvement suggestions, graded against the rubric generated back
at creation. Separately, a dev-facing **Interviewer Performance Review** judges how well
the AI interviewer itself performed (question quality, persona consistency, pacing) using a
different, independent judge model.

## 5. Results

Shows the verdict, reasoning, improvement areas, the full transcript, and the interviewer's
persona image. Any past interview remains reachable from the history sidebar and re-opens
straight into its Results page.

# Overview

Interview Practice is a mock-interview web app. A candidate describes the role they're
preparing for, an AI interviewer conducts a multi-turn interview shaped by that role and
their documents, and the app produces a STAR-based evaluation with a hire / no-hire verdict
and concrete feedback — closer to rehearsing a real interview than to a one-shot Q&A
generator.

This document is a living index. It will grow as more of the app is designed (auth,
logging, testing, etc.); right now it covers what's been decided through the first design
pass. See [`workflow.md`](./workflow.md) for the end-to-end flow,
[`domain-model.md`](./domain-model.md) for the data model,
[`architecture.md`](./architecture.md) for the technical design,
[`database-schema.md`](./database-schema.md) for the concrete schema,
[`api-design.md`](./api-design.md) for the REST contract between client and server,
[`deployment.md`](./deployment.md) for how it's containerized and run,
[`spec.md`](./spec.md) for the whole design as user stories, ready to slice into your own
issues/tickets, the repo-root [`CONTEXT.md`](../CONTEXT.md) for canonical vocabulary, and
[`adr/`](./adr/) for
the reasoning behind decisions that were hard to reverse or would otherwise look
surprising.

## Pages

| Route | Purpose |
|---|---|
| `/` | Home. Lightweight dashboard: total interviews practiced, hire/no-hire trend, quick "+ New Interview" CTA; falls back to an onboarding empty state before any history exists. |
| `/applications/:id` | Application Overview. All stages of a `JobApplication` (status + link to each Interview's Results) plus its cross-stage progress summary once 2+ stages have an Evaluation. |
| `/interviews/new` | Create Interview. Candidate sets up a session: role, documents, difficulty/tone. |
| `/interviews/:id` | Interview Session. The live, multi-turn chat with the AI interviewer (a persistent Q&A/Ask-Back phase label above the transcript), alongside a right-side interviewer sidebar (persona portrait/name/title, tone badge, company name if set, question progress, Abandon action). |
| `/interviews/:id/results` | Results. The STAR evaluation and verdict for a finished (or abandoned) interview, the transcript, and — in a separate, dev-facing section — the Interviewer Review of the AI interviewer. |
| `/preferences` | Preferences. Tabbed: Model & Prompts (model/temperature/system-prompt tuning) and Documents (manage all saved CVs/cover letters/JDs). Reached via the sidebar, deliberately kept separate from the candidate-facing flow. |

## Workflow

The full end-to-end flow (Create Interview → Q&A phase → ask-back phase → Evaluation →
Results) now lives in its own document: see [`workflow.md`](./workflow.md).

## The 5 required system prompts

The assignment requires at least 5 system prompts using different prompting techniques.
Rather than building 5 disconnected standalone tools, each prompt corresponds to one
functional phase of the single interview lifecycle above, each using a genuinely distinct
technique. Full detail is in
[`architecture.md`](./architecture.md#the-5-system-prompts--phases):

1. JD/CV analysis — zero-shot
2. Question-plan & persona generation — instruction/constraint-based prompting
3. Live interviewer conversation — role/persona prompting
4. Candidate ask-back suggestions — few-shot
5. STAR evaluation — chain-of-thought

There's also a 6th, dev-facing prompt beyond these required 5: the **Interviewer
Performance Review**, which judges the AI interviewer's own conduct rather than the
candidate (see `architecture.md`) — this is what satisfies the assignment's optional
"LLM-as-a-judge" task. Combined with the full multi-turn chatbot, this already clears the
bonus-task bar (2 medium + 1 hard) without needing LangChain — see
[ADR 0005](./adr/0005-langchain-not-used.md).

## Known limitations

- **Prototype scope, no authentication.** No login, no per-user isolation, no access
  control — see [ADR 0002](./adr/0002-single-user-prototype-no-auth.md).
- **Job description context is not RAG** — plain-text injection, no vector database or
  embeddings — see [ADR 0004](./adr/0004-job-description-context-is-not-rag.md). Worth
  keeping in mind if claiming that assignment optional task for bonus points.
- **Abandoned uploads are never cleaned up.** A Document is uploaded when the candidate
  picks the file. Removing it in the form deletes it, but abandoning Create Interview
  (closing the tab, navigating away) leaves an unreferenced Document
  (row, extracted text, file on disk) that nothing deletes — see
  [ADR 0011](./adr/0011-documents-are-uploaded-before-the-interview-is-created.md). A
  production deployment would need a scheduled cleanup job for this (and, with object
  storage instead of local disk, a bucket lifecycle rule such as S3's for the file side).

## Open items (not yet designed)

- Exact grouped-history visual treatment for `JobApplication`s (collapsible groups vs. a
  simple label prefix).
- Exact visual layout of the interviewer sidebar's now-finalized content list (portrait,
  name/title, tone badge, company name, question progress, Abandon), and of the main-page
  phase indicator label.
- **Nice to have: per-prompt cost tracking** (export-only, see `architecture.md`) —
  design-resolved, not built yet. (The interviewer's voice and dictated replies are built;
  see `architecture.md`.)
- Exact wording/trigger sensitivity of the JobApplication progress summary's narrative
  (e.g. how much data before it says "doing great as usual" vs staying neutral) — see
  `architecture.md`'s Progress summary section.
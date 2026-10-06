# Spec: Interview Practice v1

Synthesizes the full accumulated design from the documentation pass (see
[`overview.md`](./overview.md), [`workflow.md`](./workflow.md),
[`domain-model.md`](./domain-model.md), [`architecture.md`](./architecture.md),
[`database-schema.md`](./database-schema.md), [`api-design.md`](./api-design.md),
[`deployment.md`](./deployment.md), the repo-root [`CONTEXT.md`](../CONTEXT.md), and
[`adr/`](./adr/)) into one spec, for turning into your own issues/tickets. It introduces
no new decisions beyond what's already recorded in those documents — this is a synthesis,
not a new design pass.

## Problem Statement

Candidates preparing for a real job interview have no realistic way to rehearse against a
role- and stage-specific interviewer (a first-contact recruiter screen, a harder technical
screen, an HR culture-fit conversation, a final hiring-manager round) and get honest,
structured feedback on how they actually performed — most practice tools are generic
one-shot question generators, not something that feels like being interviewed.

## Solution

A mock-interview web app (Flask + Angular) where a candidate sets up a practice session
(role, company, difficulty, which stage/interviewer they're facing), has a live multi-turn
conversation with an AI interviewer persona shaped by that context and their own CV/job
description, then receives a STAR-based evaluation with a hire/no-hire verdict and concrete
improvement suggestions. Supporting features: reusable document management, multi-stage
pipeline tracking (grouping several interviews under one real job application, with a
cross-stage progress summary), a separate review of the AI interviewer's own conduct, and a
developer-facing preferences area kept apart from the candidate experience.

## User Stories

1. As a candidate, I want to create a new mock interview by specifying job title,
   seniority, and difficulty, so that the interview questions match the role I'm preparing
   for.
2. As a candidate, I want the role's domain to be inferred from my job title and documents,
   so that I don't have to categorize my own role.
3. As a candidate, I want to choose an interview type (technical or behavioral), so that I
   can focus my practice on the area I need most.
4. As a candidate, I want to choose who is interviewing me (recruiter, technical screener,
   HR, or hiring manager), so that I can practice for the specific stage of a real hiring
   pipeline I'm facing next.
5. As a candidate, I want the interviewer role I pick to seed the interview's tone and
   interview type by default, so that I get a realistic default without configuring
   everything manually, while still being able to override those defaults afterward.
6. As a candidate, I want to optionally provide a company name, so that the interviewer can
   ask me company-specific questions even if I don't upload a full job description.
7. As a candidate, I want to upload or select a previously-saved job description, so that
   the interview questions are grounded in the actual role I'm applying for.
8. As a candidate, I want to upload or select a previously-saved CV and, separately, a cover letter, so that
   the interviewer and coaching hints can reference my real experience.
9. As a candidate, I want to be asked whether to save an uploaded document for future
   reuse, so that I don't have to re-upload the same CV every time.
10. As a candidate, I want to download any of my saved documents back, so that I can
    retrieve exactly what I uploaded, not a reformatted reconstruction.
11. As a candidate, I want to choose a response style (concise or detailed), so that the
    interviewer's phrasing and my evaluation write-up match how much detail I want.
12. As a candidate, I want to optionally enable coaching helpers, so that I get hint cards
    grounded in my own CV/cover letter during the interview.
13. As a candidate, I want coaching hints to never fabricate experience I didn't actually
    provide, so that I'm not misled about my own background.
14. As a candidate, I want advanced settings to let me override the model/temperature/etc.
    per phase (including the interviewer-judge phase), so that I can experiment without
    touching global preferences.
15. As a candidate, I want the interviewer-judge model to never be the same model that
    conducted my interview, so that the app's own self-assessment isn't quietly biased,
    whether I configure this globally or per interview.
16. As a candidate, I want to be asked questions by an AI interviewer in a live, multi-turn
    conversation, so that the practice feels like a real interview rather than a one-shot
    Q&A form.
17. As a candidate, I want the interviewer to ask a number of questions appropriate to my
    chosen difficulty, so that easy sessions are shorter and harder ones more thorough.
18. As a candidate, I want the interviewer to be able to end the questioning phase early
    once it has enough signal, so that the interview doesn't feel artificially padded.
19. As a candidate, I want to hear the interviewer's questions read aloud, so that the
    experience feels like being spoken to rather than just reading text.
20. As a candidate, I want to see a live indicator of which phase (Q&A or ask-back) I'm in,
    so that I always know where I am in the flow.
21. As a candidate, I want to see my progress through the question count, so that I can
    gauge how much of the interview remains.
22. As a candidate, I want to see who I'm talking to (portrait, name, job title, tone) in a
    dedicated panel, so that the interviewer feels like a real, particular person.
23. As a candidate, I want to be able to abandon an interview at any point, so that I'm not
    forced to finish a session I no longer want to continue.
24. As a candidate, I want an abandoned interview to still produce an evaluation (flagged
    as based on a partial transcript), so that I get feedback even from a session I didn't
    finish.
25. As a candidate, I want a chance to ask the interviewer my own questions at the end of
    the interview, so that I can practice that part of a real interview too.
26. As a candidate, I want the app to suggest questions I could ask back, tailored to the
    interviewer's role and the company, so that I have good material even if I can't think
    of anything myself.
27. As a candidate, I want to be able to decline asking anything back, so that I'm not
    forced through a step I don't want.
28. As a candidate, I want my evaluation to consider not just my answers but also what (or
    whether) I asked back, so that the feedback reflects a full real-interview assessment.
29. As a candidate, I want a structured evaluation (verdict, reasoning, improvement
    suggestions, STAR breakdown) after my interview, so that I know concretely how I did
    and what to work on.
30. As a candidate, I want the evaluation to assess self-awareness/coachability (not just
    whether my STAR story is technically complete), so that the feedback matches how a
    real interviewer would judge me.
31. As a candidate, I want to revisit any past interview's results from a history list, so
    that I can track how I've done over time.
32. As a candidate, I want interviews for the same real job application (e.g. multiple
    stages at the same company) to be grouped together, so that I don't have to re-enter
    the company/role/documents for each stage.
33. As a candidate, I want to see an aggregate score and narrative comparing my performance
    across a job application's stages, so that I understand whether I'm improving, staying
    consistent, or regressing.
34. As a candidate, I want to rename or delete a job application (with its interviews)
    directly from the history sidebar, so that I can keep my history tidy without hunting
    for a separate management screen.
35. As a candidate, I want to start a brand-new interview or add a stage to an existing
    application from the sidebar, so that starting practice is always one click away.
36. As the developer, I want a separate review of the AI interviewer's own conduct
    (question quality, persona consistency, pacing), so that I can assess and demonstrate
    the quality of my own prompt engineering independent of any one candidate's
    performance.
37. As the developer, I want model, temperature, and system-prompt settings centralized in
    a Preferences area, so that I can tune the app's behavior without touching
    candidate-facing screens.
38. As the developer, I want document management (view/rename/delete/download) centralized
    in Preferences too, so that it doesn't clutter the focused Create Interview flow.
39. As the developer, I want every outbound prompt to pass through a single centralized
    security guard, so that prompt-injection and abuse are checked in one place rather
    than scattered per-endpoint.
40. As the developer, I want a leave-confirmation guard on Create Interview and Interview
    Session, so that a candidate doesn't lose in-progress work/state by navigating away
    accidentally.
41. As the developer, I want an ungracefully-closed interview (crash, Alt+F4) to eventually
    be marked abandoned automatically, so that no interview is stuck "in progress" forever
    without needing a background job.
42. As the developer, I want the whole API surface validated by a single schema-validation
    layer (Pydantic server-side, Zod client-side), so that malformed requests are rejected
    consistently at the boundary rather than deep in business logic.
43. As the developer, I want the app containerized via Docker Compose, so that it can be
    spun up consistently without manual environment setup.
44. As the developer, I want uploaded files and generated persona portraits to persist
    across container restarts, so that a redeploy doesn't silently delete candidate data.
45. As the developer, I want the OpenRouter API key sourced only from each developer's own
    machine, never written into any file in the repo, so that it's never accidentally
    committed or shared.
46. As the developer, I want a Docker-based mock LLM option, so that I can exercise the
    app's own request/response plumbing locally without real API cost.

## Implementation Decisions

- **Stack**: Flask (application factory `create_app()`, Blueprints per domain area —
  `interviews`, `documents`, `applications`, `preferences`) + Angular 22 (standalone
  components, zoneless) — see [ADR 0001](./adr/0001-flask-and-angular-over-streamlit-or-nextjs.md)
  for why not Streamlit/Next.js. UI components via Spartan + Tailwind
  ([ADR 0010](./adr/0010-spartan-for-ui-components.md)).
- **Validation**: Pydantic v2 server-side (request bodies, and the cross-field
  judge-model-exclusion invariant via `model_validator`), Zod client-side.
- **Persistence**: Postgres via SQLAlchemy; Flask-Migrate for schema migrations.
- **Entities** (full field lists in `domain-model.md`/`database-schema.md`): `Document`
  (type, raw_text, source_filename, file_path, `saved` flag — a row always exists
  regardless of the save choice, since an Interview's FK needs something to point at),
  `JobApplication` (company_name, job_title, document links, `progress_score` 1-5 +
  `progress_summary` narrative, cascade-deletes its Interviews per
  [ADR 0008](./adr/0008-jobapplication-delete-cascades-to-interviews.md)), `Interview`
  (job_title, company_name, inferred domain, seniority, difficulty→tone/question-count cascade,
  interview_type, interviewer_role→tone/interview_type cascade across the 4 roles,
  target_question_count, status, `last_activity_at` + 30-minute staleness detection per
  [ADR 0006](./adr/0006-lazy-staleness-detection-not-a-background-job.md), persona_name,
  persona_title, persona_image_path, coaching_helpers_enabled (default false),
  response_style (default concise), `InterviewQuestion` rows (the question plan) and
  `EvaluationCriterion` rows (technical/behavioral rubric), `DocumentAnalysis` per Document
  (cached phase-1 output, keyed by model),
  `InterviewPhaseSettings` rows across 6 phases including the judge phase's narrower model
  set), `Message` (phase, role, content, helper_text, sequence), `Evaluation` (verdict,
  reasoning, improvement_suggestions, star_situation/task/action/result +
  star_completeness, incomplete, model_used — always
  `gpt-5-mini`, see [ADR 0003](./adr/0003-self-grading-evaluation-vs-decoupled-interviewer-review.md)),
  `InterviewerReview` (judge_model default `google/gemini-2.5-flash`, score_question_relevance /
  score_persona_consistency / score_pacing 1-5, reasoning, automatic trigger at
  session end).
- **The 5 required LLM phases**: zero-shot JD/CV analysis (plain-text context, not RAG —
  [ADR 0004](./adr/0004-job-description-context-is-not-rag.md)); instruction/
  constraint-based question-plan + persona + rubric generation; role/persona live
  conversation; few-shot ask-back suggestions; chain-of-thought STAR evaluation. Plus a
  6th, dev-facing Interviewer Performance Review phase (separate judge model, with
  [ADR 0009](./adr/0009-judge-model-excludes-the-interview-model.md)'s collision-exclusion
  enforced in both Preferences and per-interview overrides), and the JobApplication
  Progress Summary feature (regenerated once 2+ stages have an Evaluation, from prior
  Evaluations' reasoning/improvement_suggestions/STAR fields/evaluation criteria, not
  raw transcripts).
- **Security guard**: one centralized Flask service all outbound prompts pass through
  (length limits, prompt-injection detection, off-topic/abuse detection).
- **UI layout**: topbar (app logo, page breadcrumb trail and light/dark toggle, unconditional),
  left history sidebar ("+ New Interview" CTA, Preferences link, history grouped by
  JobApplication with a hover-reveal-icon-or-right-click context menu), right interviewer
  sidebar (Interview Session only: portrait, name + title, tone badge, company name if set,
  question progress, Abandon action), a phase indicator pinned above the transcript (not in
  either sidebar).
- **API contract**: the 4 blueprints' endpoints exactly as specified in `api-design.md`
  (create/get/message/abandon/evaluation/interviewer-review for interviews;
  list/upload/download/rename/delete for documents; list/get/rename/delete for
  applications; get/patch singleton for preferences) + the uniform error contract
  (400/404/409/500, one JSON error shape).
- **File storage**: local disk under the Flask app's `instance/` folder, backed by a
  persisted Docker volume in deployment (see `deployment.md`).
- **Deployment**: Docker Compose (`client`/`server`/`db`, plus opt-in `mock-llm` behind a
  profile), project name pinned to `interview-practice`, nginx reverse-proxying `/api/*`
  same-origin in the client container (no CORS in that path), CORS only relevant for local
  dev via `CLIENT_HOST`/`CLIENT_PORT`, discrete `POSTGRES_*` env vars assembled into the DB URI at
  runtime, `.env.dev` as a checked-in template copied to a real git-ignored `.env`,
  `OPENROUTER_API_KEY` sourced only from the host shell environment, never a file.
- **Known limitations accepted**: no auth
  ([ADR 0002](./adr/0002-single-user-prototype-no-auth.md)), no logging strategy yet
  (deferred, not hidden).

## Testing Decisions

No automated test suite for this pass — explicitly out of scope, given the time budget of
a bootcamp project. If/when this changes, the natural seam is the Flask API layer itself
(test through HTTP via the contract in `api-design.md`, not internal functions), with a
thin OpenRouter client adapter as the one necessary fake boundary (the one real external
dependency). Manual/local exercising of the real API is supported today via the opt-in
`mock-llm` Docker Compose service (see `deployment.md`), which stands in for OpenRouter
with canned responses at zero cost — useful for checking the app's own plumbing, not for
judging output quality.

## Out of Scope

- Authentication/multi-user support ([ADR 0002](./adr/0002-single-user-prototype-no-auth.md)).
- LangChain ([ADR 0005](./adr/0005-langchain-not-used.md)).
- Real RAG/vector database for JD/CV context ([ADR 0004](./adr/0004-job-description-context-is-not-rag.md)).
- Automated testing, logging/observability, CI/CD, cloud hosting choice, horizontal
  scaling.
- TTS voice/rate tuning and a per-message replay button — designed (see `architecture.md`)
  but not built this pass.
- Per-prompt cost tracking UI — designed (export-only) but not built this pass.
- Exact visual/pixel design (icon choices, grouped-history collapse treatment, interviewer
  sidebar's finer layout) — left for whenever those screens actually get built.

## Further Notes

- This is a synthesis of a long documentation-only session, not a new design pass — if
  something here seems to contradict `docs/adr/`, the ADR is the source of truth, not this
  file.
- The candidate-facing STAR evaluation's model (`gpt-5-mini`) is deliberately **not**
  decoupled from the interview model — self-grading is an accepted tradeoff
  ([ADR 0003](./adr/0003-self-grading-evaluation-vs-decoupled-interviewer-review.md)).
  Don't "fix" this to look like the Interviewer Performance Review's decoupling; they're
  different by design.
- Given the size, this is meant to be sliced into your own issues/tickets rather than
  worked as one pass — this doc doesn't do that slicing itself.

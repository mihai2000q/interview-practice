# Interview Practice

A mock-interview practice app: a candidate sets up and runs a simulated interview session
against an AI interviewer, then receives a structured evaluation. This is the project's
canonical vocabulary, kept free of implementation detail — see `docs/domain-model.md` for
fields, types, and relationships.

## Language

### Core entities

**JobApplication**:
The real-world hiring pipeline for one company and role, grouping multiple Interviews as
its stages.
_Avoid_: application (bare) in prose and identifiers, job, pipeline

The short form "application" is fine where brevity is the convention: URLs (`/api/applications`,
`/applications/:id`) and user-facing copy (the "Application" section in Create Interview). Code
and docs that name the entity itself use **JobApplication**.

**ApplicationSummary**:
The trimmed view of a JobApplication returned by `GET /api/applications`: its id, company and
job title, its attached documents (id and name) and its stages. Not the entity itself, which
also holds the progress score and narrative.
_Avoid_: application summary as a name for the JobApplication itself

**Interview**:
One mock interview session representing a single stage of a hiring pipeline, optionally
part of a JobApplication.
_Avoid_: session, chat, conversation

**Document**:
A reusable CV, cover letter, or job description the candidate has uploaded, optionally
saved for reuse across Interviews.
_Avoid_: file, upload, resume

**Message**:
One turn in an Interview's transcript, tagged by phase and role.
_Avoid_: turn, chat message

**Evaluation**:
The STAR-based assessment of the candidate's performance in an Interview: a verdict,
reasoning, and improvement suggestions.
_Avoid_: result, review (see InterviewerReview — a different concept)

**InterviewerReview**:
A separate, dev-facing assessment of how well the AI interviewer itself performed in an
Interview. Never shown to the candidate.
_Avoid_: review (bare), judge report

### Interviewer & persona

**Persona**:
The generated interviewer character (name, title, tone, backstory/knowledge scope) that
conducts an Interview's live conversation.
_Avoid_: character, avatar

**Tone**:
The persona's conversational style — e.g. strict, neutral, friendly.
_Avoid_: mood, attitude

**Interviewer role**:
Who conducts a given Interview — recruiter, technical screener, HR, or hiring manager —
shaping the persona's actual knowledge scope, not just its tone.
_Avoid_: interviewer type, persona type

**Recruiter** _(interviewer role)_:
First-contact screen; shallow technical/company knowledge; broad background, motivation,
and logistics/compensation questions.

**Technical screener** _(interviewer role)_:
The first, harder technical interview stage; real technical depth, typically the most
rigorous/critical of the four roles.
_Avoid_: techie, technical interviewer

**HR** _(interviewer role)_:
Culture/values/soft-skills fit; more procedural in tone than the other roles.

**Hiring manager** _(interviewer role)_:
The final, most-familiar pipeline stage; real technical depth plus organizational context.
_Avoid_: team lead

### Interview structure

**Difficulty**:
A preset (easy/medium/hard) that seeds an Interview's question count, tone, and question
complexity — each independently editable afterward.
_Avoid_: level

**Interview type**:
Technical or behavioral — skews the question plan and which half of the evaluation
criteria is weighted more heavily.
_Avoid_: category

**Response style**:
Concise or detailed — shapes the interviewer's phrasing and the evaluation write-up's
length.
_Avoid_: verbosity

**Q&A phase**:
The part of an Interview where the interviewer asks questions toward a target count.
_Avoid_: question phase, main phase

**Ask-back phase**:
The part of an Interview, after the Q&A phase, where the candidate may ask the interviewer
their own questions.
_Avoid_: closing phase, candidate-questions phase

**Coaching helper**:
An optional hint card shown alongside a Q&A-phase question, grounded in the candidate's
CV/cover letter where possible.
_Avoid_: tip, suggestion (see Ask-back suggestion — a different concept)

**Ask-back suggestion**:
An AI-generated candidate question offered during the ask-back phase, which the candidate
may accept, edit, or ignore.
_Avoid_: hint, tip

### Evaluation & judging

**Verdict**:
An Evaluation's headline outcome — hire or no_hire.
_Avoid_: decision, result

**Evaluation criteria**:
The technical + behavioral rubric generated with the question plan, one criterion per
row, used to ground an Evaluation. Never shown to the candidate.
_Avoid_: rubric, interviewer guidelines

**Interview question**:
One entry of an Interview's question plan: something the interviewer intends to ask,
tagged technical or behavioral. Never shown to the candidate.
_Avoid_: planned question, topic

**Document analysis**:
What phase 1 extracted from one Document (domain, employer, skills, likely topics), kept
with the Document and reused across Interviews until a different model is chosen.
_Avoid_: JD analysis (it covers CVs and cover letters too)

**Interview model**:
The model used for the candidate-facing pipeline, from JD/CV analysis through Evaluation.
Default `gpt-5-mini`.
_Avoid_: main model, primary model

**Progress summary**:
A JobApplication-level assessment comparing the candidate's Evaluations across its
Interview stages: a 1-5 aggregate score plus its accompanying narrative, always generated
and regenerated together.
_Avoid_: trend report

**Judge model**:
The model used to produce an InterviewerReview. Default `google/gemini-2.5-flash`;
enforced to never be the same model that conducted the Interview being reviewed — not
just independent by default, independent by construction.
_Avoid_: evaluator model, grading model

### Settings & infrastructure

**Preferences**:
The app-wide, tabbed page for everything kept separate from the candidate-facing flow:
per-phase model/temperature/max-tokens/reasoning-effort defaults, and all Document management
(view/rename/delete/download).
_Avoid_: settings (bare), config

**Advanced settings**:
Per-phase overrides (model/temperature/max tokens/reasoning effort) set on Create
Interview, layered under the global Preferences defaults.
_Avoid_: overrides (bare)

**Security guard**:
The centralized Flask service every outbound prompt passes through before reaching
OpenRouter.
_Avoid_: guardrail, filter

**Stale Interview**:
An Interview whose `last_activity_at` has exceeded the timeout without a graceful end,
lazily marked abandoned the next time it's read.
_Avoid_: expired, timed-out

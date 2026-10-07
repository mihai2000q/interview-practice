# Judge model can't collide with the model it's judging

`InterviewerReview.judge_model` must differ from whichever model actually produced
phase 2 (question-plan/persona generation) and phase 3 (live interviewer conversation) for
that Interview — the two phases whose output constitutes "the interviewer" being judged.
Without this, the narrower per-interview judge choices
(`google/gemini-2.5-flash`/`gpt-5-mini`/`gpt-5-nano`) overlap with the Interview model
choices (`gpt-5-mini`/`gpt-5-nano`/`gpt-4o-mini`), so a candidate could otherwise pick the same
model for both roles and quietly defeat the whole reason `InterviewerReview` is decoupled
from `gpt-5-mini` in the first place (see [ADR 0003](./0003-self-grading-evaluation-vs-decoupled-interviewer-review.md)).
Enforced by excluding the colliding model from the judge-model picker everywhere it
appears (Preferences, per-interview advanced settings), with a backend validation check as
a safety net for anything that bypasses the UI (`app/llm/phase_settings.py`, raising
`409 JUDGE_MODEL_COLLISION`). The check resolves each phase's model the same way the
phases themselves do, so overrides and defaults can't disagree. The same rule
is enforced on the global Preferences defaults (`PATCH /api/preferences`), checked on the
defaults as they will be after the update, and `POST /api/interviews` checks the Interview's
overrides layered over them.

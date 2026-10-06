# The progress summary is generated on demand, from the Evaluations that exist

An Application's `progress_score` and `progress_summary` are made by
`PUT /api/applications/:id/progress`, which the Application Overview page calls when the
summary is missing or out of date, not by whatever ends an Interview. The first design
regenerated it "whenever an Interview completes", which stopped being possible when
[ADR 0014](./0014-results-are-generated-on-demand-by-an-idempotent-put.md) moved the
Evaluation to the Results page: an Interview that has just ended has no Evaluation yet, and
may never get one unless someone opens its Results.

The endpoint is idempotent. Each stored summary records what it was built from
(`progress_basis`, a fingerprint of the sorted ids of the Evaluations it compared). If the
Application's Evaluations still match it, the stored pair is returned and no model is
called; if they differ (a stage was graded, or deleted), the pair is regenerated and
replaced together. Two calls at once may both run the model; the first to store wins, as with
the Evaluation. A failure leaves the previous pair in place, so the page keeps showing it
and offers a retry.

**The server only reads Evaluations that exist; the client grades the missing ones.** A
stage that has ended but has no Evaluation yet is graded by the Overview page calling the
existing `PUT /api/interviews/:id/evaluation` for each one, in parallel, before it calls the
progress `PUT`. This is how "the summary must ask for any missing Evaluation" (ADR 0014)
is met without the applications domain importing the interviews use case, which the
vertical-slice rule forbids. A stage with nothing to grade (`409 NOTHING_TO_EVALUATE`) is
skipped. A stage still `in_progress` is never graded. The cost is that a first visit to an
Overview whose stages were never opened waits for those Evaluations (one model call each,
concurrently), so the page shows what it is doing.

The call runs on the `evaluation` phase's model and settings from Preferences (an
Application has no per-phase overrides, and a seventh phase would add a Preferences row,
a model list and a migration for no new control). It is self-grading in the same sense as
ADR 0003.

The score is the overall level across the stages graded so far, 1-5; the narrative carries
the trend (improving, steady, slipping). Stages differ in role, difficulty and type, so the
inputs name them and the prompt says a harder stage is not a worse one.

Consequence: nothing is generated below two Evaluations, and the endpoint answers
`409 NOT_ENOUGH_STAGES` then. Deleting a stage of an Application makes the stored summary
outdated while two or more Evaluations remain, and the next visit repairs it. The client
only ever deletes an Application whole, so the case of a single stage deleted through the
API that leaves fewer than two is left alone: its summary stays until a new Evaluation
replaces it.

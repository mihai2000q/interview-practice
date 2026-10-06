# Results are generated on demand by an idempotent PUT, not when the Interview ends

The Evaluation and the InterviewerReview are made by `PUT /api/interviews/:id/evaluation`,
which the Results page calls once the Interview has ended, not by the call that ends it.
The first design ran them "when `status` becomes `completed`/`abandoned`", which would put a
reasoning-model call, and its failure modes, inside the last `POST .../messages` and inside
`POST .../abandon`: the candidate's closing reply would wait for the grading, and a provider
error would have to fail (or silently skip) an interview that had already ended well. Same
reasoning as the opening and the coaching helper (ADR 0013): the slow call gets its own
idempotent endpoint, so the page that needs it asks for it, and a failure is just retried.

Both results come from one call and are made **in parallel** (`app.llm.concurrency.fan_out`),
so the candidate waits for the slower of the two rather than their sum. The prompts are built
on the request thread; the workers only call the model. The judge is a dev-facing extra, so
its failure is logged and leaves no review while the Evaluation is stored and returned; once
the Evaluation exists the review is not retried, so reloading Results never waits on it.
Two calls at once may both run the models; the rows have a unique `interview_id` and the
first to store wins (`INSERT ... ON CONFLICT DO NOTHING`), as with the helper.

`GET .../evaluation` and `GET .../interviewer-review` only read, and are `404` until the
`PUT` has made them. An Interview in which the candidate never wrote has nothing to grade
(`409 NOTHING_TO_EVALUATE`). The transcript cannot change once an Interview has ended
(exchanges re-check under a lock), so the result of a `PUT` is final.

Consequence: an Interview that nobody opens the Results page for is never evaluated, and the
application's progress summary (which needs 2+ Evaluations) must ask for any missing one
instead of assuming it exists.

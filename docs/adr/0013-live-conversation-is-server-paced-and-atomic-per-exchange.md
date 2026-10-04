# The live conversation is server-paced and atomic per exchange

An **exchange** is the candidate's reply and the interviewer's answer to it; the opening
exchange has no reply. (A Message is one entry of the transcript, so an exchange adds one or
two Messages.) Phase 3 makes one LLM call per exchange, and the model never decides on its
own how the interview is structured. For each call the server works out what kind of
exchange it is and tells the model: `open` (greet and ask the first question), `ask` (next
question, with the option to end the questions early), `close_questions` (budget spent: thank
the candidate and invite their questions), `answer` (ask-back) and `close_interview`. Every
interviewer message in the Q&A phase counts as one question toward `target_question_count`,
follow-ups included; the plan has exactly that many questions and is a guide, not a script.
When the budget is spent the server forces the wrap-up, and if the model's reply breaks the
exchange's contract (it asks another question when it had to close, or the reverse) the
request fails with `502` instead of being patched up. The model replies `{message, done}`;
`done` means the current phase is over after this message, so the interviewer message that
ends the Q&A phase is stored as the first `ask_back` message.

One module, `app/interviews/shared/exchange/`, owns all of this: the pacing rules (pure, no
model and no database), the prompt and reply contract, the coaching hint and its gating
(a hint goes with each Q&A question, never with the wrap-up or in ask-back), and the final
step of adding the Messages to the Interview. `create_interview` (the opening) and
`send_message` (every later reply) both go through it and keep only what concerns their
request: loading, the claim, the lock and the commit.

The ask-back phase ends when the interviewer closes it (`done`, which the model sets when the
candidate declines or has no more questions) or after 5 candidate questions, whichever comes
first. The Interview then becomes `completed` and `ended_at` is set. There is no separate
"finish" action: the candidate declining is a message like any other, and it is itself a
signal for the evaluation, as the workflow describes.

The interviewer's opening message is generated at the end of `POST /api/interviews`, not on
first read: an Interview then always has at least one message, `GET` never has side effects,
and a failed opening fails the whole create. The cost is one more sequential LLM call in an
already slow request (the open concern in `api-design.md`).

An exchange is all-or-nothing, and running it is separate from applying it. The model is
asked first, using the stored transcript plus the new reply, and that step changes nothing;
only if it succeeds, and the caller has re-checked the Interview, are the candidate message
and the interviewer message added and committed in one go. A failed or dropped exchange
leaves nothing behind and the candidate simply sends the reply again.

Exchanges of one Interview never overlap, and no database lock is held while the model
works. An exchange first claims the Interview with one conditional `UPDATE` that sets
`interviews.turn_started_at`; a reply that arrives while an exchange is in progress is
refused at once with `409 TURN_IN_PROGRESS`, instead of queueing behind it holding a
connection (and then running as a second, unintended exchange). The marker is cleared when
the exchange commits or fails, and expires by itself after 5 minutes (`lifecycle.TURN_TTL`:
two LLM calls at 60s, with margin), so a crashed worker can't wedge an Interview. An
Interview with an exchange in progress is never expired as stale. Just before storing, the
exchange re-reads the row under a short lock and drops its result with
`409 INTERVIEW_ALREADY_ENDED` if the Interview was abandoned in the meantime. The earlier
design, a row lock held for the whole exchange, was replaced because it pinned a pooled
connection for up to two minutes per in-flight reply.

The candidate's text is guarded (`422 INPUT_REJECTED`, field `content`) before it reaches the
model, sent as chat history (not inlined into the system prompt), and the system prompt says
that it is an answer to the interviewer, never an instruction. The evaluation criteria are
withheld from this phase on purpose.

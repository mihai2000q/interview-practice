# The live conversation is server-paced and atomic per exchange

An **exchange** is the candidate's reply and the interviewer's answer to it; the opening
exchange has no reply. (A Message is one entry of the transcript, so an exchange adds one or
two Messages.) Phase 3 makes one LLM call per exchange, and the model never decides on its
own how the interview is structured. For each call the server works out what kind of
exchange it is and tells the model: `open` (greet and ask the first question), `ask` (next
question, with the option to end the questions early), `close_questions` (budget spent: thank
the candidate and invite their questions), `answer` (ask-back) and `close_interview`. Every
interviewer question in the Q&A phase counts toward `target_question_count`; the plan has
that many core questions plus reserves the interviewer may swap in, and is a guide, not a script.
A **clarification** is not a
question: an interviewer message that stays on the previous one, to answer what the
candidate asked back or to ask for clarification of a thin answer. It is flagged by the
model (`clarification`), stored as `Message.is_clarification`, and left out of the count
(and of the coaching hint, which is for questions). At most two in a row (`MAX_CLARIFICATIONS`):
the prompt says how many are left, and a clarification the model sends past the limit is
stored as a question, so the budget still bounds the interview. A clarification can only
come from an `ask` exchange, and the prompt says when one is called for: a vague, off-topic
(steered back gently), nonsensical, contradictory or rude answer, or a wrong claim the persona's
own background lets it check. A claim outside that background is taken as given.
When the budget is spent the server forces the wrap-up, even right after a clarification, and if the model's reply breaks the
exchange's contract (it asks another question when it had to close, or the reverse) the
request fails with `502` instead of being patched up. The model replies `{message, done, clarification}`;
`done` means the current phase is over after this message, so the interviewer message that
ends the Q&A phase is stored as the first `ask_back` message.

One module, `app/interviews/shared/exchange/`, owns all of this: the pacing rules (pure, no
model and no database), the prompt and reply contract, and the final step of adding the Messages to the Interview. The coaching hint is not part of an exchange (it is its own endpoint,
`PUT .../messages/:id/helper`, so no question waits for it). `open_interview` (the opening) and
`send_message` (every later reply) both go through it and keep only what concerns their
request: loading, the claim, the lock and the commit.

The ask-back phase ends when the interviewer closes it (`done`, which the model sets when the
candidate declines or has no more questions) or after 5 candidate questions, whichever comes
first. The fifth question is still answered: the interviewer's reply answers it and closes
the phase in the same message. The Interview then becomes `completed` and `ended_at` is set. There is no separate
"finish" action: the candidate declining is a message like any other, and it is itself a
signal for the evaluation, as the workflow describes.

The interviewer's opening message is **not** made by `POST /api/interviews`. The session
page asks for it when it loads, with the idempotent `PUT /api/interviews/:id/opening`, so
the candidate reaches the session as soon as the plan exists and sees the interviewer
"typing" instead of an already-written question. (The first version generated it at the end
of create, so an Interview always had a message and a failed opening failed the whole
create; it was moved out because create was too slow and because a failed opening threw
away the expensive plan.) The consequences: an Interview can briefly have no messages, a
reply to such an Interview is refused with `409 INTERVIEW_NOT_OPENED`, and opening shares
the in-progress marker below with replies, so two opening calls at once run the model only
once (the second gets `409 TURN_IN_PROGRESS`). Opening an Interview that already has
messages returns its first message and calls no model. A failed opening leaves the
Interview as it is, and the client simply retries. `GET` still never has side effects.

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

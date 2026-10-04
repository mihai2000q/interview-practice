# Stale sessions are detected lazily, not via a background job

An Interview whose client never gracefully ends it (Alt+F4, crash, power loss) would
otherwise sit at `status = in_progress` forever, since no JS can run to notify the backend
on the way out — neither the in-app leave-confirmation guard nor a `beforeunload` handler
can help here. Rather than standing up a scheduled job/cron to sweep for these, staleness
is detected lazily: any `in_progress` Interview whose `last_activity_at` is older than a
timeout is flipped to `abandoned` the next time it's read (history list, reopening it).
Simpler than a background worker for a prototype at this scale; revisit if the app ever
needs near-real-time abandonment detection.

## How the rule is applied

Settling staleness is part of *loading* an Interview, not something each reader remembers
to do: `get_interview_or_404` closes a stale session before returning it, so every use
case (reading it, replying, abandoning, asking for suggestions) sees it as it stands now.
The applications list settles the stages it is about to show, so the history never draws a
dead session as `in_progress`. A reply to a session that went stale while the candidate
was away is refused with `409 INTERVIEW_ALREADY_ENDED`: staleness is settled before the
reply sets its own in-progress marker, which would otherwise make the session look active.

The flip is a compare-and-swap `UPDATE`, guarded by the activity time and exchange marker
the reader saw, so a message that arrives in between wins and nothing is overwritten. No
locks are involved. `ended_at` is when the activity stopped, not when it was noticed. An
Interview with an exchange in progress (a marker younger than 5 minutes, see ADR 0013) is
never stale, however long the model takes. The rules are pure functions of the Interview
and the time, in `app/services/interview_lifecycle.py`, because both the interviews and
the applications domains use them.

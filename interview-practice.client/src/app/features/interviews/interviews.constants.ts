export const MAX_QUESTION_COUNT = 30;
export const JOB_TITLE_MAX_LENGTH = 200;
export const COMPANY_NAME_MAX_LENGTH = 200;
export const MAX_MESSAGE_LENGTH = 2000;

/** What the Decline button sends: a plain message, so it counts like any reply (ADR 0013). */
export const DECLINE_ASK_BACK_MESSAGE =
  "Thank you, that covers everything I wanted to know, so I don't have any further questions. I appreciate your time today.";

/** While another request is creating the opening message: how often, and how many times, to look. */
export const OPENING_POLL_INTERVAL_MS = 1000;
export const OPENING_MAX_POLLS = 15;

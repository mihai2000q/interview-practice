import { z } from 'zod';
import {
  difficultySchema,
  interviewerRoleSchema,
  interviewStatusSchema,
  interviewTypeSchema,
  messagePhaseSchema,
  messageRoleSchema,
  responseStyleSchema,
  senioritySchema,
  toneSchema,
} from './interview.enums';

export const messageSchema = z.object({
  id: z.string(),
  phase: messagePhaseSchema,
  role: messageRoleSchema,
  content: z.string(),
  helperText: z.string().nullable(),
  /** The interviewer stayed on the previous question: not a question of its own. */
  isClarification: z.boolean(),
  sequence: z.number(),
  createdAt: z.coerce.date(),
});
export type Message = z.infer<typeof messageSchema>;

export const interviewSchema = z.object({
  id: z.string(),
  jobTitle: z.string(),
  companyName: z.string().nullable(),
  domain: z.string(),
  seniority: senioritySchema,
  difficulty: difficultySchema,
  tone: toneSchema,
  interviewType: interviewTypeSchema,
  interviewerRole: interviewerRoleSchema,
  responseStyle: responseStyleSchema,
  targetQuestionCount: z.number(),
  coachingHelpersEnabled: z.boolean(),
  status: interviewStatusSchema,
  personaName: z.string(),
  personaTitle: z.string(),
  personaImageUrl: z.string().nullable(),
  createdAt: z.coerce.date(),
  endedAt: z.coerce.date().nullable(),
  phase: messagePhaseSchema,
  messages: z.array(messageSchema),
});
export type Interview = z.infer<typeof interviewSchema>;

/** `PUT /api/interviews/:id/persona-image`: `null` when portraits are switched off. */
export const personaImageResultSchema = z.object({
  personaImageUrl: z.string().nullable(),
});

export const messageExchangeSchema = z.object({
  candidateMessage: messageSchema,
  interviewerMessage: messageSchema,
  phase: messagePhaseSchema,
  status: interviewStatusSchema,
});
export type MessageExchange = z.infer<typeof messageExchangeSchema>;

/** `GET /api/interviews/:id/ask-back-suggestions`: questions the candidate could ask. */
export const askBackSuggestionsSchema = z.object({
  suggestions: z.array(z.string()),
});

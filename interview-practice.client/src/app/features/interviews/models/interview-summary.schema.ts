import { z } from 'zod';
import { verdictSchema } from './evaluation.schema';
import { interviewerRoleSchema, interviewStatusSchema } from './interview.enums';

/** `GET /api/interviews`: one Interview as the history list needs it, without its messages. */
export const interviewSummarySchema = z.object({
  id: z.string(),
  jobTitle: z.string(),
  companyName: z.string().nullable(),
  interviewerRole: interviewerRoleSchema,
  status: interviewStatusSchema,
  /** `null` until an Evaluation exists (it is made when the Results page is opened). */
  verdict: verdictSchema.nullable(),
  /** `null` for a standalone Interview. */
  jobApplicationId: z.string().nullable(),
  createdAt: z.coerce.date(),
  endedAt: z.coerce.date().nullable(),
});
export type InterviewSummary = z.infer<typeof interviewSummarySchema>;

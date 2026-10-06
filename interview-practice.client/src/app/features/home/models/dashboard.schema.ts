import { z } from 'zod';
import { verdictSchema } from '@app/features/interviews/models/evaluation.schema';
import { interviewStatusSchema } from '@app/features/interviews/models/interview.enums';

/** `GET /api/dashboard`: the numbers behind the Home page. */
export const dashboardSchema = z.object({
  totalInterviews: z.number(),
  byStatus: z.object({
    inProgress: z.number(),
    completed: z.number(),
    abandoned: z.number(),
  }),
  outcomes: z.object({
    hire: z.number(),
    noHire: z.number(),
    /** Ended interviews that were answered but whose Results page was never opened. */
    awaitingEvaluation: z.number(),
  }),
  /** The interviews that ended most recently, newest first. */
  recent: z.array(
    z.object({
      id: z.string(),
      jobTitle: z.string(),
      companyName: z.string().nullable(),
      status: interviewStatusSchema,
      verdict: verdictSchema.nullable(),
      endedAt: z.coerce.date().nullable(),
    }),
  ),
});
export type Dashboard = z.infer<typeof dashboardSchema>;
export type RecentInterview = Dashboard['recent'][number];

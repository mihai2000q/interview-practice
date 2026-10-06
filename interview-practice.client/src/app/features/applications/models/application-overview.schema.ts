import { z } from 'zod';
import { verdictSchema } from '@app/features/interviews/models/evaluation.schema';
import {
  interviewerRoleSchema,
  interviewStatusSchema,
} from '@app/features/interviews/models/interview.enums';
import { applicationDocumentSchema } from './application-summary.schema';

/** One stage of the pipeline: an Interview as the overview lists it. */
export const overviewStageSchema = z.object({
  id: z.string(),
  interviewerRole: interviewerRoleSchema,
  status: interviewStatusSchema,
  /** `null` until an Evaluation exists (it is made when the Results page is opened). */
  verdict: verdictSchema.nullable(),
  createdAt: z.coerce.date(),
  endedAt: z.coerce.date().nullable(),
});
export type OverviewStage = z.infer<typeof overviewStageSchema>;

/** `GET /api/applications/:id`: the Application, its stages and how they compare. */
export const applicationOverviewSchema = z.object({
  id: z.string(),
  companyName: z.string().nullable(),
  jobTitle: z.string(),
  jobDescription: applicationDocumentSchema.nullable(),
  cv: applicationDocumentSchema.nullable(),
  coverLetter: applicationDocumentSchema.nullable(),
  /** 1-5; `null` until a progress summary has been generated. Always set with the summary. */
  progressScore: z.number().int().min(1).max(5).nullable(),
  progressSummary: z.string().nullable(),
  createdAt: z.coerce.date(),
  /** Oldest first. */
  interviews: z.array(overviewStageSchema),
});
export type ApplicationOverview = z.infer<typeof applicationOverviewSchema>;

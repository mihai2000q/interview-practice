import { z } from 'zod';
import {
  interviewerRoleSchema,
  interviewStatusSchema,
} from '@app/features/interviews/models/interview.enums';

export const applicationStageSchema = z.object({
  id: z.string(),
  interviewerRole: interviewerRoleSchema,
  status: interviewStatusSchema,
});
export type ApplicationStage = z.infer<typeof applicationStageSchema>;

/** A Document attached to an application, with its name so it can be shown without a lookup. */
export const applicationDocumentSchema = z.object({
  id: z.string(),
  name: z.string(),
  /** The model that made its cached analysis; null while it has none. */
  analysisModel: z.string().nullable(),
});
export type ApplicationDocument = z.infer<typeof applicationDocumentSchema>;

/** `GET /api/applications`: one Application with its attached Documents and its stages. */
export const applicationSummarySchema = z.object({
  id: z.string(),
  companyName: z.string().nullable(),
  jobTitle: z.string(),
  jobDescription: applicationDocumentSchema.nullable(),
  cv: applicationDocumentSchema.nullable(),
  coverLetter: applicationDocumentSchema.nullable(),
  /** Oldest first. */
  interviews: z.array(applicationStageSchema),
});
export type ApplicationSummary = z.infer<typeof applicationSummarySchema>;

export const applicationSummaryListSchema = z.array(applicationSummarySchema);

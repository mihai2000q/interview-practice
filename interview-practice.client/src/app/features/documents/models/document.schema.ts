import { z } from 'zod';

const documentTypeSchema = z.enum(['cv', 'cover_letter', 'job_description']);
export type DocumentType = z.infer<typeof documentTypeSchema>;

export const storedDocumentSchema = z.object({
  id: z.string(),
  type: documentTypeSchema,
  name: z.string(),
  sourceFilename: z.string(),
  saved: z.boolean(),
  /** The model that made its cached analysis; null while it has none. */
  analysisModel: z.string().nullable(),
  createdAt: z.coerce.date(),
});
export type StoredDocument = z.infer<typeof storedDocumentSchema>;

export const storedDocumentListSchema = z.array(storedDocumentSchema);

export const documentAnalysisSchema = z.object({
  model: z.string(),
  domain: z.string().nullable(),
  companyName: z.string().nullable(),
  skills: z.array(z.string()),
  likelyTopics: z.array(z.string()),
});
export type DocumentAnalysis = z.infer<typeof documentAnalysisSchema>;

/** Model and completion settings for an analysis; what a `jdAnalysis` override can carry. */
export interface AnalysisSettings {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  reasoningEffort?: string;
}

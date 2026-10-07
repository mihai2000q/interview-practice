import { z } from 'zod';

export const verdictSchema = z.enum(['hire', 'no_hire']);
export type Verdict = z.infer<typeof verdictSchema>;

export const starCompletenessSchema = z.enum(['strong', 'partial', 'weak']);
export type StarCompleteness = z.infer<typeof starCompletenessSchema>;

/** `PUT`/`GET /api/interviews/:id/evaluation`: how the candidate did. */
export const evaluationSchema = z.object({
  verdict: verdictSchema,
  reasoning: z.string(),
  /** Text with one strength per line. */
  strengths: z.string(),
  /** Text with one weakness per line. */
  weaknesses: z.string(),
  /** Text with one suggestion per line. */
  improvementSuggestions: z.string(),
  starBreakdown: z.object({
    situation: z.string(),
    task: z.string(),
    action: z.string(),
    result: z.string(),
    completeness: starCompletenessSchema,
  }),
  /** The Interview was abandoned, so this rests on a partial transcript. */
  incomplete: z.boolean(),
});
export type Evaluation = z.infer<typeof evaluationSchema>;

/** `GET /api/interviews/:id/interviewer-review`: how the AI interviewer did (dev-facing). */
export const interviewerReviewSchema = z.object({
  judgeModel: z.string(),
  /** Each from 1 to 5. */
  scores: z.object({
    questionRelevance: z.number(),
    personaConsistency: z.number(),
    pacing: z.number(),
  }),
  reasoning: z.string(),
});
export type InterviewerReview = z.infer<typeof interviewerReviewSchema>;

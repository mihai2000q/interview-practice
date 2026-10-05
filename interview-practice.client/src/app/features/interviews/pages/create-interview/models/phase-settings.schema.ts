import { z } from 'zod';

export const PHASES = [
  'jdAnalysis',
  'questionPlan',
  'liveConversation',
  'askBack',
  'evaluation',
  'interviewerReview',
] as const;
export type Phase = (typeof PHASES)[number];

export const PHASE_LABELS: Record<Phase, string> = {
  jdAnalysis: 'Job description & CV analysis',
  questionPlan: 'Question plan & persona',
  liveConversation: 'Live interview',
  askBack: 'Ask-back suggestions',
  evaluation: 'Evaluation',
  interviewerReview: 'Interviewer review (judge)',
};

export const DEFAULT_INTERVIEW_MODEL = 'gpt-5-mini';
export const INTERVIEW_MODELS = ['gpt-5-mini', 'gpt-5-nano', 'gpt-4o-mini'] as const;
/** Not a subset of `INTERVIEW_MODELS` on purpose, see docs/architecture.md and ADR 0009. Jev is a decision model, so only the judge can use it. */
export const JUDGE_MODELS = [
  'google/gemini-2.5-flash',
  'google/gemini-3.5-flash-lite',
  'gpt-5-mini',
  'gpt-5-nano',
  'typesafe/jev-1.13',
] as const;
/** Stand-ins for the Preferences defaults until Preferences exists; only used to place the sliders. */
export const DEFAULT_TEMPERATURE = 0.7;
export const DEFAULT_MAX_TOKENS = 1024;
export const REASONING_EFFORTS = ['minimal', 'low', 'medium', 'high'] as const;

export const phaseSettingsSchema = z.object({
  model: z.string().optional(),
  temperature: z.number().min(0).max(2).optional(),
  maxTokens: z.number().int().positive().optional(),
  reasoningEffort: z.enum(REASONING_EFFORTS).optional(),
});
export type PhaseSettings = z.infer<typeof phaseSettingsSchema>;

/** Per-phase LLM overrides; an absent phase or field falls back to the Preferences default. */
export const phaseSettingsOverrideSchema = z.partialRecord(z.enum(PHASES), phaseSettingsSchema);
export type PhaseSettingsOverride = z.infer<typeof phaseSettingsOverrideSchema>;

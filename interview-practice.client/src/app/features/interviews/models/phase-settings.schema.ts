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

/** The sliders' limits; the schema below accepts exactly these. */
export const TEMPERATURE_RANGE = { min: 0, max: 2, step: 0.1 } as const;
export const MAX_TOKENS_RANGE = { min: 128, max: 8192, step: 128 } as const;

export const phaseSettingsSchema = z.object({
  model: z.string().optional(),
  temperature: z.number().min(TEMPERATURE_RANGE.min).max(TEMPERATURE_RANGE.max).optional(),
  maxTokens: z.number().int().positive().optional(),
  reasoningEffort: z.enum(REASONING_EFFORTS).optional(),
});
export type PhaseSettings = z.infer<typeof phaseSettingsSchema>;

/** `settings` without its unset fields, or `undefined` when none is set. */
export function compactPhaseSettings(settings: PhaseSettings): PhaseSettings | undefined {
  const { model, temperature, maxTokens, reasoningEffort } = settings;
  const set: PhaseSettings = {
    ...(model !== undefined && { model }),
    ...(temperature !== undefined && { temperature }),
    ...(maxTokens !== undefined && { maxTokens }),
    ...(reasoningEffort !== undefined && { reasoningEffort }),
  };
  return Object.keys(set).length > 0 ? set : undefined;
}

/** Per-phase LLM overrides; an absent phase or field falls back to the Preferences default. */
export const phaseSettingsOverrideSchema = z.partialRecord(z.enum(PHASES), phaseSettingsSchema);
export type PhaseSettingsOverride = z.infer<typeof phaseSettingsOverrideSchema>;

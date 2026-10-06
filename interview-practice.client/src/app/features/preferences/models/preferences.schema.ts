import { z } from 'zod';
import { REASONING_EFFORTS } from '@app/core/phase-settings/phase-settings.schema';

/** What one phase runs on by default; a `null` setting means the provider's own default. */
const phasePreferencesSchema = z.object({
  model: z.string(),
  temperature: z.number().nullable(),
  maxTokens: z.number().int().nullable(),
  reasoningEffort: z.enum(REASONING_EFFORTS).nullable(),
});
export type PhasePreferences = z.infer<typeof phasePreferencesSchema>;

/** Every phase, keyed like `PhaseSettingsOverride`. */
export const preferencesSchema = z.object({
  jdAnalysis: phasePreferencesSchema,
  questionPlan: phasePreferencesSchema,
  liveConversation: phasePreferencesSchema,
  coachingHelpers: phasePreferencesSchema,
  evaluation: phasePreferencesSchema,
  interviewerReview: phasePreferencesSchema,
});
export type Preferences = z.infer<typeof preferencesSchema>;

/** A `PATCH` body: only what changed. A `null` setting goes back to its default. */
export type PreferencesPatch = {
  [Phase in keyof Preferences]?: Partial<PhasePreferences>;
};

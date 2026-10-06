import { z } from 'zod';
import {
  Difficulty,
  InterviewerRole,
  InterviewType,
  ResponseStyle,
  Seniority,
  Tone,
} from './interview.enums';
import { PhaseSettingsOverride } from '@app/core/phase-settings/phase-settings.schema';

/** `POST /api/interviews` body (docs/api-design.md). */
export interface CreateInterviewRequest {
  jobTitle: string;
  companyName?: string;
  seniority: Seniority;
  difficulty: Difficulty;
  targetQuestionCount: number;
  tone: Tone;
  interviewType: InterviewType;
  interviewerRole: InterviewerRole;
  responseStyle: ResponseStyle;
  coachingHelpersEnabled: boolean;
  jobDescriptionId: string | null;
  cvId: string | null;
  coverLetterId: string | null;
  jobApplication: { id: string } | { createNew: true } | null;
  phaseSettingsOverride?: PhaseSettingsOverride;
}

/** `POST /api/interviews`: only the id is used, to go to the session. */
export const createInterviewResponseSchema = z.object({ id: z.string() });
export type CreateInterviewResponse = z.infer<typeof createInterviewResponseSchema>;

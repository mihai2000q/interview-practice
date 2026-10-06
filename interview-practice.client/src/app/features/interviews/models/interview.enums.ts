import { z } from 'zod';

/** The vocabulary of an Interview, shared by the create form, the API shapes and the session. */
export const senioritySchema = z.enum(['junior', 'mid', 'senior']);
export type Seniority = z.infer<typeof senioritySchema>;

export const difficultySchema = z.enum(['easy', 'medium', 'hard']);
export type Difficulty = z.infer<typeof difficultySchema>;

export const toneSchema = z.enum(['strict', 'neutral', 'friendly']);
export type Tone = z.infer<typeof toneSchema>;

export const responseStyleSchema = z.enum(['concise', 'detailed']);
export type ResponseStyle = z.infer<typeof responseStyleSchema>;

export const interviewerRoleSchema = z.enum([
  'recruiter',
  'technical_screener',
  'hr',
  'hiring_manager',
]);
export type InterviewerRole = z.infer<typeof interviewerRoleSchema>;

export const interviewTypeSchema = z.enum(['technical', 'behavioral']);
export type InterviewType = z.infer<typeof interviewTypeSchema>;

export const messagePhaseSchema = z.enum(['qa', 'ask_back']);
export type MessagePhase = z.infer<typeof messagePhaseSchema>;

export const messageRoleSchema = z.enum(['interviewer', 'candidate']);
export type MessageRole = z.infer<typeof messageRoleSchema>;

export const interviewStatusSchema = z.enum(['in_progress', 'completed', 'abandoned']);
export type InterviewStatus = z.infer<typeof interviewStatusSchema>;

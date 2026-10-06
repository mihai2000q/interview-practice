import {
  Difficulty,
  InterviewerRole,
  InterviewType,
  ResponseStyle,
  Seniority,
  Tone,
} from './interview.enums';
import type { Interview } from './interview.schema';

/** Maps a select value to its label */
export function labelOf(options: readonly { value: string; label: string }[]) {
  return (value: unknown): string => options.find((option) => option.value === value)?.label ?? '';
}

export const SENIORITIES: readonly { value: Seniority; label: string }[] = [
  { value: 'junior', label: 'Junior' },
  { value: 'mid', label: 'Mid' },
  { value: 'senior', label: 'Senior' },
];

export const DIFFICULTIES: readonly { value: Difficulty; label: string }[] = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
];

export const INTERVIEW_TYPES: readonly { value: InterviewType; label: string; icon: string }[] = [
  { value: 'technical', label: 'Technical', icon: 'lucideCode' },
  { value: 'behavioral', label: 'Behavioral', icon: 'lucideMessageSquare' },
];

export const RESPONSE_STYLES: readonly { value: ResponseStyle; label: string }[] = [
  { value: 'concise', label: 'Concise' },
  { value: 'detailed', label: 'Detailed' },
];

export const INTERVIEWER_ROLES: readonly { value: InterviewerRole; label: string }[] = [
  { value: 'recruiter', label: 'Recruiter' },
  { value: 'technical_screener', label: 'Technical screener' },
  { value: 'hr', label: 'Human Resources' },
  { value: 'hiring_manager', label: 'Hiring manager' },
];

export const INTERVIEWER_TONES: readonly { value: Tone; label: string }[] = [
  { value: 'strict', label: 'Strict' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'friendly', label: 'Friendly' },
];

/** How an Interview was set up (seniority, difficulty, type, response style), as label/value rows. */
export function interviewSettings(
  interview: Pick<Interview, 'seniority' | 'difficulty' | 'interviewType' | 'responseStyle'>,
): { label: string; value: string }[] {
  return [
    { label: 'Seniority', value: labelOf(SENIORITIES)(interview.seniority) },
    { label: 'Difficulty', value: labelOf(DIFFICULTIES)(interview.difficulty) },
    { label: 'Type', value: labelOf(INTERVIEW_TYPES)(interview.interviewType) },
    { label: 'Response style', value: labelOf(RESPONSE_STYLES)(interview.responseStyle) },
  ];
}

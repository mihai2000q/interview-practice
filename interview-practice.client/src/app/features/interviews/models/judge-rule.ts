import { Phase } from './phase-settings.schema';

/**
 * The judge may never be a model that ran the interview (ADR 0009). The server answers
 * `409 JUDGE_MODEL_COLLISION` for the combination, so the pickers keep it from being chosen.
 */

/** The phases whose output is the interviewer the judge scores. */
export const INTERVIEWER_PHASES = ['questionPlan', 'liveConversation'] as const;
export type InterviewerPhase = (typeof INTERVIEWER_PHASES)[number];

/** The models in effect, whether chosen or inherited, for the judge and for the interviewer. */
export interface JudgeRuleModels {
  judge: string;
  interviewers: readonly string[];
}

export function isInterviewerPhase(phase: Phase): phase is InterviewerPhase {
  return (INTERVIEWER_PHASES as readonly Phase[]).includes(phase);
}

/** Whether `phase` can't run on `model` now: the judge's own for the interviewer, and the other way around. */
export function isModelTaken(phase: Phase, model: string, models: JudgeRuleModels): boolean {
  if (phase === 'interviewerReview') {
    return models.interviewers.includes(model);
  }
  return isInterviewerPhase(phase) && model === models.judge;
}

/** Who holds the models `isModelTaken` rules out for `phase`, shown next to them. */
export function takenNote(phase: Phase): string {
  return phase === 'interviewerReview' ? 'used by the interviewer' : 'used by the judge';
}

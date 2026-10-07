import { Phase } from './phase-settings.schema';

/**
 * The judge may never be a model that ran the interview (ADR 0009). The server answers
 * `409 JUDGE_MODEL_COLLISION` for the combination, so the pickers keep it from being chosen.
 */

/** The phases whose output is the interviewer the judge scores. */
export const INTERVIEWER_PHASES = ['questionPlan', 'liveConversation'] as const;
export type InterviewerPhase = (typeof INTERVIEWER_PHASES)[number];

/**
 * The models in effect, whether chosen or inherited, for the judge and for the interviewer. A
 * model is `undefined` when it isn't known: the Preferences it would come from aren't loaded.
 */
export interface JudgeRuleModels {
  judge: string | undefined;
  interviewers: readonly { phase: InterviewerPhase; model: string | undefined }[];
}

/** The models in effect, given what `modelOf` answers for each phase. */
export function resolveRuleModels(modelOf: (phase: Phase) => string | undefined): JudgeRuleModels {
  return {
    judge: modelOf('interviewerReview'),
    interviewers: INTERVIEWER_PHASES.map((phase) => ({ phase, model: modelOf(phase) })),
  };
}

export function isInterviewerPhase(phase: Phase): phase is InterviewerPhase {
  return (INTERVIEWER_PHASES as readonly Phase[]).includes(phase);
}

/** The interviewer phases that run on the judge's model, which the rule forbids. */
export function collidingPhases({ judge, interviewers }: JudgeRuleModels): InterviewerPhase[] {
  return judge === undefined
    ? []
    : interviewers.filter(({ model }) => model === judge).map(({ phase }) => phase);
}

/** Whether `phase` can't run on `model` now: the judge's own for the interviewer, and the other way around. */
export function isModelTaken(phase: Phase, model: string, models: JudgeRuleModels): boolean {
  if (phase === 'interviewerReview') {
    return models.interviewers.some((interviewer) => interviewer.model === model);
  }
  return isInterviewerPhase(phase) && model === models.judge;
}

/** What each interviewer phase is called in the note, as the page names the phase. */
const HOLDER_NAMES: Record<InterviewerPhase, string> = {
  questionPlan: 'the planner',
  liveConversation: 'the interviewer',
};

/**
 * Who holds `model`, which `isModelTaken` rules out for `phase`, shown next to it: for the
 * judge, the interviewer phases running on it (the planner, the interviewer, or both).
 */
export function takenNote(phase: Phase, model: string, models: JudgeRuleModels): string {
  if (phase !== 'interviewerReview') {
    return 'used by the judge';
  }
  const holders = models.interviewers
    .filter((interviewer) => interviewer.model === model)
    .map(({ phase: holder }) => HOLDER_NAMES[holder]);
  return `used by ${new Intl.ListFormat('en').format(holders)}`;
}

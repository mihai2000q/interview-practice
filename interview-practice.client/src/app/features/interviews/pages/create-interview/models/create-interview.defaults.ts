import {
  Difficulty,
  InterviewerRole,
  InterviewType,
  ResponseStyle,
  Tone,
} from '@app/features/interviews/models/interview.enums';

/** What picking a difficulty seeds */
export const DIFFICULTY_DEFAULTS: Record<
  Difficulty,
  {
    targetQuestionCount: number;
    tone: Tone;
    interviewType: InterviewType;
    responseStyle: ResponseStyle;
    coachingHelpersEnabled: boolean;
  }
> = {
  easy: {
    targetQuestionCount: 5,
    tone: 'friendly',
    interviewType: 'behavioral',
    responseStyle: 'concise',
    coachingHelpersEnabled: true,
  },
  medium: {
    targetQuestionCount: 8,
    tone: 'neutral',
    interviewType: 'behavioral',
    responseStyle: 'concise',
    coachingHelpersEnabled: false,
  },
  hard: {
    targetQuestionCount: 12,
    tone: 'strict',
    interviewType: 'technical',
    responseStyle: 'detailed',
    coachingHelpersEnabled: false,
  },
};

/** What picking an interviewer role seeds; both stay editable (the last pick wins). */
export const ROLE_DEFAULTS: Record<InterviewerRole, { interviewType: InterviewType; tone: Tone }> =
  {
    recruiter: { interviewType: 'behavioral', tone: 'friendly' },
    technical_screener: { interviewType: 'technical', tone: 'strict' },
    hr: { interviewType: 'behavioral', tone: 'neutral' },
    hiring_manager: { interviewType: 'technical', tone: 'friendly' },
  };

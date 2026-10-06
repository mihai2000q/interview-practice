import { Verdict } from './evaluation.schema';
import { InterviewStatus } from './interview.enums';

export type OutcomeTone = 'live' | 'success' | 'destructive' | 'muted';

export interface Outcome {
  label: string;
  tone: OutcomeTone;
  /** A lucide icon name. */
  icon: string;
}

/** How an Interview is described wherever it is listed: where it stands, or how it went. */
export function outcomeOf(interview: {
  status: InterviewStatus;
  verdict: Verdict | null;
}): Outcome {
  if (interview.status === 'in_progress') {
    return { label: 'In progress', tone: 'live', icon: 'lucideCircleDot' };
  }
  switch (interview.verdict) {
    case 'hire':
      return { label: 'Hire', tone: 'success', icon: 'lucideCircleCheck' };
    case 'no_hire':
      return { label: 'No hire', tone: 'destructive', icon: 'lucideCircleX' };
    default:
      return interview.status === 'abandoned'
        ? { label: 'Abandoned', tone: 'muted', icon: 'lucideCircleSlash' }
        : { label: 'See results', tone: 'muted', icon: 'lucideCircleDashed' };
  }
}

/** Text colour for a tone (theme tokens only). */
export const OUTCOME_TEXT: Record<OutcomeTone, string> = {
  live: 'text-primary',
  success: 'text-success',
  destructive: 'text-destructive',
  muted: 'text-muted-foreground',
};

/** The Spartan badge that carries a tone (a variant, plus the colour the variants don't have). */
export const OUTCOME_BADGE: Record<
  OutcomeTone,
  { variant: 'default' | 'secondary' | 'destructive'; class: string }
> = {
  live: { variant: 'default', class: '' },
  success: { variant: 'default', class: 'bg-success text-success-foreground' },
  destructive: { variant: 'destructive', class: '' },
  muted: { variant: 'secondary', class: '' },
};

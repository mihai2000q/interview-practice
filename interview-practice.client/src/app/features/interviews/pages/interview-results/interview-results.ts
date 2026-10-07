import { Component, computed, inject, input, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideChevronDown, lucideHouse, lucidePlus } from '@ng-icons/lucide';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { HlmCollapsibleImports } from '@spartan-ng/helm/collapsible';
import { HlmEmptyImports } from '@spartan-ng/helm/empty';
import { HlmSeparatorImports } from '@spartan-ng/helm/separator';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { HlmTooltipImports } from '@spartan-ng/helm/tooltip';
import { ApiError, toApiError } from '@app/core/api/api-error';
import { valueOrUndefined } from '@app/core/api/resource-value';
import {
  INTERVIEWER_ROLES,
  interviewSettings,
  labelOf,
} from '@app/features/interviews/models/interview.options';
import { endedByInterviewer } from '@app/features/interviews/models/interview-outcome';
import { InterviewsApi } from '@app/features/interviews/services/interviews-api';
import { ResultsCache } from '@app/features/interviews/services/results-cache';
import { ChatTranscript } from '@app/features/interviews/components/chat-transcript/chat-transcript';
import { PersonaAvatar } from '@app/features/interviews/components/persona-avatar/persona-avatar';
import { StrengthsWeaknesses } from './components/strengths-weaknesses/strengths-weaknesses';
import { ImprovementSuggestions } from './components/improvement-suggestions/improvement-suggestions';
import { InterviewerReviewPanel } from './components/interviewer-review-panel/interviewer-review-panel';
import { StarBreakdown } from './components/star-breakdown/star-breakdown';
import { VerdictSummary } from './components/verdict-summary/verdict-summary';

/** What the page says when the Evaluation can't be shown, and what the candidate can do about it. */
interface Problem {
  title: string;
  description: string;
  action: 'retry' | 'session' | 'new' | 'preferences' | 'home';
}

function problemOf(error: ApiError): Problem {
  switch (error.code) {
    case 'INTERVIEW_NOT_ENDED':
      return {
        title: 'This interview is still in progress',
        description: 'Finish it (or abandon it) first, then come back for your results.',
        action: 'session',
      };
    case 'NOTHING_TO_EVALUATE':
      return {
        title: 'Nothing to evaluate',
        description: "You didn't reply to the interviewer, so there is nothing to grade.",
        action: 'new',
      };
    case 'JUDGE_MODEL_COLLISION':
      // The Preferences changed since the interview was made; trying again fails the same way.
      return {
        title: "The judge can't use this model",
        description: error.message,
        action: 'preferences',
      };
    default:
      return error.status === 404
        ? { title: 'Interview not found', description: error.message, action: 'home' }
        : {
            title: 'Could not evaluate the interview',
            description: error.message,
            action: 'retry',
          };
  }
}

@Component({
  selector: 'app-interview-results',
  imports: [
    ChatTranscript,
    HlmBadge,
    HlmButtonImports,
    HlmCardImports,
    HlmCollapsibleImports,
    HlmEmptyImports,
    HlmSeparatorImports,
    HlmSkeleton,
    HlmTooltipImports,
    ImprovementSuggestions,
    StrengthsWeaknesses,
    InterviewerReviewPanel,
    NgIcon,
    PersonaAvatar,
    RouterLink,
    StarBreakdown,
    VerdictSummary,
  ],
  providers: [provideIcons({ lucideChevronDown, lucideHouse, lucidePlus })],
  templateUrl: './interview-results.html',
})
export class InterviewResults {
  readonly id = input.required<string>();

  private readonly api = inject(InterviewsApi);
  private readonly results = inject(ResultsCache);
  /** Makes the Evaluation (and the review) the first time, so this is the slow call; later it is remembered. */
  private readonly evaluationResource = rxResource({
    params: () => this.id(),
    stream: ({ params }) => this.results.evaluation(params),
  });
  /** The persona, the transcript and the settings: the page can do without them. */
  private readonly interviewResource = rxResource({
    params: () => this.id(),
    stream: ({ params }) => this.results.interview(params),
  });
  /** Made by the same call as the Evaluation, so it is asked for once that has finished. */
  private readonly reviewResource = rxResource({
    params: () => (this.evaluation() ? this.id() : undefined),
    stream: ({ params }) => this.results.review(params),
  });

  /**
   * What the page shows: what is already kept for this Interview, else what was requested. A
   * resource passes through "loading" even when its answer is at hand, which would flash the
   * skeletons for results that haven't changed.
   */
  private readonly kept = computed(() => this.results.kept(this.id()));
  protected readonly evaluation = computed(
    () => this.kept().evaluation ?? valueOrUndefined(this.evaluationResource),
  );
  protected readonly interview = computed(
    () => this.kept().interview ?? valueOrUndefined(this.interviewResource),
  );
  protected readonly review = computed(
    () => this.kept().review ?? valueOrUndefined(this.reviewResource),
  );
  protected readonly interviewLoading = this.interviewResource.isLoading;
  /** Without the Interview the portrait, settings and transcript are missing: say so. */
  protected readonly interviewError = computed(() => {
    const error = this.interviewResource.error();
    return error ? toApiError(error).message : null;
  });
  protected readonly reviewLoading = this.reviewResource.isLoading;
  protected readonly reviewError = computed(() =>
    this.reviewResource.error() ? 'Could not load the interviewer review.' : null,
  );
  protected readonly problem = computed(() => {
    const error = this.evaluationResource.error();
    return error ? problemOf(toApiError(error)) : null;
  });

  protected readonly personaImageUrl = computed(() =>
    this.interview()?.personaImageUrl ? this.api.personaImageUrl(this.id()) : null,
  );
  protected readonly role = computed(() =>
    labelOf(INTERVIEWER_ROLES)(this.interview()?.interviewerRole),
  );
  protected readonly statusLabel = computed(() => {
    const interview = this.interview();
    if (interview?.status === 'abandoned') {
      return 'Abandoned';
    }
    return interview && endedByInterviewer(interview) ? 'Ended by the interviewer' : 'Completed';
  });
  /** The Interview's settings, as the short chips under the heading (the label is the tooltip). */
  protected readonly facts = computed(() => {
    const interview = this.interview();
    return interview ? interviewSettings(interview, { withTone: true }) : [];
  });
  protected readonly subtitle = computed(() => {
    const interview = this.interview();
    if (!interview) {
      return null;
    }
    return interview.companyName
      ? `${interview.jobTitle} at ${interview.companyName}`
      : interview.jobTitle;
  });

  protected readonly transcriptOpen = signal(false);

  protected retry(): void {
    this.evaluationResource.reload();
  }

  protected retryInterview(): void {
    this.interviewResource.reload();
  }
}

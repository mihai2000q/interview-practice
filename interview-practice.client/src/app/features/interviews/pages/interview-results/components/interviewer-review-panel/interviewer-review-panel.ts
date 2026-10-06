import { Component, computed, input } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideFlaskConical } from '@ng-icons/lucide';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { InterviewerReview } from '@app/features/interviews/models/evaluation.schema';
import { ScoreGauge } from '@app/shared/components/score-gauge/score-gauge';

/**
 * The dev-facing review of the AI interviewer (not the candidate), set apart from the rest of the
 * Results page: a judge model scores question relevance, persona consistency and pacing.
 */
@Component({
  selector: 'app-interviewer-review-panel',
  imports: [HlmBadge, HlmSkeleton, NgIcon, ScoreGauge],
  providers: [provideIcons({ lucideFlaskConical })],
  templateUrl: './interviewer-review-panel.html',
})
export class InterviewerReviewPanel {
  /** `null` once loaded when there is no review (the judge's call failed). */
  readonly review = input<InterviewerReview | null | undefined>(undefined);
  readonly loading = input(false);
  /** The review could not be loaded (not the same as there being none). */
  readonly error = input<string | null>(null);

  protected readonly gauges = computed(() => {
    const scores = this.review()?.scores;
    return scores
      ? [
          { label: 'Question relevance', score: scores.questionRelevance },
          { label: 'Persona consistency', score: scores.personaConsistency },
          { label: 'Pacing', score: scores.pacing },
        ]
      : [];
  });
}

import { DatePipe } from '@angular/common';
import { Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideFileText } from '@ng-icons/lucide';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { HlmEmptyImports } from '@spartan-ng/helm/empty';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { toApiError } from '@app/core/api/api-error';
import { valueOrUndefined } from '@app/core/api/resource-value';
import { InterviewStatus } from '@app/features/interviews/models/interview.enums';
import { INTERVIEWER_ROLES, labelOf } from '@app/features/interviews/models/interview.options';
import { OUTCOME_BADGE, outcomeOf } from '@app/features/interviews/models/interview-outcome';
import { ScoreGauge } from '@app/shared/components/score-gauge/score-gauge';
import { ApplicationsApi } from '@app/features/applications/services/applications-api';

/** A progress summary needs this many stages with an Evaluation to compare. */
const STAGES_TO_COMPARE = 2;

/** One Application: its pipeline of stages, how they compare, and the documents behind it. */
@Component({
  selector: 'app-application-overview',
  imports: [
    DatePipe,
    HlmBadge,
    HlmButtonImports,
    HlmCardImports,
    HlmEmptyImports,
    HlmSkeleton,
    NgIcon,
    RouterLink,
    ScoreGauge,
  ],
  providers: [provideIcons({ lucideFileText })],
  templateUrl: './application-overview.html',
})
export class ApplicationOverviewPage {
  /** The route's `:id`. */
  readonly id = input.required<string>();

  private readonly api = inject(ApplicationsApi);
  private readonly overviewResource = rxResource({
    params: () => ({ id: this.id() }),
    stream: ({ params }) => this.api.get(params.id),
  });

  protected readonly overview = computed(() => valueOrUndefined(this.overviewResource));
  protected readonly error = computed(() => {
    const error = this.overviewResource.error();
    return error ? toApiError(error) : null;
  });

  protected readonly outcomeOf = outcomeOf;
  protected readonly badgeOf = OUTCOME_BADGE;
  protected readonly roleLabel = labelOf(INTERVIEWER_ROLES);
  protected readonly stagesToCompare = STAGES_TO_COMPARE;
  protected readonly placeholders = [1, 2, 3];

  /** How many stages have a verdict, so the page can say how far it is from a comparison. */
  protected readonly evaluatedCount = computed(
    () => this.overview()?.interviews.filter((stage) => stage.verdict !== null).length ?? 0,
  );

  protected readonly documents = computed(() => {
    const overview = this.overview();
    return overview
      ? [
          { label: 'Job description', document: overview.jobDescription },
          { label: 'CV', document: overview.cv },
          { label: 'Cover letter', document: overview.coverLetter },
        ]
      : [];
  });

  protected retry(): void {
    this.overviewResource.reload();
  }

  /** A running interview is resumed; a finished one opens its results. */
  protected link(stage: { id: string; status: InterviewStatus }): string[] {
    return stage.status === 'in_progress'
      ? ['/interviews', stage.id]
      : ['/interviews', stage.id, 'results'];
  }
}

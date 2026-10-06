import { DatePipe } from '@angular/common';
import { Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideFileText } from '@ng-icons/lucide';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { HlmEmptyImports } from '@spartan-ng/helm/empty';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { HlmSpinnerImports } from '@spartan-ng/helm/spinner';
import { toApiError } from '@app/core/api/api-error';
import { valueOrUndefined } from '@app/core/api/resource-value';
import {
  ApplicationOverview,
  OverviewStage,
} from '@app/features/applications/models/application-overview.schema';
import { InterviewStatus } from '@app/features/interviews/models/interview.enums';
import { INTERVIEWER_ROLES, labelOf } from '@app/features/interviews/models/interview.options';
import { OUTCOME_BADGE, outcomeOf } from '@app/features/interviews/models/interview-outcome';
import { ScoreGauge } from '@app/shared/components/score-gauge/score-gauge';
import { ResultsCache } from '@app/features/interviews/services/results-cache';
import { ApplicationsApi } from '@app/features/applications/services/applications-api';

/** A progress summary needs this many stages with an Evaluation to compare. */
const STAGES_TO_COMPARE = 2;

/** What making the progress summary is doing, for the card that shows it. */
type Refresh =
  | { kind: 'idle' }
  | { kind: 'working'; step: 'grading' | 'summarizing' }
  | { kind: 'failed'; message: string };

/** A stage that has ended, so it can be graded. */
const isFinished = (stage: OverviewStage) => stage.status !== 'in_progress';
/** A finished stage still waiting for its Evaluation (it is made when Results is opened). */
const isUngraded = (stage: OverviewStage) => isFinished(stage) && stage.verdict === null;

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
    HlmSpinnerImports,
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
  private readonly results = inject(ResultsCache);
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

  /** How many stages have ended: only those can be compared. */
  protected readonly finishedCount = computed(
    () => this.overview()?.interviews.filter(isFinished).length ?? 0,
  );

  protected readonly refresh = signal<Refresh>({ kind: 'idle' });
  protected readonly working = computed(() => this.refresh().kind === 'working');
  protected readonly refreshStep = computed(() => {
    const refresh = this.refresh();
    return refresh.kind === 'working' ? refresh.step : null;
  });
  protected readonly refreshError = computed(() => {
    const refresh = this.refresh();
    return refresh.kind === 'failed' ? refresh.message : null;
  });

  /** The Application whose summary was last made here, so a visit tries once. */
  private readonly attemptedFor = signal<string | null>(null);
  /** Stages that came back with nothing to grade: not asked again during this visit. */
  private readonly ungradable = new Set<string>();
  /** Counts the runs of `refreshProgress`, so an older one never overwrites a newer one's state. */
  private runs = 0;

  /** The page has found the summary missing or outdated and is about to make it. */
  private readonly pending = computed(() => {
    const overview = this.overview();
    return !!overview && this.attemptedFor() !== overview.id && this.needsRefresh(overview);
  });
  /** Making the summary, or about to: the card says so rather than that there is nothing. */
  protected readonly preparing = computed(() => this.working() || this.pending());

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

  constructor() {
    // Another Application's refresh is none of this one's business: forget it, and let any run
    // still going for the previous one finish without touching the card.
    effect(() => {
      this.id();
      untracked(() => {
        this.runs++;
        this.refresh.set({ kind: 'idle' });
      });
    });

    // The summary is made on demand (ADR 0015): grade the finished stages that have no
    // Evaluation, then ask for the summary, whenever the page finds it missing or outdated.
    effect(() => {
      const overview = this.overview();
      if (overview && this.pending()) {
        untracked(() => {
          this.attemptedFor.set(overview.id);
          void this.refreshProgress(overview);
        });
      }
    });
  }

  protected retry(): void {
    this.overviewResource.reload();
  }

  protected retryProgress(): void {
    const overview = this.overview();
    if (overview && !this.working()) {
      void this.refreshProgress(overview);
    }
  }

  /** A running interview is resumed; a finished one opens its results. */
  protected link(stage: { id: string; status: InterviewStatus }): string[] {
    return stage.status === 'in_progress'
      ? ['/interviews', stage.id]
      : ['/interviews', stage.id, 'results'];
  }

  private needsRefresh(overview: ApplicationOverview): boolean {
    const stages = overview.interviews;
    return (
      overview.progressOutdated ||
      (stages.some((stage) => this.isGradable(stage)) &&
        stages.filter(isFinished).length >= STAGES_TO_COMPARE)
    );
  }

  private isGradable(stage: OverviewStage): boolean {
    return isUngraded(stage) && !this.ungradable.has(stage.id);
  }

  /**
   * Grades every finished stage that has no Evaluation (the Results cache keeps what comes back,
   * so opening those results later asks for nothing), then asks for the summary, then reads the
   * page again. A stage with nothing to grade is left out, and not asked about again this visit; any other failure is told.
   */
  private async refreshProgress(overview: ApplicationOverview): Promise<void> {
    const { id } = overview;
    const ungraded = overview.interviews.filter((stage) => this.isGradable(stage));
    let graded = overview.interviews.filter((stage) => stage.verdict !== null).length;
    const run = ++this.runs;
    let problem: string | null = null;

    if (ungraded.length > 0) {
      this.refresh.set({ kind: 'working', step: 'grading' });
      const outcomes = await Promise.allSettled(
        ungraded.map((stage) => firstValueFrom(this.results.evaluation(stage.id))),
      );
      outcomes.forEach((outcome, index) => {
        if (outcome.status === 'fulfilled') {
          graded++;
          return;
        }
        const error = toApiError(outcome.reason);
        if (error.code === 'NOTHING_TO_EVALUATE') {
          this.ungradable.add(ungraded[index].id);
        } else {
          problem ??= error.message;
        }
      });
    }

    if (graded >= STAGES_TO_COMPARE) {
      this.refresh.set({ kind: 'working', step: 'summarizing' });
      try {
        await firstValueFrom(this.api.generateProgress(id));
      } catch (err) {
        problem ??= toApiError(err).message;
      }
    }

    // Only the latest run speaks for the card, and only this page's own data is read again.
    if (run === this.runs) {
      this.refresh.set(problem ? { kind: 'failed', message: problem } : { kind: 'idle' });
    }
    if (this.id() === id) {
      this.overviewResource.reload();
    }
  }
}

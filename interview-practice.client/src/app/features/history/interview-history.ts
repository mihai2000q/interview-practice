import { computed, inject, Service, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { toApiError } from '@app/core/api/api-error';
import { valueOrUndefined } from '@app/core/api/resource-value';
import { ApplicationsApi } from '@app/features/applications/services/applications-api';
import { ApplicationSummary } from '@app/features/applications/models/application-summary';
import { InterviewSummary } from '@app/features/interviews/models/interview-summary.schema';
import { InterviewsApi } from '@app/features/interviews/services/interviews-api';

/** The Interviews of one Application, oldest first: the stages of its pipeline. */
export interface HistoryGroup {
  kind: 'group';
  application: ApplicationSummary;
  stages: InterviewSummary[];
  /** When the newest stage started: where the group sits in the list. */
  latest: Date;
}

/** An Interview that belongs to no Application. */
export interface HistorySingle {
  kind: 'single';
  interview: InterviewSummary;
  latest: Date;
}

export type HistoryEntry = HistoryGroup | HistorySingle;

/**
 * The candidate's past interviews as the history sidebar lists them: grouped under their
 * Application, standalone ones on their own, all ordered by how recently they were started. One
 * instance for the whole app, so the sidebar, the drawer and the pages all share what was loaded.
 */
@Service()
export class InterviewHistory {
  private readonly interviewsApi = inject(InterviewsApi);
  private readonly applicationsApi = inject(ApplicationsApi);
  /** Bumped to read both lists again (after an interview was made, ended or evaluated). */
  private readonly version = signal(0);

  private readonly interviewsResource = rxResource({
    params: () => this.version(),
    stream: () => this.interviewsApi.list(),
  });
  private readonly applicationsResource = rxResource({
    params: () => this.version(),
    stream: () => this.applicationsApi.list(),
  });

  readonly loading = computed(
    () => this.interviewsResource.isLoading() || this.applicationsResource.isLoading(),
  );
  readonly error = computed(() => {
    const error = this.interviewsResource.error() ?? this.applicationsResource.error();
    return error ? toApiError(error).message : null;
  });

  /** `undefined` until both lists have arrived. */
  readonly entries = computed<HistoryEntry[] | undefined>(() => {
    const interviews = valueOrUndefined(this.interviewsResource);
    const applications = valueOrUndefined(this.applicationsResource);
    return interviews && applications ? groupHistory(interviews, applications) : undefined;
  });

  /** Reads both lists again, unless that is already happening (what is loading is fresh enough). */
  refresh(): void {
    if (!this.loading()) {
      this.version.update((version) => version + 1);
    }
  }
}

function groupHistory(
  interviews: readonly InterviewSummary[],
  applications: readonly ApplicationSummary[],
): HistoryEntry[] {
  const stagesOf = new Map<string, InterviewSummary[]>();
  const entries: HistoryEntry[] = [];
  for (const interview of interviews) {
    const known =
      interview.jobApplicationId !== null &&
      applications.some((application) => application.id === interview.jobApplicationId);
    if (known) {
      const key = interview.jobApplicationId as string;
      stagesOf.set(key, [...(stagesOf.get(key) ?? []), interview]);
    } else {
      entries.push({ kind: 'single', interview, latest: interview.createdAt });
    }
  }
  for (const application of applications) {
    const stages = (stagesOf.get(application.id) ?? []).sort(
      (a, b) => a.createdAt.getTime() - b.createdAt.getTime(),
    );
    if (stages.length > 0) {
      entries.push({
        kind: 'group',
        application,
        stages,
        latest: stages[stages.length - 1].createdAt,
      });
    }
  }
  return entries.sort((a, b) => b.latest.getTime() - a.latest.getTime());
}

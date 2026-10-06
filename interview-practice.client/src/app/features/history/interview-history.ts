import { computed, inject, linkedSignal, Service, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { firstValueFrom, Subject } from 'rxjs';
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

/** What the candidate asked to delete: an Application with its Interviews, or one Interview. */
export interface DeleteTarget {
  kind: 'application' | 'interview';
  id: string;
  /** What the history calls it, for the confirmation. */
  label: string;
  /** Every Interview that goes with it. */
  interviewIds: readonly string[];
  /** One of them is still being answered. */
  running: boolean;
}

/** The Application an entry is, or the standalone Interview, as something to delete. */
export function deleteTargetOf(entry: HistoryEntry, label: string): DeleteTarget {
  return entry.kind === 'group'
    ? {
        kind: 'application',
        id: entry.application.id,
        label,
        interviewIds: entry.stages.map((stage) => stage.id),
        running: entry.stages.some((stage) => stage.status === 'in_progress'),
      }
    : {
        kind: 'interview',
        id: entry.interview.id,
        label,
        interviewIds: [entry.interview.id],
        running: entry.interview.status === 'in_progress',
      };
}

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
  /** Counts what was deleted from here, so a page showing totals knows to read them again. */
  readonly deletions = signal(0);
  private readonly removedInterviews = new Subject<readonly string[]>();
  /** The ids of the Interviews that were deleted from here, for whatever keeps them around. */
  readonly interviewsRemoved$ = this.removedInterviews.asObservable();

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

  private readonly arrived = computed<HistoryEntry[] | undefined>(() => {
    const interviews = valueOrUndefined(this.interviewsResource);
    const applications = valueOrUndefined(this.applicationsResource);
    return interviews && applications ? groupHistory(interviews, applications) : undefined;
  });

  /**
   * `undefined` until both lists have arrived the first time. Reading them again keeps showing the
   * last ones until the new ones are here, so the sidebar doesn't blink on every visit.
   */
  readonly entries = linkedSignal<HistoryEntry[] | undefined, HistoryEntry[] | undefined>({
    source: this.arrived,
    computation: (arrived, previous) => arrived ?? previous?.value,
  });

  /** Deletes what was asked for, then reads the lists again. Already gone counts as deleted. */
  async remove(target: DeleteTarget): Promise<void> {
    try {
      await firstValueFrom(
        target.kind === 'application'
          ? this.applicationsApi.delete(target.id)
          : this.interviewsApi.delete(target.id),
      );
    } catch (err) {
      if (toApiError(err).status !== 404) {
        throw err;
      }
    }
    this.deletions.update((count) => count + 1);
    this.removedInterviews.next(target.interviewIds);
    this.version.update((version) => version + 1);
  }

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

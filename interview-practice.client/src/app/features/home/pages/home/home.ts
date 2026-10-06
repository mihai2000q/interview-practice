import { Component, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucidePlus } from '@ng-icons/lucide';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { HlmEmptyImports } from '@spartan-ng/helm/empty';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { toApiError } from '@app/core/api/api-error';
import { valueOrUndefined } from '@app/core/api/resource-value';
import { InterviewHistory } from '@app/features/history/interview-history';
import { DashboardApi } from '@app/features/home/services/dashboard-api';
import { HomeOnboarding } from './components/home-onboarding/home-onboarding';
import { OutcomeDonut } from './components/outcome-donut/outcome-donut';
import { RecentResults } from './components/recent-results/recent-results';
import { StatTile } from './components/stat-tile/stat-tile';

/** The dashboard: how the practice is going, in a few numbers and one ring. */
@Component({
  selector: 'app-home',
  imports: [
    HlmButtonImports,
    HlmCardImports,
    HlmEmptyImports,
    HlmSkeleton,
    HomeOnboarding,
    NgIcon,
    OutcomeDonut,
    RecentResults,
    RouterLink,
    StatTile,
  ],
  providers: [provideIcons({ lucidePlus })],
  templateUrl: './home.html',
})
export class Home {
  private readonly api = inject(DashboardApi);
  private readonly history = inject(InterviewHistory);
  private readonly dashboardResource = rxResource({
    // Deleting an entry in the sidebar changes every number here.
    params: () => this.history.deletions(),
    stream: () => this.api.get(),
  });

  protected readonly dashboard = computed(() => valueOrUndefined(this.dashboardResource));
  protected readonly error = computed(() => {
    const error = this.dashboardResource.error();
    return error ? toApiError(error).message : null;
  });
  protected readonly empty = computed(() => this.dashboard()?.totalInterviews === 0);

  protected readonly stats = computed(() => {
    const dashboard = this.dashboard();
    if (!dashboard) {
      return [];
    }
    const { byStatus, outcomes } = dashboard;
    const evaluated = outcomes.hire + outcomes.noHire;
    const practiced = [
      `${byStatus.completed} completed`,
      `${byStatus.abandoned} abandoned`,
      ...(byStatus.inProgress > 0 ? [`${byStatus.inProgress} in progress`] : []),
    ];
    return [
      {
        label: 'Interviews practiced',
        value: dashboard.totalInterviews,
        hint: practiced.join(' · '),
      },
      {
        label: 'Hire rate',
        value: evaluated ? `${Math.round((outcomes.hire / evaluated) * 100)}%` : '–',
        hint: evaluated
          ? `${outcomes.hire} of ${evaluated} evaluated`
          : 'No evaluated interviews yet',
      },
      {
        label: 'Awaiting results',
        value: outcomes.awaitingEvaluation,
        hint:
          outcomes.awaitingEvaluation > 0
            ? 'Open a finished interview to get its verdict'
            : 'All your finished interviews have a verdict',
      },
    ];
  });

  protected retry(): void {
    this.dashboardResource.reload();
  }
}

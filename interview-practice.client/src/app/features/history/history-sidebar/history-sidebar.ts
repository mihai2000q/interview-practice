import { DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  lucideBuilding2,
  lucideChevronDown,
  lucideCircleCheck,
  lucideCircleDashed,
  lucideCircleDot,
  lucideCircleSlash,
  lucideCircleX,
  lucidePlus,
} from '@ng-icons/lucide';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmCollapsibleImports } from '@spartan-ng/helm/collapsible';
import { HlmSidebarImports, HlmSidebarService } from '@spartan-ng/helm/sidebar';
import { filter } from 'rxjs';
import { OUTCOME_TEXT, outcomeOf } from '@app/features/interviews/models/interview-outcome';
import { INTERVIEWER_ROLES, labelOf } from '@app/features/interviews/models/interview.options';
import { HistoryGroup, InterviewHistory } from '../interview-history';

/**
 * The way into practice, beside the pages that show it: start an interview, or open a past one.
 * Spartan's sidebar does the rest (a panel on wide screens, a drawer on narrow ones, opened by the
 * topbar's trigger). Loaded lazily, as only some pages show it.
 */
@Component({
  selector: 'app-history-sidebar',
  imports: [
    DatePipe,
    HlmButtonImports,
    HlmCollapsibleImports,
    HlmSidebarImports,
    NgIcon,
    RouterLink,
    RouterLinkActive,
  ],
  providers: [
    provideIcons({
      lucideBuilding2,
      lucideChevronDown,
      lucideCircleCheck,
      lucideCircleDashed,
      lucideCircleDot,
      lucideCircleSlash,
      lucideCircleX,
      lucidePlus,
    }),
  ],
  templateUrl: './history-sidebar.html',
  host: { class: 'contents' },
})
export class HistorySidebar {
  protected readonly history = inject(InterviewHistory);
  private readonly sidebar = inject(HlmSidebarService);
  protected readonly outcomeOf = outcomeOf;
  protected readonly toneClass = OUTCOME_TEXT;
  protected readonly roleLabel = labelOf(INTERVIEWER_ROLES);
  protected readonly placeholders = [1, 2, 3, 4];

  constructor() {
    // Whatever was done since a page last showed this (an interview made, ended or evaluated) may
    // have changed it: read it again on arriving, and on every move between these pages.
    this.history.refresh();
    inject(Router)
      .events.pipe(
        filter((event) => event instanceof NavigationEnd),
        takeUntilDestroyed(),
      )
      .subscribe(() => this.history.refresh());
  }

  /** Starting an interview leaves the page: the drawer (narrow screens) closes behind it. */
  protected closeMobile(): void {
    this.sidebar.setOpenMobile(false);
  }

  protected groupLabel(group: HistoryGroup): string {
    const { companyName, jobTitle } = group.application;
    return companyName ? `${companyName} — ${jobTitle}` : jobTitle;
  }

  /** A running interview is resumed; a finished one opens its results. */
  protected link(interview: { id: string; status: string }): string[] {
    return interview.status === 'in_progress'
      ? ['/interviews', interview.id]
      : ['/interviews', interview.id, 'results'];
  }
}

import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
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
  lucideEllipsis,
  lucidePlus,
  lucideSettings,
  lucideTrash2,
} from '@ng-icons/lucide';
import { toast } from '@spartan-ng/brain/sonner';
import { HlmAlertDialogImports } from '@spartan-ng/helm/alert-dialog';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmCollapsibleImports } from '@spartan-ng/helm/collapsible';
import { HlmContextMenuImports } from '@spartan-ng/helm/context-menu';
import { HlmDropdownMenuImports } from '@spartan-ng/helm/dropdown-menu';
import { HlmSidebarImports } from '@spartan-ng/helm/sidebar';
import { filter } from 'rxjs';
import { InterviewStatus } from '@app/features/interviews/models/interview.enums';
import { OUTCOME_TEXT, outcomeOf } from '@app/features/interviews/models/interview-outcome';
import { INTERVIEWER_ROLES, labelOf } from '@app/features/interviews/models/interview.options';
import { toApiError } from '@app/core/api/api-error';
import {
  DeleteTarget,
  deleteTargetOf,
  HistoryEntry,
  HistoryGroup,
  InterviewHistory,
} from '../interview-history';

/**
 * The way into practice, beside the pages that show it: start an interview, or open a past one.
 * Spartan's sidebar does the rest (a panel on wide screens, a drawer on narrow ones, opened by the
 * topbar's trigger). Loaded lazily, as only some pages show it.
 */
@Component({
  selector: 'app-history-sidebar',
  imports: [
    DatePipe,
    HlmAlertDialogImports,
    HlmButtonImports,
    HlmCollapsibleImports,
    HlmContextMenuImports,
    HlmDropdownMenuImports,
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
      lucideEllipsis,
      lucidePlus,
      lucideSettings,
      lucideTrash2,
    }),
  ],
  templateUrl: './history-sidebar.html',
  host: { class: 'contents' },
})
export class HistorySidebar {
  protected readonly history = inject(InterviewHistory);
  protected readonly outcomeOf = outcomeOf;
  protected readonly toneClass = OUTCOME_TEXT;
  protected readonly roleLabel = labelOf(INTERVIEWER_ROLES);
  protected readonly placeholders = [1, 2, 3, 4];
  private readonly router = inject(Router);

  /** What the open confirmation is about; `null` while there is none. */
  protected readonly target = signal<DeleteTarget | null>(null);
  protected readonly deleting = signal(false);
  protected readonly deleteError = signal<string | null>(null);
  protected readonly deleteDescription = computed(() => {
    const target = this.target();
    if (!target) {
      return '';
    }
    const count = target.interviewIds.length;
    const what =
      target.kind === 'application'
        ? `all ${count === 1 ? 'its interview' : `${count} of its interviews`}, with their transcripts and results`
        : 'the interview, with its transcript and results';
    const running = target.running ? ' An interview that is still running is stopped too.' : '';
    return `This permanently deletes ${what}.${running} This can't be undone.`;
  });

  constructor() {
    // Whatever was done since a page last showed this (an interview made, ended or evaluated) may
    // have changed it: read it again on arriving, and on every move between these pages.
    this.history.refresh();
    this.router.events
      .pipe(
        filter((event) => event instanceof NavigationEnd),
        takeUntilDestroyed(),
      )
      .subscribe(() => this.history.refresh());
  }

  protected entryLabel(entry: HistoryEntry): string {
    if (entry.kind === 'group') {
      return this.groupLabel(entry);
    }
    const { companyName, jobTitle } = entry.interview;
    return companyName ? `${companyName} — ${jobTitle}` : jobTitle;
  }

  protected askDelete(entry: HistoryEntry): void {
    this.deleteError.set(null);
    this.target.set(deleteTargetOf(entry, this.entryLabel(entry)));
  }

  /** The dialog was dismissed (Escape, the backdrop, Cancel): forget the request, unless it is running. */
  protected onDialogState(state: 'open' | 'closed'): void {
    if (state === 'closed' && !this.deleting()) {
      this.target.set(null);
    }
  }

  protected async confirmDelete(): Promise<void> {
    const target = this.target();
    if (!target || this.deleting()) {
      return;
    }
    this.deleteError.set(null);
    this.deleting.set(true);
    try {
      await this.history.remove(target);
      this.target.set(null);
      toast.success(`Deleted “${target.label}”`);
      // The page on screen may be one of the deleted interviews, or the deleted application.
      if ([target.id, ...target.interviewIds].some((id) => this.router.url.includes(id))) {
        await this.router.navigateByUrl('/');
      }
    } catch (err) {
      this.deleteError.set(toApiError(err).message);
    } finally {
      this.deleting.set(false);
    }
  }

  protected groupLabel(group: HistoryGroup): string {
    const { companyName, jobTitle } = group.application;
    return companyName ? `${companyName} — ${jobTitle}` : jobTitle;
  }

  /** A running interview is resumed; a finished one opens its results. */
  protected link(interview: { id: string; status: InterviewStatus }): string[] {
    return interview.status === 'in_progress'
      ? ['/interviews', interview.id]
      : ['/interviews', interview.id, 'results'];
  }
}

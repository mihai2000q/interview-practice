import { Component, computed, input } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideCircleCheck, lucideCircleX, lucideTriangleAlert } from '@ng-icons/lucide';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { Verdict } from '@app/features/interviews/models/evaluation.schema';

/** The headline of the Results page: hire or no hire, and why. */
@Component({
  selector: 'app-verdict-summary',
  imports: [HlmBadge, HlmCardImports, NgIcon],
  providers: [provideIcons({ lucideCircleCheck, lucideCircleX, lucideTriangleAlert })],
  templateUrl: './verdict-summary.html',
})
export class VerdictSummary {
  readonly verdict = input.required<Verdict>();
  readonly reasoning = input.required<string>();
  /** The Interview was abandoned: the verdict rests on part of the conversation. */
  readonly incomplete = input.required<boolean>();

  protected readonly hired = computed(() => this.verdict() === 'hire');
}

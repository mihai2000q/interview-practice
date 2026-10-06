import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { OUTCOME_BADGE, outcomeOf } from '@app/features/interviews/models/interview-outcome';
import { RecentInterview } from '@app/features/home/models/dashboard.schema';

/** The interviews that ended last, each one click from its results. */
@Component({
  selector: 'app-recent-results',
  imports: [DatePipe, HlmBadge, HlmCardImports, RouterLink],
  templateUrl: './recent-results.html',
})
export class RecentResults {
  readonly items = input.required<readonly RecentInterview[]>();

  protected readonly outcomeOf = outcomeOf;
  protected readonly badgeOf = OUTCOME_BADGE;
}

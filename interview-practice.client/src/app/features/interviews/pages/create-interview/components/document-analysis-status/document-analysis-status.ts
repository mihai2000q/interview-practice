import { Component, computed, input, output } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideCircleCheck, lucideInfo } from '@ng-icons/lucide';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmSpinnerImports } from '@spartan-ng/helm/spinner';
import { HlmTooltipImports } from '@spartan-ng/helm/tooltip';

/**
 * `running`: being analyzed. `done`: analyzed by the model the interview will use. `missing`: no
 * analysis. `outdated`: analyzed by another model than the interview will use, which the server
 * redoes at creation. In the last two the candidate can analyze it now instead (faster later).
 */
export type DocumentAnalysisState = 'running' | 'done' | 'missing' | 'outdated';

@Component({
  selector: 'app-document-analysis-status',
  imports: [HlmButtonImports, HlmSpinnerImports, HlmTooltipImports, NgIcon],
  providers: [provideIcons({ lucideCircleCheck, lucideInfo })],
  templateUrl: './document-analysis-status.html',
  host: { class: 'block text-sm', 'aria-live': 'polite', role: 'status' },
})
export class DocumentAnalysisStatus {
  readonly state = input.required<DocumentAnalysisState>();
  /** The model that made the Document's analysis, if it has one. */
  readonly analysisModel = input<string | null>(null);
  /** The model the interview will analyze with. */
  readonly expectedModel = input.required<string>();
  /** The last attempt to analyze it failed for a reason that isn't the Document's. */
  readonly attemptFailed = input(false);
  readonly analyzeNow = output();

  protected readonly message = computed(() => {
    const base =
      this.state() === 'outdated'
        ? 'Document analyzed with a different model.'
        : 'Document not analyzed.';
    return this.attemptFailed() ? `${base} The last attempt failed.` : base;
  });
  protected readonly actionLabel = computed(() => {
    if (this.attemptFailed()) {
      return 'Try again';
    }
    return this.state() === 'outdated' ? 'Analyze again' : 'Analyze now';
  });
  protected readonly hint = computed(() =>
    this.state() === 'outdated'
      ? `It was analyzed with ${this.analysisModel()}, but this interview uses ${this.expectedModel()}. Creating the interview will analyze it again, which might take longer.`
      : 'Creating the interview might take longer without an already cached analysis.',
  );
}

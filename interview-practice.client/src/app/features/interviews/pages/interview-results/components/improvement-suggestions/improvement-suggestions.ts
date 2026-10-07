import { Component, computed, input } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideLightbulb } from '@ng-icons/lucide';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { evaluationLines } from '@app/features/interviews/models/evaluation-lines';

/** What to work on next, one suggestion per line of the Evaluation's text. */
@Component({
  selector: 'app-improvement-suggestions',
  imports: [HlmCardImports, NgIcon],
  providers: [provideIcons({ lucideLightbulb })],
  templateUrl: './improvement-suggestions.html',
})
export class ImprovementSuggestions {
  /** Text with one suggestion per line. */
  readonly text = input.required<string>();

  protected readonly suggestions = computed(() => evaluationLines(this.text()));
}

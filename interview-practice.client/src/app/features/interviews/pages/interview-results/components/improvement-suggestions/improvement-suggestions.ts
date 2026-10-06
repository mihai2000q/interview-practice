import { Component, computed, input } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideLightbulb } from '@ng-icons/lucide';
import { HlmCardImports } from '@spartan-ng/helm/card';

/** A bullet or number the model put in front of a line ("- ", "* ", "1. ", "2) "). */
const LIST_MARKER = /^(?:[-*•]|\d+[.)])\s+/;

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

  protected readonly suggestions = computed(() =>
    this.text()
      .split('\n')
      .map((line) => line.trim().replace(LIST_MARKER, ''))
      .filter((line) => line.length > 0),
  );
}

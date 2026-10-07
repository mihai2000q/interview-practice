import { Component, computed, input } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideCircleAlert, lucideCircleCheck } from '@ng-icons/lucide';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { evaluationLines } from '@app/features/interviews/models/evaluation-lines';

/** What went well and where it fell short, one point per line of the Evaluation's texts. */
@Component({
  selector: 'app-strengths-weaknesses',
  imports: [HlmCardImports, NgIcon],
  providers: [provideIcons({ lucideCircleAlert, lucideCircleCheck })],
  templateUrl: './strengths-weaknesses.html',
})
export class StrengthsWeaknesses {
  /** Text with one strength per line. */
  readonly strengths = input.required<string>();
  /** Text with one weakness per line. */
  readonly weaknesses = input.required<string>();

  protected readonly strengthItems = computed(() => evaluationLines(this.strengths()));
  protected readonly weaknessItems = computed(() => evaluationLines(this.weaknesses()));
}

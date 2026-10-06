import { Component, computed, input } from '@angular/core';
import { HlmBadge } from '@spartan-ng/helm/badge';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { Evaluation, StarCompleteness } from '@app/features/interviews/models/evaluation.schema';

const COMPLETENESS: Record<StarCompleteness, { label: string; filled: number; color: string }> = {
  strong: { label: 'Strong', filled: 3, color: 'bg-success' },
  partial: { label: 'Partial', filled: 2, color: 'bg-warning' },
  weak: { label: 'Weak', filled: 1, color: 'bg-destructive' },
};

/** How well the answers followed STAR (Situation, Task, Action, Result), one line per letter. */
@Component({
  selector: 'app-star-breakdown',
  imports: [HlmBadge, HlmCardImports],
  templateUrl: './star-breakdown.html',
})
export class StarBreakdown {
  readonly breakdown = input.required<Evaluation['starBreakdown']>();

  protected readonly completeness = computed(() => COMPLETENESS[this.breakdown().completeness]);
  protected readonly segments = computed(() => {
    const { filled, color } = this.completeness();
    return [0, 1, 2].map((i) => (i < filled ? color : 'bg-muted'));
  });
  protected readonly letters = computed(() => {
    const { situation, task, action, result } = this.breakdown();
    return [
      { letter: 'S', name: 'Situation', text: situation },
      { letter: 'T', name: 'Task', text: task },
      { letter: 'A', name: 'Action', text: action },
      { letter: 'R', name: 'Result', text: result },
    ];
  });
}

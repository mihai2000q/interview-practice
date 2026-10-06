import { Component, computed, input } from '@angular/core';
import { HlmChartImports } from '@spartan-ng/helm/chart';
import { defineChart } from '@tanstack/charts';
import { pie, polar, radialArc } from '@tanstack/charts/polar';

/**
 * Hired against not hired, as a ring with the passed share written in its middle. The ring is a
 * summary: the legend beside it gives every number in text, so nothing depends on reading it.
 */
@Component({
  selector: 'app-outcome-donut',
  imports: [HlmChartImports],
  templateUrl: './outcome-donut.html',
})
export class OutcomeDonut {
  readonly hire = input.required<number>();
  readonly noHire = input.required<number>();

  protected readonly evaluated = computed(() => this.hire() + this.noHire());
  protected readonly legend = computed(() => {
    const evaluated = this.evaluated();
    const share = (count: number) => (evaluated ? Math.round((count / evaluated) * 100) : 0);
    return [
      { label: 'Hire', count: this.hire(), share: share(this.hire()), dot: 'bg-success' },
      {
        label: 'No hire',
        count: this.noHire(),
        share: share(this.noHire()),
        dot: 'bg-destructive',
      },
    ];
  });
  protected readonly summary = computed(() =>
    this.evaluated() === 0
      ? 'No evaluated interviews yet'
      : `${this.hire()} of ${this.evaluated()} evaluated interviews ended in a hire`,
  );

  protected readonly chart = computed(() => {
    // An empty ring when nothing has been evaluated, so the card is not a blank space. A segment
    // with nothing in it is left out, so a lone one is a whole ring and not a ring with a notch.
    const parts =
      this.evaluated() === 0
        ? [{ id: 'empty', value: 1 }]
        : [
            { id: 'hire', value: this.hire() },
            { id: 'noHire', value: this.noHire() },
          ].filter((part) => part.value > 0);
    const slices = pie(parts, { value: 'value', gapAngle: parts.length > 1 ? 0.05 : 0 });
    return {
      definition: defineChart({
        marks: [
          polar({
            radiusRatio: 0.95,
            scales: { angle: null, radius: null },
            marks: [
              radialArc(slices, {
                innerRadius: ({ radius }) => radius * 0.72,
                cornerRadius: 6,
                color: 'id',
                key: 'id',
              }),
            ],
          }),
        ],
        scales: { x: null, y: null },
        color: {
          domain: ['hire', 'noHire', 'empty'],
          range: ['var(--success)', 'var(--destructive)', 'var(--muted)'],
        },
      }),
      ariaLabel: this.summary(),
      aspectRatio: 1,
    };
  });
}

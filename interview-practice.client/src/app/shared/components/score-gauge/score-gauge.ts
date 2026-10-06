import { Component, computed, input } from '@angular/core';
import { HlmChartImports } from '@spartan-ng/helm/chart';
import { defineChart } from '@tanstack/charts';
import { pie, polar, radialArc } from '@tanstack/charts/polar';

/** Scores run from 1 to 5. */
const MAX_SCORE = 5;

/** The gauge sweeps three quarters of a circle, open at the bottom. */
const SWEEP = Math.PI * 0.75;

/**
 * A score out of a maximum as a partial-circle gauge. The arc is a compact summary: the exact
 * value is written next to it, in text, so nothing depends on reading the arc.
 */
@Component({
  selector: 'app-score-gauge',
  imports: [HlmChartImports],
  templateUrl: './score-gauge.html',
  host: { class: 'flex flex-col items-center gap-1 text-center' },
})
export class ScoreGauge {
  readonly label = input.required<string>();
  readonly score = input.required<number>();

  protected readonly max = MAX_SCORE;

  /** Kept inside the scale, so a stray value from the server can't draw past the arc. */
  protected readonly value = computed(() => Math.min(Math.max(this.score(), 0), MAX_SCORE));

  protected readonly chart = computed(() => {
    const value = this.value();
    const parts = [
      { id: 'score', value },
      { id: 'remaining', value: MAX_SCORE - value },
    ] as const;
    const slices = pie(parts, { value: 'value', startAngle: -SWEEP, endAngle: SWEEP });

    return {
      definition: defineChart({
        marks: [
          polar({
            radiusRatio: 0.9,
            scales: { angle: null, radius: null },
            marks: [
              radialArc(slices, {
                innerRadius: ({ radius }) => radius * 0.74,
                cornerRadius: 999,
                color: 'id',
                key: 'id',
              }),
            ],
          }),
        ],
        scales: { x: null, y: null },
        color: { domain: ['score', 'remaining'], range: ['var(--chart-2)', 'var(--muted)'] },
      }),
      ariaLabel: `${this.label()}: ${value} out of ${MAX_SCORE}`,
      aspectRatio: 1,
    };
  });
}

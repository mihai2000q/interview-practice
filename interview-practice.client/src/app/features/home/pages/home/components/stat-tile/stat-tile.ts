import { Component, input } from '@angular/core';
import { HlmCardImports } from '@spartan-ng/helm/card';

/** One headline number with what it means. */
@Component({
  selector: 'app-stat-tile',
  imports: [HlmCardImports],
  template: `
    <section class="h-full gap-2 [--card-spacing:--spacing(4)]" hlmCard>
      <div class="gap-1" hlmCardHeader>
        <p hlmCardDescription>{{ label() }}</p>
        <p class="text-3xl tracking-tight tabular-nums" hlmCardTitle>{{ value() }}</p>
      </div>
      @if (hint(); as hint) {
        <div hlmCardContent>
          <p class="text-xs text-muted-foreground">{{ hint }}</p>
        </div>
      }
    </section>
  `,
  host: { class: 'block' },
})
export class StatTile {
  readonly label = input.required<string>();
  readonly value = input.required<string | number>();
  readonly hint = input<string | null>(null);
}

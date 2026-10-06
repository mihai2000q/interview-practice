import { Component, input } from '@angular/core';

/** Three bouncing dots, for "the other side is writing". */
@Component({
  selector: 'app-typing-indicator',
  template: `
    <span class="sr-only">{{ label() }}</span>
    @for (delay of delays; track delay) {
      <span
        [style.animation-delay.ms]="delay"
        aria-hidden="true"
        class="size-1.5 animate-bounce rounded-full bg-muted-foreground motion-reduce:animate-pulse"
      ></span>
    }
  `,
  host: { class: 'inline-flex items-center gap-1', role: 'status' },
})
export class TypingIndicator {
  readonly label = input('Typing…');
  protected readonly delays = [0, 150, 300];
}

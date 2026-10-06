import { DOCUMENT } from '@angular/common';
import { Component, computed, effect, inject, input, linkedSignal, output } from '@angular/core';

const TICK_MS = 30;
const CHARS_PER_SECOND = 60;
/** Long messages speed up instead of making the candidate wait. */
const MAX_DURATION_MS = 6000;

/**
 * Reveals `text` character by character, so whatever holds it grows as it types. Screen readers
 * get the whole message at once instead of one character at a time.
 */
@Component({
  selector: 'app-typewriter',
  template: `
    <span class="sr-only">{{ text() }}</span>
    <span aria-hidden="true">{{ revealed() }}</span>
  `,
  host: { class: 'whitespace-pre-wrap' },
})
export class Typewriter {
  readonly text = input.required<string>();
  /** Turning this off (for example once the candidate replies) shows the rest immediately. */
  readonly animate = input(true);
  readonly finished = output();

  private readonly reducedMotion =
    inject(DOCUMENT).defaultView?.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  private readonly shown = linkedSignal(() =>
    this.animate() && !this.reducedMotion ? 0 : this.text().length,
  );
  protected readonly revealed = computed(() => this.text().slice(0, this.shown()));

  constructor() {
    effect((onCleanup) => {
      const length = this.text().length;
      if (!this.animate()) {
        return;
      }
      if (this.reducedMotion || length === 0) {
        // Nothing to type out, but whoever waits for the message to be shown still needs to know.
        this.finished.emit();
        return;
      }
      const duration = Math.min((length / CHARS_PER_SECOND) * 1000, MAX_DURATION_MS);
      const step = Math.ceil(length / Math.max(1, Math.ceil(duration / TICK_MS)));
      const timer = setInterval(() => {
        const next = Math.min(this.shown() + step, length);
        this.shown.set(next);
        if (next >= length) {
          clearInterval(timer);
          this.finished.emit();
        }
      }, TICK_MS);
      onCleanup(() => clearInterval(timer));
    });
  }
}

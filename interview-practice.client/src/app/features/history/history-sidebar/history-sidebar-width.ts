import { computed, Service, signal } from '@angular/core';

const STORAGE_KEY = 'history-sidebar-width';
export const MIN_WIDTH = 224;
export const MAX_WIDTH = 480;
const DEFAULT_WIDTH = 256; // Spartan's own 16rem

/** How wide the history sidebar is on wide screens, as set by dragging its edge. Remembered. */
@Service()
export class HistorySidebarWidth {
  readonly px = signal(this.stored());
  /** While the edge is being dragged, the layout skips its width transitions so it keeps up. */
  readonly dragging = signal(false);
  /** For the sidebar wrapper's `--sidebar-width`. */
  readonly css = computed(() => `${this.px()}px`);

  set(px: number): void {
    this.px.set(Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, px)));
  }

  /** Called when a drag ends, rather than on every move. */
  save(): void {
    this.px.set(Math.round(this.px()));
    try {
      localStorage.setItem(STORAGE_KEY, String(this.px()));
    } catch {
      // Private mode or blocked storage: the width just lasts until the page is closed.
    }
  }

  private stored(): number {
    try {
      const value = Number(localStorage.getItem(STORAGE_KEY));
      return value >= MIN_WIDTH && value <= MAX_WIDTH ? value : DEFAULT_WIDTH;
    } catch {
      return DEFAULT_WIDTH;
    }
  }
}

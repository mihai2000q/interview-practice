import { DOCUMENT } from '@angular/common';
import { computed, effect, inject, Service, signal } from '@angular/core';

export type ThemeName = 'dark' | 'light';

const STORAGE_KEY = 'theme';

/**
 * The light or dark look, as the `dark` class on `<html>`. The page starts dark (index.html), and a
 * script there applies a saved light choice before the first paint, so the DOM is the source of
 * truth on startup and nothing flashes.
 */
@Service()
export class AppTheme {
  private readonly root = inject(DOCUMENT).documentElement;

  readonly theme = signal<ThemeName>(this.root.classList.contains('dark') ? 'dark' : 'light');
  readonly isDark = computed(() => this.theme() === 'dark');

  constructor() {
    effect(() => this.root.classList.toggle('dark', this.isDark()));
  }

  toggle(): void {
    const next: ThemeName = this.isDark() ? 'light' : 'dark';
    this.theme.set(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage can be blocked (private windows): the choice then lasts until the page closes.
    }
  }
}

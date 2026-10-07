import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideCircleCheck } from '@ng-icons/lucide';
import { HlmSpinnerImports } from '@spartan-ng/helm/spinner';

/** Not tied to the server's real progress; it only shows that something is being prepared. */
const STEPS = [
  'Reading the job details',
  'Choosing your interviewer',
  'Writing the questions',
  'Setting the evaluation criteria',
  'Putting the final touches',
] as const;
/** Once STEPS are done, these rotate for as long as the creation takes (high reasoning effort). */
const WAITING = [
  'Preparing the environment',
  'Warming up the interviewer',
  'Arranging the room',
  'Double-checking the details',
  'Almost ready',
] as const;
const STEP_MS = 3000;

/**
 * Full-page overlay shown while the interview is being created. It steps through STEPS on a timer,
 * then loops through WAITING until the page navigates away or the creation fails.
 */
@Component({
  selector: 'app-interview-creation-progress',
  imports: [HlmSpinnerImports, NgIcon],
  providers: [provideIcons({ lucideCircleCheck })],
  templateUrl: './interview-creation-progress.html',
  host: {
    class: 'fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm',
  },
})
export class InterviewCreationProgress {
  protected readonly steps = STEPS;
  private readonly ticks = signal(0);
  /** The step in progress; `steps.length` once all of them are done. */
  protected readonly current = computed(() => Math.min(this.ticks(), STEPS.length));
  protected readonly waiting = computed(() => {
    const extra = this.ticks() - STEPS.length;
    return extra >= 0 ? WAITING[extra % WAITING.length] : null;
  });

  constructor() {
    const timer = setInterval(() => this.ticks.update((ticks) => ticks + 1), STEP_MS);
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
  }
}

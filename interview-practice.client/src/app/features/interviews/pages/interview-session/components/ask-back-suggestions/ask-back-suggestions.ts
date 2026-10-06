import { Component, computed, inject, input, output, signal } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideCheck, lucideLightbulb, lucideRefreshCw } from '@ng-icons/lucide';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmPopoverImports } from '@spartan-ng/helm/popover';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { firstValueFrom } from 'rxjs';
import { toApiError } from '@app/core/api/api-error';
import { InterviewsApi } from '@app/features/interviews/services/interviews-api';

/**
 * Suggested questions to ask the interviewer, in a popover. They are fetched the first time it
 * opens (each fetch is an LLM call) and kept until the candidate asks for new ones. Picking one
 * hands it over to be edited and sent; the ones already sent are shown as asked and can't be
 * picked again.
 */
let nextSuggestionId = 0;

/** The interview moved on (ended, left ask-back, helpers off): asking again won't change that. */
const FINAL_REFUSALS = new Set([
  'INTERVIEW_ALREADY_ENDED',
  'NOT_IN_ASK_BACK_PHASE',
  'HELPERS_DISABLED',
]);

@Component({
  selector: 'app-ask-back-suggestions',
  imports: [HlmButtonImports, HlmPopoverImports, HlmSkeleton, NgIcon],
  providers: [provideIcons({ lucideCheck, lucideLightbulb, lucideRefreshCw })],
  templateUrl: './ask-back-suggestions.html',
})
export class AskBackSuggestions {
  readonly interviewId = input.required<string>();
  /** Suggestions the candidate has already sent (possibly after editing them). */
  readonly used = input<readonly string[]>([]);
  readonly picked = output<string>();
  /** The server says suggestions are no longer possible; the page should re-read the interview. */
  readonly unavailable = output();

  private readonly api = inject(InterviewsApi);
  /** Each has its own id: the model can return the same question twice, so the text can't be a key. */
  protected readonly suggestions = signal<{ id: number; text: string }[] | null>(null);
  protected readonly usedSet = computed(() => new Set(this.used()));
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly retryable = signal(true);

  protected onStateChange(state: 'open' | 'closed'): void {
    if (state === 'open' && this.suggestions() === null && !this.loading()) {
      void this.load();
    }
  }

  protected async load(): Promise<void> {
    this.error.set(null);
    this.retryable.set(true);
    this.loading.set(true);
    try {
      const suggestions = await firstValueFrom(this.api.getAskBackSuggestions(this.interviewId()));
      this.suggestions.set(suggestions.map((text) => ({ id: nextSuggestionId++, text })));
    } catch (err) {
      const error = toApiError(err);
      this.error.set(error.message);
      if (FINAL_REFUSALS.has(error.code)) {
        this.retryable.set(false);
        this.unavailable.emit();
      }
    } finally {
      this.loading.set(false);
    }
  }

  protected pick(suggestion: string, close: () => void): void {
    close();
    this.picked.emit(suggestion);
  }
}

import { Component, inject, input, output, signal } from '@angular/core';
import { HlmAlertDialogImports } from '@spartan-ng/helm/alert-dialog';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { firstValueFrom } from 'rxjs';
import { toApiError } from '@app/core/api/api-error';
import { InterviewsApi } from '@app/features/interviews/services/interviews-api';

@Component({
  selector: 'app-abandon-interview',
  imports: [HlmAlertDialogImports, HlmButtonImports],
  templateUrl: './abandon-interview.html',
})
export class AbandonInterview {
  readonly interviewId = input.required<string>();
  readonly abandoned = output();

  private readonly api = inject(InterviewsApi);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected async confirm(close: () => void): Promise<void> {
    if (this.busy()) {
      return;
    }
    this.error.set(null);
    this.busy.set(true);
    try {
      await firstValueFrom(this.api.abandon(this.interviewId()));
      close();
      this.abandoned.emit();
    } catch (err) {
      const error = toApiError(err);
      if (error.code === 'INTERVIEW_ALREADY_ENDED') {
        // Already over (completed, closed after 30 minutes idle, or abandoned in another tab): the
        // goal is reached, so carry on to the results as after a normal abandon.
        close();
        this.abandoned.emit();
        return;
      }
      this.error.set(error.message);
    } finally {
      this.busy.set(false);
    }
  }

  protected onOpenChange(): void {
    this.error.set(null);
  }
}

import { Component, computed, inject, linkedSignal, signal, viewChild } from '@angular/core';
import { form, submit } from '@angular/forms/signals';
import { Router, RouterLink } from '@angular/router';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { firstValueFrom } from 'rxjs';
import { toApiError } from '@app/core/api/api-error';
import { ConfirmsLeaving } from '@app/core/guards/leave-confirmation-guard';
import { PhaseModelOverrides } from './components/phase-model-overrides/phase-model-overrides';
import { InterviewsApi } from '@app/features/interviews/services/interviews-api';
import { ApplicationSummary } from '@app/features/applications/models/application-summary.schema';
import { describeInputRejection } from './models/input-rejection';
import { toCreateInterviewRequest } from './models/create-interview.request';
import {
  createInterviewValidation,
  initialCreateInterviewModel,
} from './models/create-interview.schema';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { HlmTooltipImports } from '@spartan-ng/helm/tooltip';
import { PreferencesStore } from '@app/features/preferences/services/preferences-store';
import { InterviewJobContext } from './components/interview-job-context/interview-job-context';
import { InterviewStructure } from './components/interview-structure/interview-structure';
import { InterviewPersona } from './components/interview-persona/interview-persona';
import { InterviewApplication } from './components/interview-application/interview-application';
import { InterviewDocuments } from './components/interview-documents/interview-documents';

@Component({
  selector: 'app-create-interview',
  imports: [
    RouterLink,
    PhaseModelOverrides,
    HlmButtonImports,
    HlmSkeleton,
    HlmTooltipImports,
    InterviewApplication,
    InterviewJobContext,
    InterviewStructure,
    InterviewPersona,
    InterviewDocuments,
  ],
  templateUrl: './create-interview.html',
  host: { '(window:beforeunload)': 'onBeforeUnload($event)' },
})
export class CreateInterview implements ConfirmsLeaving {
  protected readonly model = signal(initialCreateInterviewModel());
  protected readonly selectedApplication = signal<ApplicationSummary | null>(null);
  protected readonly interviewForm = form(this.model, createInterviewValidation);
  protected readonly validationSummary = computed(() => {
    const messages = new Set(
      this.interviewForm()
        .errorSummary()
        .map((error) => error.message)
        .filter((message): message is string => !!message),
    );
    return messages.size > 0 ? [...messages].join(' · ') : 'Some fields need attention.';
  });
  protected readonly submitError = signal<string | null>(null);
  private readonly documents = viewChild(InterviewDocuments);
  /** Documents are analyzed as soon as they are picked; starting waits for that to finish. */
  protected readonly analyzingDocuments = computed(() => this.documents()?.analyzing() ?? false);
  /** An upload that is still running would be left out of the interview, and orphaned. */
  protected readonly uploadingDocuments = computed(() => this.documents()?.uploading() ?? false);
  protected readonly documentsBusy = computed(
    () => this.analyzingDocuments() || this.uploadingDocuments(),
  );
  protected readonly submitDisabled = computed(
    () => this.interviewForm().invalid() || this.documentsBusy(),
  );
  protected readonly preferences = inject(PreferencesStore);
  /**
   * The form shows the Preferences defaults, so it first waits for them. If they can't be loaded it
   * is shown anyway, with a notice, as the server applies them whether or not they are shown. Once
   * shown it stays, so asking again doesn't discard what was entered.
   */
  protected readonly formShown = linkedSignal<boolean, boolean>({
    source: () => this.preferences.ready() || this.preferences.loadError() !== null,
    computation: (loaded, previous) => loaded || (previous?.value ?? false),
  });
  private readonly interviewsApi = inject(InterviewsApi);
  private readonly router = inject(Router);
  private readonly submitted = signal(false);

  leaveConfirmation(): string | null {
    return !this.submitted() && this.interviewForm().dirty()
      ? 'You have unsaved changes. Are you sure you want to leave?'
      : null;
  }

  protected onBeforeUnload(event: BeforeUnloadEvent): void {
    if (this.leaveConfirmation() !== null) {
      event.preventDefault();
    }
  }

  protected onSubmit(event: Event): void {
    event.preventDefault();
    if (this.documentsBusy()) {
      return;
    }
    this.submitError.set(null);
    void submit(this.interviewForm, async (form) => {
      const request = toCreateInterviewRequest(this.model());
      if (!request) {
        this.submitError.set('Some fields are invalid. Check the form and try again.');
        return undefined;
      }
      try {
        const interview = await firstValueFrom(this.interviewsApi.create(request));
        this.submitted.set(true);
        await this.router.navigate(['/interviews', interview.id]);
        return undefined;
      } catch (err) {
        const error = toApiError(err);
        if (error.code !== 'INPUT_REJECTED') {
          this.submitError.set(error.message);
          return undefined;
        }
        // Nothing was created and the input is kept: show why, on the field it is about.
        const rejection = describeInputRejection(error);
        const target = rejection.field ? form[rejection.field] : null;
        if (!target) {
          this.submitError.set(rejection.message);
          return undefined;
        }
        target().focusBoundControl();
        return { kind: 'inputRejected', message: rejection.message, fieldTree: target };
      }
    });
  }
}

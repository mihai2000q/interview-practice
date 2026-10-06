import { Component, computed, inject, input, linkedSignal, model } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FieldTree, FormField } from '@angular/forms/signals';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideChevronDown, lucideLayers } from '@ng-icons/lucide';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { HlmCollapsibleImports } from '@spartan-ng/helm/collapsible';
import { HlmFieldImports } from '@spartan-ng/helm/field';
import { HlmRadioGroupImports } from '@spartan-ng/helm/radio-group';
import { HlmSelectImports } from '@spartan-ng/helm/select';
import { ApplicationSummary } from '@app/features/applications/models/application-summary.schema';
import { ApplicationsApi } from '@app/features/applications/services/applications-api';
import { CreateInterviewModel } from '@app/features/interviews/pages/create-interview/models/create-interview.schema';

/** Standalone interview, the next stage of an existing application, or a new application. */
@Component({
  selector: 'app-interview-application',
  providers: [provideIcons({ lucideChevronDown, lucideLayers })],
  imports: [
    FormField,
    HlmCardImports,
    HlmCollapsibleImports,
    HlmFieldImports,
    HlmRadioGroupImports,
    HlmSelectImports,
    NgIcon,
  ],
  templateUrl: './interview-application.html',
})
export class InterviewApplication {
  readonly interviewForm = input.required<FieldTree<CreateInterviewModel>>();
  /**
   * The full ApplicationSummary behind `applicationId`. The form model only keeps the id; this holds
   * the values (names, documents) that get pre-filled and locked while it is set.
   */
  readonly selectedApplication = model<ApplicationSummary | null>(null);
  /** Expanded by the user, or by a failed submit that needs the application choice. */
  /** An invalid application choice, once touched, needs this card open so the error is seen. */
  private readonly needsAttention = computed(() => {
    const field = this.interviewForm().applicationId();
    return field.touched() && field.errors().length > 0;
  });
  /** Opened by the candidate, or by `needsAttention`; it then stays open. */
  protected readonly expanded = linkedSignal<boolean, boolean>({
    source: this.needsAttention,
    computation: (attention, previous) => attention || (previous?.value ?? false),
  });
  /** "Existing" has nothing to pick from while loading, on error, or with no applications. */
  protected readonly existingUnavailable = computed(
    () =>
      this.applications.isLoading() ||
      !!this.applications.error() ||
      (this.applications.value() ?? []).length === 0,
  );
  protected readonly existingHint = computed(() => {
    if (this.applications.isLoading()) {
      return 'Loading…';
    }
    if (this.applications.error()) {
      return 'Unavailable';
    }
    return (this.applications.value() ?? []).length === 0 ? 'No applications yet' : '';
  });
  protected readonly existing = computed(
    () => this.interviewForm().applicationMode().value() === 'existing',
  );
  protected readonly selectDisabled = computed(
    () =>
      this.applications.isLoading() ||
      !!this.applications.error() ||
      (this.applications.value() ?? []).length === 0,
  );
  protected readonly placeholder = computed(() => {
    if (this.applications.isLoading()) {
      return 'Loading…';
    }
    if (this.applications.error()) {
      return 'Unavailable';
    }
    return (this.applications.value() ?? []).length === 0
      ? 'No applications yet'
      : 'Select application...';
  });
  private readonly api = inject(ApplicationsApi);
  protected readonly applications = rxResource({ stream: () => this.api.list() });

  /** The company is optional: without one the label is just the job title. */
  protected readonly applicationLabel = (application: ApplicationSummary): string =>
    application.companyName
      ? `${application.companyName} — ${application.jobTitle}`
      : application.jobTitle;

  protected readonly applicationName = (id: unknown): string => {
    const application = (this.applications.value() ?? []).find((item) => item.id === id);
    return application ? this.applicationLabel(application) : '';
  };

  /** Leaving "existing" releases the application: the pre-filled values stay, unlocked. */
  protected onModeChange(mode: unknown): void {
    if (mode !== 'existing') {
      this.selectedApplication.set(null);
      this.interviewForm().applicationId().value.set(null);
    }
  }

  protected onApplicationChange(id: unknown): void {
    const application = (this.applications.value() ?? []).find((item) => item.id === id) ?? null;
    this.selectedApplication.set(application);
    const form = this.interviewForm();
    form.applicationId().value.set(application?.id ?? null);
    form.applicationId().markAsDirty();
    if (!application) {
      return;
    }
    form.jobTitle().value.set(application.jobTitle);
    form.seniority().value.set(application.seniority);
    form.companyName().value.set(application.companyName ?? '');
    form.jobDescriptionId().value.set(application.jobDescription?.id ?? null);
    form.cvId().value.set(application.cv?.id ?? null);
    form.coverLetterId().value.set(application.coverLetter?.id ?? null);
    form.jobTitle().markAsDirty();
    form.seniority().markAsDirty();
    form.companyName().markAsDirty();
    form.jobDescriptionId().markAsDirty();
    form.cvId().markAsDirty();
    form.coverLetterId().markAsDirty();
  }
}

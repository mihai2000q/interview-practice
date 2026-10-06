import { Component, computed, input, viewChildren } from '@angular/core';
import {
  ApplicationDocument,
  ApplicationSummary,
} from '@app/features/applications/models/application-summary';
import { FieldTree, FormField } from '@angular/forms/signals';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { HlmCard, HlmCardContent, HlmCardHeader, HlmCardTitle } from '@spartan-ng/helm/card';
import { HlmFieldGroup } from '@spartan-ng/helm/field';
import { CreateInterviewModel } from '@app/features/interviews/pages/create-interview/models/create-interview.schema';
import { DocumentPicker } from '../document-picker/document-picker';
import { lucideFileText } from '@ng-icons/lucide';

@Component({
  providers: [provideIcons({ lucideFileText })],
  imports: [
    FormField,
    HlmCard,
    HlmCardContent,
    HlmCardHeader,
    HlmCardTitle,
    HlmFieldGroup,
    NgIcon,
    DocumentPicker,
  ],
  selector: 'app-interview-documents',
  templateUrl: './interview-documents.html',
})
export class InterviewDocuments {
  readonly interviewForm = input.required<FieldTree<CreateInterviewModel>>();
  /** The selected Application, whose documents are pre-filled (and possibly not in the saved list). */
  readonly application = input<ApplicationSummary | null>(null);

  private readonly pickers = viewChildren(DocumentPicker);
  /** True while any of the three Documents is being analyzed. */
  readonly analyzing = computed(() => this.pickers().some((picker) => picker.analyzing()));
  /** True while any of the three files is still being sent. */
  readonly uploading = computed(() => this.pickers().some((picker) => picker.uploading()));

  /** The `jdAnalysis` override, which decides which model the documents' analysis must come from. */
  protected readonly analysisSettings = computed(
    () => this.interviewForm().phaseSettings().value().jdAnalysis,
  );
  protected readonly jobDescriptionDocs = computed(() =>
    this.asList(this.application()?.jobDescription),
  );
  protected readonly cvDocs = computed(() => this.asList(this.application()?.cv));
  protected readonly coverLetterDocs = computed(() => this.asList(this.application()?.coverLetter));

  private asList(document: ApplicationDocument | null | undefined): ApplicationDocument[] {
    return document ? [document] : [];
  }
}

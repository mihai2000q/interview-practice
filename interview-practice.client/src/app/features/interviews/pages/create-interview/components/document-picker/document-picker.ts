import {
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  input,
  model,
  signal,
  untracked,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { NgIcon, provideIcons } from '@ng-icons/core';
import { lucideFileText, lucideX } from '@ng-icons/lucide';
import { HlmAttachmentImports } from '@spartan-ng/helm/attachment';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmCheckboxImports } from '@spartan-ng/helm/checkbox';
import { HlmFieldImports } from '@spartan-ng/helm/field';
import { HlmSelectImports } from '@spartan-ng/helm/select';
import { firstValueFrom, Subscription } from 'rxjs';
import { toApiError } from '@app/core/api/api-error';
import { ApplicationDocument } from '@app/features/applications/models/application-summary';
import {
  AnalysisSettings,
  DocumentType,
  StoredDocument,
} from '@app/features/documents/models/document.schema';
import { DEFAULT_INTERVIEW_MODEL } from '@app/features/interviews/pages/create-interview/models/phase-settings.schema';
import { MAX_UPLOAD_MB } from '@app/features/documents/documents.constants';
import { DocumentsApi } from '@app/features/documents/services/documents-api';
import { FileDropzone } from '@app/shared/components/file-dropzone/file-dropzone';
import {
  DocumentAnalysisState,
  DocumentAnalysisStatus,
} from '../document-analysis-status/document-analysis-status';

let nextId = 0;

const SELECT_PLACEHOLDERS: Record<DocumentType, string> = {
  cv: 'Select existing CV...',
  cover_letter: 'Select existing letter...',
  job_description: 'Select existing description...',
};

/**
 * Select a saved Document, or upload a new PDF (click or drop). Once a file is uploaded here it
 * replaces the select and dropzone with an attachment and a "save for later" checkbox.
 * Binds to a form field as a `FormValueControl`.
 *
 * Whichever Document is chosen shows whether it has been analysed by the model the interview
 * will use (the `jdAnalysis` override, else the default): the server keeps one analysis per
 * Document and redoes it for another model. A freshly uploaded one is analysed by the client at
 * once, in the background; a saved or prefilled one, or one analysed by another model, is only
 * analysed when the candidate asks ("Analyze now"), because otherwise the server does it when
 * the interview is created, which takes longer. `analyzing` lets the page hold back submission while
 * an analysis runs. Removing the upload stops it; so does choosing something else. If the server
 * rejects an uploaded Document's content (422), it is deleted as if removed and the candidate is
 * asked for a different file; a rejected saved Document is kept and only reported. Any other
 * failure is on our side: the Document stays "not analyzed" and can be tried again.
 */
@Component({
  selector: 'app-document-picker',
  providers: [provideIcons({ lucideFileText, lucideX })],
  imports: [
    HlmAttachmentImports,
    HlmButtonImports,
    HlmCheckboxImports,
    HlmFieldImports,
    HlmSelectImports,
    DocumentAnalysisStatus,
    FileDropzone,
    NgIcon,
  ],
  templateUrl: './document-picker.html',
})
export class DocumentPicker {
  readonly type = input.required<DocumentType>();
  readonly label = input.required<string>();
  readonly value = model<string | null>(null);
  readonly disabled = input(false);
  readonly extraDocuments = input<ApplicationDocument[]>([]);
  /** The interview's `jdAnalysis` override: the analysis it will use, and what "Analyze now" runs. */
  readonly analysisSettings = input<AnalysisSettings | undefined>(undefined);

  protected readonly selectId = `document-picker-${nextId++}`;
  protected readonly uploading = signal(false);
  protected readonly uploadError = signal<string | null>(null);
  protected readonly uploadedDocument = signal<StoredDocument | null>(null);
  /** The Document being analysed right now. */
  private readonly analysisTarget = signal<string | null>(null);
  readonly analyzing = computed(() => this.analysisTarget() !== null);
  /** Models that analysed Documents in this session; the lists loaded earlier don't know yet. */
  private readonly analyzedModels = signal<ReadonlyMap<string, string>>(new Map());
  /** The model the interview will analyse with: the override, else the default. */
  protected readonly expectedModel = computed(
    () => this.analysisSettings()?.model ?? DEFAULT_INTERVIEW_MODEL,
  );
  /** The last attempt to analyse the chosen Document failed for a reason that isn't its own. */
  protected readonly analysisFailed = signal(false);
  /** Nothing to choose from (still loading, failed to load, or no saved documents yet). */
  protected readonly selectDisabled = computed(
    () =>
      this.disabled() ||
      this.savedDocuments.isLoading() ||
      !!this.savedDocuments.error() ||
      this.options().length === 0,
  );
  protected readonly placeholder = computed(() => {
    if (this.savedDocuments.isLoading()) {
      return 'Loading…';
    }
    if (this.savedDocuments.error()) {
      return 'Unavailable';
    }
    return this.options().length === 0 ? 'No saved documents' : SELECT_PLACEHOLDERS[this.type()];
  });
  private readonly documentsApi = inject(DocumentsApi);
  private analysisRequest: Subscription | null = null;
  protected readonly savedDocuments = rxResource({
    params: () => this.type(),
    stream: ({ params }) => this.documentsApi.list(params),
  });
  private readonly uploadedDocuments = signal<StoredDocument[]>([]);
  protected readonly options = computed(() => {
    const listed = this.savedDocuments.value() ?? [];
    const listedIds = new Set(listed.map((doc) => doc.id));
    return [
      ...this.extraDocuments().filter((doc) => !listedIds.has(doc.id)),
      ...this.uploadedDocuments().filter((doc) => !listedIds.has(doc.id)),
      ...listed,
    ];
  });

  private readonly selectedDocument = computed(() => {
    const id = this.value();
    return id ? (this.options().find((doc) => doc.id === id) ?? null) : null;
  });
  protected readonly analysisModel = computed(() => {
    const document = this.selectedDocument();
    return document ? (this.analyzedModels().get(document.id) ?? document.analysisModel) : null;
  });
  protected readonly analysisState = computed<DocumentAnalysisState | null>(() => {
    const document = this.selectedDocument();
    if (!document) {
      return null;
    }
    if (this.analysisTarget() === document.id) {
      return 'running';
    }
    const model = this.analysisModel();
    if (model === null) {
      return 'missing';
    }
    return model === this.expectedModel() ? 'done' : 'outdated';
  });

  protected reload(): void {
    this.savedDocuments.reload();
  }

  protected readonly documentName = (id: unknown): string =>
    this.options().find((doc) => doc.id === id)?.name ??
    (id ? 'Document from the application' : '');

  /** Clears the upload from the form and deletes the Document; not awaited, a failure is harmless. */
  protected removeUpload(): void {
    const document = this.uploadedDocument();
    this.value.set(null);
    if (document) {
      this.discardUpload(document);
    }
  }

  private discardUpload(document: StoredDocument): void {
    this.stopAnalysis();
    this.analysisFailed.set(false);
    this.uploadedDocument.set(null);
    this.uploadError.set(null);
    this.uploadedDocuments.update((list) => list.filter((doc) => doc.id !== document.id));
    this.documentsApi.delete(document.id).subscribe({
      next: () => this.savedDocuments.reload(),
      error: () => undefined,
    });
  }

  constructor() {
    inject(DestroyRef).onDestroy(() => this.analysisRequest?.unsubscribe());

    // Choosing something else clears the "couldn't be analyzed" message of the discarded file.
    effect(() => {
      if (this.value()) {
        untracked(() => this.uploadError.set(null));
      }
    });

    // Choosing another Document ends an analysis of the previous one.
    effect(() => {
      const id = this.value();
      untracked(() => {
        if (this.analysisTarget() !== id) {
          this.stopAnalysis();
        }
        this.analysisFailed.set(false);
      });
    });

    // Something else set a different Document (e.g. an Application's): the upload is replaced.
    effect(() => {
      const document = this.uploadedDocument();
      if (document && this.value() !== document.id) {
        untracked(() => this.discardUpload(document));
      }
    });
  }

  private stopAnalysis(): void {
    this.analysisRequest?.unsubscribe();
    this.analysisRequest = null;
    this.analysisTarget.set(null);
  }

  /** "Analyze now" on a Document that has no analysis yet. */
  protected analyzeSelected(): void {
    const document = this.selectedDocument();
    if (document && !this.analyzing()) {
      this.analyze(document.id);
    }
  }

  private analyze(documentId: string): void {
    this.stopAnalysis();
    this.analysisFailed.set(false);
    this.analysisTarget.set(documentId);
    this.analysisRequest = this.documentsApi
      .analyzeDocument(documentId, this.analysisSettings())
      .subscribe({
        next: (analysis) => {
          this.stopAnalysis();
          this.analyzedModels.update((models) => new Map(models).set(documentId, analysis.model));
        },
        error: (err: unknown) => {
          const error = toApiError(err);
          this.stopAnalysis();
          if (error.status !== 422 && error.code !== 'INPUT_REJECTED') {
            this.analysisFailed.set(true);
            return;
          }
          const reason = error.message.replace(/\.$/, '');
          const upload = this.uploadedDocument();
          if (upload?.id === documentId) {
            this.value.set(null);
            this.discardUpload(upload);
            this.uploadError.set(
              `This document couldn't be analyzed: ${reason}. Please upload a different file.`,
            );
          } else {
            this.uploadError.set(`This document couldn't be analyzed: ${reason}.`);
          }
        },
      });
  }

  protected async setSaved(saved: boolean): Promise<void> {
    const document = this.uploadedDocument();
    if (!document) {
      return;
    }
    try {
      const updated = await firstValueFrom(this.documentsApi.update(document.id, { saved }));
      this.uploadedDocument.set(updated);
      this.savedDocuments.reload();
    } catch (err) {
      this.uploadError.set(toApiError(err).message);
    }
  }

  /** The dropzone only hands over PDFs; the size limit is checked here. */
  protected async upload(file: File): Promise<void> {
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      this.uploadError.set(`The file is larger than ${MAX_UPLOAD_MB} MB.`);
      return;
    }

    this.uploadError.set(null);
    this.uploading.set(true);
    try {
      // A job description is usually specific to one role, so it isn't kept unless asked.
      const save = this.type() !== 'job_description';
      const document = await firstValueFrom(this.documentsApi.upload(file, this.type(), save));
      this.uploadedDocuments.update((list) => [document, ...list]);
      this.uploadedDocument.set(document);
      this.value.set(document.id);
      this.savedDocuments.reload();
      this.analyze(document.id);
    } catch (err) {
      this.uploadError.set(toApiError(err).message);
    } finally {
      this.uploading.set(false);
    }
  }
}

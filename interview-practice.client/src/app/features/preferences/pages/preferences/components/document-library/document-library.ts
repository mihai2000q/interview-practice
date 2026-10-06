import { DatePipe } from '@angular/common';
import { Component, computed, effect, ElementRef, inject, signal, viewChild } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  lucideCheck,
  lucideDownload,
  lucideFileText,
  lucidePencil,
  lucideTrash2,
  lucideX,
} from '@ng-icons/lucide';
import { toast } from '@spartan-ng/brain/sonner';
import { HlmAlertDialogImports } from '@spartan-ng/helm/alert-dialog';
import { HlmAttachmentImports } from '@spartan-ng/helm/attachment';
import { HlmButtonImports } from '@spartan-ng/helm/button';
import { HlmCardImports } from '@spartan-ng/helm/card';
import { HlmEmptyImports } from '@spartan-ng/helm/empty';
import { HlmInput } from '@spartan-ng/helm/input';
import { HlmSkeleton } from '@spartan-ng/helm/skeleton';
import { firstValueFrom, forkJoin, map } from 'rxjs';
import { toApiError } from '@app/core/api/api-error';
import { valueOrUndefined } from '@app/core/api/resource-value';
import { DOCUMENT_TYPES, MAX_UPLOAD_MB } from '@app/features/documents/documents.constants';
import { DocumentType, StoredDocument } from '@app/features/documents/models/document.schema';
import { DocumentsApi } from '@app/features/documents/services/documents-api';
import { FileDropzone } from '@app/shared/components/file-dropzone/file-dropzone';

const NAME_MAX_LENGTH = 200;

/**
 * The "Documents" tab: every saved CV, cover letter and job description, with the way to upload
 * another, rename one, get the original file back or delete one. This is the only place a
 * Document is managed; Create Interview just picks or uploads.
 */
@Component({
  selector: 'app-document-library',
  providers: [
    provideIcons({
      lucideCheck,
      lucideDownload,
      lucideFileText,
      lucidePencil,
      lucideTrash2,
      lucideX,
    }),
  ],
  imports: [
    DatePipe,
    FileDropzone,
    HlmAlertDialogImports,
    HlmAttachmentImports,
    HlmButtonImports,
    HlmCardImports,
    HlmEmptyImports,
    HlmInput,
    HlmSkeleton,
    NgIcon,
  ],
  templateUrl: './document-library.html',
})
export class DocumentLibrary {
  private readonly api = inject(DocumentsApi);
  private readonly documentsResource = rxResource({
    stream: () =>
      forkJoin(DOCUMENT_TYPES.map(({ value }) => this.api.list(value))).pipe(
        map((lists) => lists.flat()),
      ),
  });

  protected readonly types = DOCUMENT_TYPES;
  protected readonly nameMaxLength = NAME_MAX_LENGTH;
  protected readonly maxUploadMb = MAX_UPLOAD_MB;
  protected readonly downloadUrl = (id: string) => this.api.downloadUrl(id);

  private readonly documents = computed(() => valueOrUndefined(this.documentsResource));
  /** Loaded, split by type (newest first, as the server sends them). */
  protected readonly loaded = computed(() => {
    const documents = this.documents();
    return documents
      ? this.types.map((type) => ({
          ...type,
          documents: documents.filter((document) => document.type === type.value),
        }))
      : undefined;
  });
  protected readonly loadError = computed(() => {
    const error = this.documentsResource.error();
    return error ? toApiError(error).message : null;
  });

  /** The type being uploaded to, and why the last upload failed. */
  protected readonly uploading = signal<DocumentType | null>(null);
  protected readonly uploadError = signal<{ type: DocumentType; message: string } | null>(null);

  /** The Document being renamed, with the name typed so far. */
  protected readonly renaming = signal<{ id: string; name: string } | null>(null);
  protected readonly renamingSaving = signal(false);
  protected readonly renameError = signal<string | null>(null);
  protected readonly canRename = computed(() => {
    const renaming = this.renaming();
    return !!renaming && renaming.name.trim().length > 0 && !this.renamingSaving();
  });

  /** The Document the open confirmation is about; `null` while there is none. */
  protected readonly deleteTarget = signal<StoredDocument | null>(null);
  protected readonly deleting = signal(false);
  protected readonly deleteError = signal<string | null>(null);

  /** The rename field, while there is one: it takes focus as it appears. */
  private readonly renameInput = viewChild<ElementRef<HTMLInputElement>>('renameInput');

  constructor() {
    effect(() => this.renameInput()?.nativeElement.select());
  }

  protected retry(): void {
    this.documentsResource.reload();
  }

  /** The dropzone only hands over PDFs; the size limit is checked here. */
  protected async upload(type: DocumentType, file: File): Promise<void> {
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      this.uploadError.set({ type, message: `The file is larger than ${MAX_UPLOAD_MB} MB.` });
      return;
    }
    this.uploadError.set(null);
    this.uploading.set(type);
    try {
      const document = await firstValueFrom(this.api.upload(file, type, true));
      this.documentsResource.reload();
      toast.success(`Added “${document.name}”`);
    } catch (err) {
      this.uploadError.set({ type, message: toApiError(err).message });
    } finally {
      this.uploading.set(null);
    }
  }

  protected startRename(document: StoredDocument): void {
    this.renameError.set(null);
    this.renaming.set({ id: document.id, name: document.name });
  }

  protected typeName(event: Event): void {
    const name = (event.target as HTMLInputElement).value;
    this.renaming.update((renaming) => renaming && { ...renaming, name });
  }

  protected cancelRename(): void {
    this.renaming.set(null);
  }

  protected async confirmRename(): Promise<void> {
    const renaming = this.renaming();
    if (!renaming || !this.canRename()) {
      return;
    }
    this.renameError.set(null);
    this.renamingSaving.set(true);
    try {
      await firstValueFrom(this.api.update(renaming.id, { name: renaming.name.trim() }));
      this.renaming.set(null);
      this.documentsResource.reload();
    } catch (err) {
      this.renameError.set(toApiError(err).message);
    } finally {
      this.renamingSaving.set(false);
    }
  }

  protected askDelete(document: StoredDocument): void {
    this.deleteError.set(null);
    this.deleteTarget.set(document);
  }

  /** The dialog was dismissed (Escape, the backdrop, Cancel): forget the request, unless it is running. */
  protected onDialogState(state: 'open' | 'closed'): void {
    if (state === 'closed' && !this.deleting()) {
      this.deleteTarget.set(null);
    }
  }

  protected async confirmDelete(): Promise<void> {
    const document = this.deleteTarget();
    if (!document || this.deleting()) {
      return;
    }
    this.deleteError.set(null);
    this.deleting.set(true);
    try {
      await firstValueFrom(this.api.delete(document.id));
      this.deleteTarget.set(null);
      this.documentsResource.reload();
      toast.success(`Deleted “${document.name}”`);
    } catch (err) {
      this.deleteError.set(toApiError(err).message);
    } finally {
      this.deleting.set(false);
    }
  }

  protected analysisLabel(document: StoredDocument): string {
    return document.analysisModel ? `Analyzed with ${document.analysisModel}` : 'Not analyzed yet';
  }
}

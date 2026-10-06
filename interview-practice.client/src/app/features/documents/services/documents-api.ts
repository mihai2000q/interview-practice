import { HttpClient } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { map, Observable } from 'rxjs';
import { environment } from '@env/environment';
import { mapApiError } from '@app/core/api/api-error';
import {
  AnalysisSettings,
  DocumentAnalysis,
  documentAnalysisSchema,
  DocumentType,
  StoredDocument,
  storedDocumentListSchema,
  storedDocumentSchema,
} from '../models/document.schema';

@Service()
export class DocumentsApi {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/documents`;

  list(type: DocumentType): Observable<StoredDocument[]> {
    return this.http.get<unknown>(this.url, { params: { type } }).pipe(
      map((body) => storedDocumentListSchema.parse(body)),
      mapApiError(),
    );
  }

  upload(file: File, type: DocumentType, save: boolean): Observable<StoredDocument> {
    const body = new FormData();
    body.append('file', file);
    body.append('type', type);
    body.append('save', String(save));
    return this.http.post<unknown>(this.url, body).pipe(
      map((response) => storedDocumentSchema.parse(response)),
      mapApiError(),
    );
  }

  /** With the interview's `jdAnalysis` override the result is the one that interview will reuse. */
  analyzeDocument(id: string, settings?: AnalysisSettings): Observable<DocumentAnalysis> {
    return this.http.put<unknown>(`${this.url}/${id}/analysis`, settings ?? null).pipe(
      map((response) => documentAnalysisSchema.parse(response)),
      mapApiError(),
    );
  }

  /** Where the browser fetches the original file; a link's `href`, not an XHR. */
  downloadUrl(id: string): string {
    return `${this.url}/${id}/download`;
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}`).pipe(mapApiError());
  }

  /** Rename a Document and/or change whether it is kept in the library. */
  update(id: string, changes: { name?: string; saved?: boolean }): Observable<StoredDocument> {
    return this.http.patch<unknown>(`${this.url}/${id}`, changes).pipe(
      map((response) => storedDocumentSchema.parse(response)),
      mapApiError(),
    );
  }
}

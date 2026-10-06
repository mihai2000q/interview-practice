import { HttpClient } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { map, Observable } from 'rxjs';
import { environment } from '@env/environment';
import { mapApiError } from '@app/core/api/api-error';
import {
  ApplicationOverview,
  applicationOverviewSchema,
  ApplicationProgress,
  applicationProgressSchema,
} from '../models/application-overview.schema';
import {
  ApplicationSummary,
  applicationSummaryListSchema,
} from '../models/application-summary.schema';

@Service()
export class ApplicationsApi {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/applications`;

  list(): Observable<ApplicationSummary[]> {
    return this.http.get<unknown>(this.url).pipe(
      map((body) => applicationSummaryListSchema.parse(body)),
      mapApiError(),
    );
  }

  /** One Application with its stages and, once there is one, its progress summary. */
  get(id: string): Observable<ApplicationOverview> {
    return this.http.get<unknown>(`${this.url}/${id}`).pipe(
      map((body) => applicationOverviewSchema.parse(body)),
      mapApiError(),
    );
  }

  /**
   * Makes the progress summary if it is missing or outdated, from the Evaluations that exist
   * (ADR 0015); answers at once when it is current. `409 NOT_ENOUGH_STAGES` below two.
   */
  generateProgress(id: string): Observable<ApplicationProgress> {
    return this.http.put<unknown>(`${this.url}/${id}/progress`, null).pipe(
      map((body) => applicationProgressSchema.parse(body)),
      mapApiError(),
    );
  }

  /** Deletes the Application and every Interview under it, with their results. Irreversible. */
  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}`).pipe(mapApiError());
  }
}

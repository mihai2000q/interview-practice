import { HttpClient } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { map, Observable } from 'rxjs';
import { environment } from '@env/environment';
import { mapApiError } from '@app/core/api/api-error';
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

  /** Deletes the Application and every Interview under it, with their results. Irreversible. */
  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}`).pipe(mapApiError());
  }
}

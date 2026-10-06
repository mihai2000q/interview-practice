import { HttpClient } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import { mapApiError } from '@app/core/api/api-error';
import { ApplicationSummary } from '../models/application-summary';

@Service()
export class ApplicationsApi {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/applications`;

  list(): Observable<ApplicationSummary[]> {
    return this.http.get<ApplicationSummary[]>(this.url).pipe(mapApiError());
  }

  /** Deletes the Application and every Interview under it, with their results. Irreversible. */
  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}`).pipe(mapApiError());
  }
}

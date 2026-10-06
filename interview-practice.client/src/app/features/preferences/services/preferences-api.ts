import { HttpClient } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { map, Observable, timeout } from 'rxjs';
import { environment } from '@env/environment';
import { mapApiError } from '@app/core/api/api-error';
import { Preferences, PreferencesPatch, preferencesSchema } from '../models/preferences.schema';

/**
 * Reading the Preferences is one query, so an answer that takes this long is not coming. Create
 * Interview waits for it before showing its form, so a hung request has to turn into an error.
 */
const GET_TIMEOUT_MS = 10_000;

@Service()
export class PreferencesApi {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/preferences`;

  get(): Observable<Preferences> {
    return this.http.get<unknown>(this.url).pipe(
      timeout(GET_TIMEOUT_MS),
      map((body) => preferencesSchema.parse(body)),
      mapApiError(),
    );
  }

  /** Answers with the whole resource, as `get` does. */
  update(patch: PreferencesPatch): Observable<Preferences> {
    return this.http.patch<unknown>(this.url, patch).pipe(
      map((body) => preferencesSchema.parse(body)),
      mapApiError(),
    );
  }
}

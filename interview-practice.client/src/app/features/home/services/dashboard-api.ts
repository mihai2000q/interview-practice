import { HttpClient } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { map, Observable } from 'rxjs';
import { environment } from '@env/environment';
import { mapApiError } from '@app/core/api/api-error';
import { Dashboard, dashboardSchema } from '../models/dashboard.schema';

@Service()
export class DashboardApi {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/dashboard`;

  get(): Observable<Dashboard> {
    return this.http.get<unknown>(this.url).pipe(
      map((body) => dashboardSchema.parse(body)),
      mapApiError(),
    );
  }
}

// features/export/export-api.service.ts
// Feature-scoped service: trigger + poll export per §15.C

import { inject, Injectable } from '@angular/core';
import { interval, Observable, switchMap, takeWhile } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import { ExportRecord } from '@core/models/export-record.model';

@Injectable()
export class ExportApiService {
  private readonly api = inject(ApiClient);

  /** POST /api/v1/products/:id/export-xlsx — trigger async export job */
  trigger(productId: string): Observable<ExportRecord> {
    return this.api.post<ExportRecord>(`/products/${productId}/export-xlsx`, {}, {
      retryOn503: true,
    });
  }

  /** GET /api/v1/exports/:id — poll until ready or failed */
  poll(exportId: string): Observable<ExportRecord> {
    return interval(2000).pipe(
      switchMap(() => this.api.get<ExportRecord>(`/exports/${exportId}`)),
      takeWhile(record => record.status === 'processing', true),
    );
  }
}

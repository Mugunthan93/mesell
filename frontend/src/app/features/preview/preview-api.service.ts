// features/preview/preview-api.service.ts
// Feature-scoped service: GET /products/:id/preview per §13.C

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';

export interface PreviewData {
  readonly title: string;
  readonly price: number | null;
  readonly imageUrls: readonly string[];
  readonly firstVariant: Record<string, unknown> | null;
  readonly fullDescription: string | null;
}

@Injectable()
export class PreviewApiService {
  private readonly api = inject(ApiClient);

  getPreview(productId: string): Observable<PreviewData> {
    return this.api.get<PreviewData>(`/products/${productId}/preview`);
  }
}

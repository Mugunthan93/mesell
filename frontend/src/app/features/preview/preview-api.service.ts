// features/preview/preview-api.service.ts
// Feature-scoped service: GET /products/:id/preview per §13.C
// NOT providedIn: 'root' — scoped to PREVIEW_ROUTES providers[]

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';

/** Wire-format response from GET /api/v1/products/:id/preview */
export interface PreviewData {
  readonly title: string;
  readonly price: number;
  readonly image_urls: string[];
  readonly first_variant: string | null;
  readonly full_description: string | null;
  readonly quality_score: number | null;
  readonly category_path: string;
}

@Injectable()
export class PreviewApiService {
  private readonly api = inject(ApiClient);

  getPreview(productId: string): Observable<PreviewData> {
    return this.api.get<PreviewData>(`/products/${productId}/preview`);
  }
}

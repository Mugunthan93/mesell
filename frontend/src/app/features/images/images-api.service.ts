// features/images/images-api.service.ts
// Feature-scoped service: image upload + precheck polling per §12.C
// API contract: POST/GET /api/v1/products/:id/images, DELETE /api/v1/products/:id/images/:imageId

import { inject, Injectable } from '@angular/core';
import { interval, map, Observable, switchMap } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';

// API response shape per §12.C (snake_case matches backend wire format)
export interface ProductImage {
  readonly id: string;
  readonly product_id: string;
  readonly slot_index: 0 | 1 | 2 | 3;
  readonly status: 'pending' | 'processing' | 'ready' | 'failed';
  readonly gcs_url: string | null;
  readonly precheck_jsonb: {
    readonly is_jpeg: boolean | null;
    readonly color_space: string | null;
    readonly resolution_ok: boolean | null;
    readonly white_bg_ok: boolean | null;
    readonly watermark_pass: boolean | null;
  } | null;
  readonly uploaded_at: string;
}

interface GetImagesResponse {
  readonly images: ProductImage[];
}

@Injectable()
export class ImagesApiService {
  private readonly api = inject(ApiClient);

  /**
   * POST /api/v1/products/:id/images — multipart upload
   * retryOn503: true for GCS hiccups
   *
   * NOTE(postMultipart): ApiClient.postMultipart returns Observable<T> — it does NOT
   * use { reportProgress: true, observe: 'events' } so upload progress HttpEvents
   * are not emitted. ImagesComponent uses completion (not progress %) as the
   * upload-done signal. Upload % tracking requires a future http.request() upgrade.
   */
  uploadImage(
    productId: string,
    slotIndex: 0 | 1 | 2 | 3,
    file: Blob,
  ): Observable<ProductImage> {
    const formData = new FormData();
    formData.append('slot_index', String(slotIndex));
    formData.append('image', file);
    return this.api.postMultipart<ProductImage>(
      `/products/${productId}/images`,
      formData,
      { retryOn503: true },
    );
  }

  /**
   * GET /api/v1/products/:id/images every 2 s.
   * Completes when caller unsubscribes (takeUntil in the component).
   */
  pollImages(productId: string): Observable<ProductImage[]> {
    return interval(2000).pipe(
      switchMap(() =>
        this.api.get<GetImagesResponse>(`/products/${productId}/images`),
      ),
      map(res => res.images),
    );
  }

  /**
   * DELETE /api/v1/products/:id/images/:imageId — remove a slot image (204)
   */
  deleteImage(productId: string, imageId: string): Observable<void> {
    return this.api.delete<void>(`/products/${productId}/images/${imageId}`);
  }
}

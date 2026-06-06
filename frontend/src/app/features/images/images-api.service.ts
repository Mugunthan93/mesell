// features/images/images-api.service.ts
// Feature-scoped service: image upload + precheck polling per §12.C

import { inject, Injectable } from '@angular/core';
import { interval, Observable, switchMap, takeWhile } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import { ImagePrecheckResult } from '@shared/enums/image-precheck-result.enum';

export interface ProductImage {
  readonly id: string;
  readonly slotIndex: number;
  readonly status: ImagePrecheckResult;
  readonly url: string | null;
  readonly precheckResults: {
    readonly isJpeg: boolean;
    readonly colorSpaceOk: boolean;
    readonly resolutionOk: boolean;
    readonly whiteBgOk: boolean;
    readonly noWatermark: boolean;
  } | null;
}

@Injectable()
export class ImagesApiService {
  private readonly api = inject(ApiClient);

  /** POST /api/v1/products/:id/images — multipart upload */
  upload(productId: string, slotIndex: number, file: Blob): Observable<unknown> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('slotIndex', String(slotIndex));
    return this.api.postMultipart<unknown>(`/products/${productId}/images`, formData, {
      retryOn503: true,
    });
  }

  /** GET /api/v1/products/:id/images — poll until all statuses leave 'pending' */
  pollImages(productId: string): Observable<ProductImage[]> {
    return interval(2000).pipe(
      switchMap(() => this.api.get<ProductImage[]>(`/products/${productId}/images`)),
      takeWhile(
        images => images.some(img => img.status === 'pending' || img.status === 'processing'),
        true,
      ),
    );
  }
}

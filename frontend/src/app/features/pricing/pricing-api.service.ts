// features/pricing/pricing-api.service.ts
// Feature-scoped service: POST /products/:id/price-calc per §14.C

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import { PricingCalc } from '@core/models/pricing-calc.model';

export interface PriceCalcRequest {
  readonly mrp: number;
  readonly targetPayout?: number;
}

@Injectable()
export class PricingApiService {
  private readonly api = inject(ApiClient);

  calculate(productId: string, request: PriceCalcRequest): Observable<PricingCalc> {
    return this.api.post<PricingCalc>(`/products/${productId}/price-calc`, request);
  }
}

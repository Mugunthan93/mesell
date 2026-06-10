// features/pricing/pricing-api.service.ts
// Feature-scoped service: POST /products/:id/price-calc per §14.C
// NOT providedIn: 'root' — scoped to PRICING_ROUTES providers[]
//
// NOTE: core/models/pricing-calc.model.ts uses camelCase + different field set
// (commissionAmount, isPositive, productId) that does NOT match BACKEND §12 locked
// wire format. Feature-local PricingCalc defined here matches the actual API contract.
// TODO(cross-cutting): reconcile @core/models/pricing-calc.model.ts to snake_case wire format.

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';

/** Wire-format response from POST /api/v1/products/:id/price-calc */
export interface PricingCalc {
  readonly mrp: number;
  readonly commission: number;
  readonly commission_pct: number;
  readonly gst: number;
  readonly gst_pct: number;
  readonly platform_fee: number;
  readonly platform_fee_pct: number;
  readonly logistics_deduction: number;
  readonly seller_payout: number;
  readonly net_margin: number;
  readonly net_margin_pct: number;
}

@Injectable()
export class PricingApiService {
  private readonly api = inject(ApiClient);

  calculate(productId: string, mrp: number, targetPayout: number): Observable<PricingCalc> {
    return this.api.post<PricingCalc>(
      `/products/${productId}/price-calc`,
      { mrp, target_payout: targetPayout },
    );
  }
}

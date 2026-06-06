// core/models/pricing-calc.model.ts
// Pricing calculation response per BACKEND_ARCHITECTURE.md §12 (pricing module)

import { UUID } from '@core/auth/jwt-payload.model';

export interface PricingCalc {
  readonly productId: UUID;
  readonly mrp: number;
  readonly commissionPct: number;
  readonly commissionAmount: number;
  readonly gstPct: number;
  readonly gstAmount: number;
  readonly sellerPayout: number;
  readonly netMarginAmount: number;
  readonly netMarginPct: number;
  /** true if margin is above 0, false if at loss */
  readonly isPositive: boolean;
}

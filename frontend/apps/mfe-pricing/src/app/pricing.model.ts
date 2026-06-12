/**
 * pricing.model.ts — Wire-contract DTOs for POST /api/v1/products/{id}/price-calc (#25).
 *
 * R-W6-6 (Decimal wire-type, CONFIRMED 2026-06-12):
 *   Pydantic v2 + FastAPI serialise Python Decimal → JSON STRING by default.
 *   Backend has NO json_encoders / float coercion (grep confirmed, 2026-06-12).
 *   Therefore all monetary/pct fields in PriceCalcResponse are typed `string`.
 *   Parse for arithmetic: Number(res.profit) — for display use formatRupee(res.mrp).
 *   Flip to number only on evidence of a different serialised shape (R-W6-6 protocol).
 *
 * DECISION-1 (RULED 2026-06-11, MASTER_PLAN §7):
 *   Pricing is SERVER-CALC. PnlBreakdown + mock PriceCalcRequest{mrp, target_margin}
 *   are DEAD. computePnlBreakdown / COMMISSION_PCT / GST_PCT are DEAD.
 *   Any local-math fallback = AUTO-REJECT.
 */

// ─── Request ──────────────────────────────────────────────────────────────────

/**
 * Body for POST /api/v1/products/{id}/price-calc (endpoint #25).
 * Pydantic accepts both JSON string and number for Decimal fields; sending as string
 * avoids IEEE-754 float rounding (e.g. 299.99 → "299.99" preserves 2dp precision).
 * V1.5 overrides (override_commission_pct / override_gst_pct) are omitted — backend
 * extra="forbid" accepts their absence (optional fields with defaults).
 */
export interface PriceCalcRequest {
  /** COGS per unit, INR (gt 0, 2dp). Replaces the retired FE-input `mrp`. */
  input_cost: string;
  /** Desired profit margin as % of input_cost (ge 0, le 500, 2dp). Default 30. */
  target_margin_pct: string;
}

// ─── Alert ────────────────────────────────────────────────────────────────────

/** Severity literal for server-issued pricing alerts. */
export type AlertSeverity = 'warning' | 'info';

/** Alert code literal — matches backend Literal["LOW_MARGIN", "HIGH_MRP_MULTIPLIER", "THIN_PROFIT"]. */
export type AlertCode = 'LOW_MARGIN' | 'HIGH_MRP_MULTIPLIER' | 'THIN_PROFIT';

/**
 * PriceCalcAlert — wire shape from PriceCalcResponse.alerts[].
 * message_id is a validation_message_id key (spec §5A.H) resolved client-side.
 * transloco is NOT wired in V1 (Wave-2B drop) — render via ALERT_MESSAGES map or raw key.
 * i18n chore deferred to post-Wave-D.
 */
export interface PriceCalcAlert {
  code: AlertCode;
  /** Stable i18n key (e.g. "pricing.low_margin") — render via ALERT_MESSAGES. */
  message_id: string;
  severity: AlertSeverity;
}

// ─── Response ────────────────────────────────────────────────────────────────

/**
 * 200-OK body for POST /api/v1/products/{id}/price-calc.
 *
 * ALL monetary / pct fields are Decimal-serialised as JSON strings (R-W6-6 confirmed).
 * Parse with Number() for arithmetic comparisons. Use formatRupee(field) for display.
 * MRP is a SERVER-COMPUTED output — it was a FE input in the retired mock.
 */
export interface PriceCalcResponse {
  /** Server-computed MRP (selling price), INR. Was a FE input — now a RESULT. */
  mrp: string;
  /** Meesho net price (after Meesho's share). */
  meesho_price: string;
  /** Seller payout (what the seller actually receives). */
  seller_price: string;
  /** Commission rate resolved from category commission table (NOT hardcoded). */
  commission_pct: string;
  /** Commission amount, INR (was commission_amt in retired PnlBreakdown). */
  commission_amount: string;
  /** GST rate resolved from category table (NOT hardcoded). */
  gst_pct: string;
  /** GST amount, INR (was gst_amt in retired PnlBreakdown). */
  gst_amount: string;
  /** Profit, INR (was net_margin in retired PnlBreakdown). Positive = profitable. */
  profit: string;
  /** Profit as % of input_cost (was net_margin_pct in retired PnlBreakdown). */
  profit_pct: string;
  /** Server-issued pricing alerts (LOW_MARGIN / HIGH_MRP_MULTIPLIER / THIN_PROFIT). */
  alerts: PriceCalcAlert[];
  /** ISO-8601 datetime string of when this calculation was performed. */
  calculated_at: string;
}

// ─── Typed error surfaces ─────────────────────────────────────────────────────

/**
 * 404: flag off (FEATURE_PRICE_CALCULATOR_ENABLED=false) OR product not found / cross-tenant.
 * The breakdown stays null; component renders "Price Calculator unavailable" banner.
 * NO local-math fallback (DECISION-1 + R-W6-1).
 */
export interface PriceCalcUnavailableError {
  kind: 'unavailable';
  /** 'flag_off' when FEATURE_PRICE_CALCULATOR_ENABLED=false; 'not_found' otherwise. */
  reason: 'flag_off' | 'not_found';
}

/**
 * 422: pricing.commission.missing — category has no usable commission rate.
 * Component renders "Pricing isn't available for this category yet" + detail.
 */
export interface PriceCalcCommissionMissingError {
  kind: 'commission_missing';
  detail: string;
  error_code: string;
}

/**
 * 400: validation.price.invalid_input — Pydantic constraint violation (e.g. input_cost<=0).
 * The form validators should prevent most; surface if server returns 400.
 */
export interface PriceCalcValidationError {
  kind: 'validation';
  detail: string;
}

/** Union of typed non-throwing error shapes emitted by PricingApiService.calc(). */
export type PriceCalcErrorShape =
  | PriceCalcUnavailableError
  | PriceCalcCommissionMissingError
  | PriceCalcValidationError;

// ─── i18n: static alert message map (transloco not wired — Wave-2B drop) ─────

/**
 * Static fallback for PriceCalcAlert.message_id resolution.
 * transloco chore deferred to post-Wave-D. Do NOT invent arbitrary copy.
 * Component renders: ALERT_MESSAGES[alert.message_id] ?? alert.message_id.
 */
export const ALERT_MESSAGES: Record<string, string> = {
  'pricing.low_margin':          'Low margin — consider adjusting your cost or margin target.',
  'pricing.high_mrp_multiplier': 'MRP seems high relative to input cost.',
  'pricing.thin_profit':         'Thin profit — shipping and returns may reduce profitability.',
};

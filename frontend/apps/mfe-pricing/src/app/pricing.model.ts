/**
 * pricing.model.ts — Wire-contract DTOs for POST /api/v1/products/{id}/price-calc.
 *
 * W3 TOTAL REWRITE (2026-06-19): binds EXACTLY to W2 §2.1/§2.2 census-confirmed contract.
 * SUPERSEDES the wrong DECISION-1 "server-calc P&L" model (open PR #287 base) which
 * deducted FULL shipping from seller and used fabricated logistics/fixed/rto fees.
 *
 * R-W6-6 (Decimal wire-type, CONFIRMED 2026-06-12 + W2 §2.2):
 *   Pydantic v2 + FastAPI serialise Python Decimal → JSON STRING by default.
 *   All monetary/pct fields in PriceCalcResponse are typed `string`.
 *   Parse for arithmetic: Number(res.estimated_bank_settlement).
 *   Use formatRupee(res.estimated_bank_settlement) for display (2dp paise precision).
 *
 * GREP GATE — DEAD tokens (zero occurrences in this file, per W3 §4.2):
 *   mrp, meesho_price, seller_price, commission_amount, gst_pct, gst_amount,
 *   profit, profit_pct, input_cost, target_margin_pct, override_*, wdrp,
 *   logistics_fee, fixed_fee, rto, return_rate_pct, net_profit, output_gst, landed_cost,
 *   LOW_MARGIN, HIGH_MRP_MULTIPLIER, THIN_PROFIT, commission_missing.
 */

// ─── Request ──────────────────────────────────────────────────────────────────

/**
 * Body for POST /api/v1/products/{id}/price-calc (W2 §2.1).
 *
 * Backend schema has `extra="forbid"` — any field not in this interface causes a 422.
 * Do NOT add category, any override_* field, meesho_price, input_cost. Backend resolves
 * the category leaf server-side from the product's stored category_id.
 *
 * `selling_price` sent as Decimal string to avoid IEEE-754 float rounding
 * (e.g. 299.99 → "299.99" preserves 2dp; Pydantic Decimal gt=0, decimal_places=2).
 *
 * `commission_pct` is OPTIONAL — omit the key when not overriding; do NOT send `""`.
 * Backend defaults to 0 (commission is 0% for all 3,772 categories per census 2026-06-19).
 */
export interface PriceCalcRequest {
  /** Listed Meesho selling price, INR (gt 0, 2dp). Primary input — backend resolves shipping from product category. */
  selling_price: string;
  /** Commission override %, optional (ge 0, le 100, 2dp). Omit key entirely to use backend default (0). */
  commission_pct?: string;
}

// ─── Alert ────────────────────────────────────────────────────────────────────

/** Severity literal for server-issued pricing alerts (W2 §2.2). */
export type AlertSeverity = 'warning';

/**
 * Alert code literal — matches backend `Literal["NEGATIVE_SETTLEMENT"]` (W2 §1.1).
 * V1 ships ONE alert code. The previous LOW_MARGIN / HIGH_MRP_MULTIPLIER / THIN_PROFIT are DEAD.
 */
export type AlertCode = 'NEGATIVE_SETTLEMENT';

/**
 * PriceCalcAlert — wire shape from PriceCalcResponse.alerts[] (W2 §2.2).
 * 0 or 1 alerts — NEGATIVE_SETTLEMENT fires when estimated_bank_settlement < 0.
 * `message_id` is a stable i18n key resolved client-side via ALERT_MESSAGES.
 * transloco is NOT wired in V1 (Wave-2B drop) — render via ALERT_MESSAGES map or raw key.
 */
export interface PriceCalcAlert {
  code: AlertCode;
  /** Stable i18n key e.g. "pricing.alert.negative_settlement" — render via ALERT_MESSAGES. */
  message_id: string;
  severity: AlertSeverity;
}

// ─── Response ─────────────────────────────────────────────────────────────────

/**
 * 200-OK body for POST /api/v1/products/{id}/price-calc (W2 §2.2 — THE contract W3 binds to).
 *
 * ALL monetary / pct fields are Decimal-serialised as JSON strings (R-W6-6).
 * Parse with Number() for arithmetic. Use formatRupee(field) for display (2dp).
 *
 * Confirmed settlement formula (verified on 3,772 categories + founder real-order ₹61.78):
 *   shipping        = pricing_lookup.get_shipping(meesho_leaf_id)   // per-category constant
 *   commission_fees = commission_pct × selling_price                 // rounded 2dp ROUND_HALF_UP
 *   total_price     = selling_price + shipping
 *   gst_on_shipping = 0.18 × shipping                               // rounded 2dp
 *   tds             = 0.001 × total_price                           // rounded 2dp
 *   tcs             = 0 (always)
 *   estimated_bank_settlement = selling_price − commission_fees − gst_on_shipping − tds − tcs
 *   Real-order proof: selling 70, shipping 45 → gst 8.10, tds 0.12 → settlement 61.78 ✓
 *
 * UI row mapping (W3 §2.2 — 5 visible rows + disclaimer):
 *   selling_price            → "Selling price" row (echo of input)
 *   commission_fees          → "Commission fee ({commission_pct}%)" row
 *   gst_on_shipping          → "GST" deduction row (18% of shipping; seller's real cost)
 *   tds                      → "TDS" deduction row
 *   estimated_bank_settlement → "Estimated Bank Settlement" HEADLINE
 *   tcs                      → always "0.00", NOT rendered as a row
 *   shipping / total_price   → optional muted context line, NOT a deduction row
 *   disclaimer               → muted fine-print below headline (render server-sent literal)
 */
export interface PriceCalcResponse {
  /** Echo of selling_price from the request. */
  selling_price: string;
  /** Per-category shipping constant from pricing lookup (buyer-paid pass-through). */
  shipping: string;
  /** selling_price + shipping (total billed to buyer). */
  total_price: string;
  /** Commission rate applied — override or backend default (0). */
  commission_pct: string;
  /** commission_pct × selling_price, rounded 2dp ROUND_HALF_UP. */
  commission_fees: string;
  /** 0.18 × shipping, rounded 2dp ROUND_HALF_UP (the seller's actual shipping cost). */
  gst_on_shipping: string;
  /** 0.001 × total_price, rounded 2dp ROUND_HALF_UP. */
  tds: string;
  /** Always "0.00" in V1. Returned by contract; NOT rendered as a UI row. */
  tcs: string;
  /** HEADLINE: selling_price − commission_fees − gst_on_shipping − tds − tcs. May be negative (→ NEGATIVE_SETTLEMENT alert). */
  estimated_bank_settlement: string;
  /**
   * Verbatim Meesho disclaimer (server-sent literal — render `response.disclaimer` directly;
   * do NOT hardcode a second copy in the template). Displayed as muted fine-print below headline.
   * Text: "Bank settlement amount may vary slightly based on the quantity in the order,
   * Meesho commission policy at the time of the order and the actual weight of the product
   * as calculated by our third party delivery partner."
   */
  disclaimer: string;
  /** 0 or 1 alerts. NEGATIVE_SETTLEMENT fires when estimated_bank_settlement < 0. */
  alerts: PriceCalcAlert[];
  /** ISO-8601 datetime string of when this calculation was performed on the server. */
  calculated_at: string;
}

// ─── Typed error surfaces ──────────────────────────────────────────────────────

/**
 * 404: flag off (FEATURE_PRICE_CALCULATOR_ENABLED=false) OR product not found / cross-tenant.
 * Component renders "Price Calculator unavailable" banner.
 * NO local-math fallback ever (DECISION-1 + R-W6-1).
 */
export interface PriceCalcUnavailableError {
  kind: 'unavailable';
  /** 'flag_off' when FEATURE_PRICE_CALCULATOR_ENABLED=false; 'not_found' otherwise. */
  reason: 'flag_off' | 'not_found';
}

/**
 * 422 with error_code "pricing.category.no_pricing_data":
 * the product's category leaf is absent from the pricing lookup data file.
 * Component renders "Pricing isn't available for this category yet" inline message.
 * REPLACES the retired PriceCalcCommissionMissingError (pricing.commission.missing is DEAD).
 */
export interface PriceCalcNoPricingDataError {
  kind: 'no_pricing_data';
  detail: string;
  error_code: string;
}

/**
 * 400 / 422 Pydantic body validation (e.g. selling_price <= 0, or stale extra field with extra="forbid"):
 * Disambiguated from no_pricing_data by the absence of the pricing.category.no_pricing_data error_code.
 * Component renders inline field error near the input.
 */
export interface PriceCalcValidationError {
  kind: 'validation';
  detail: string;
}

/**
 * 5xx or network/non-HTTP error (spec §3.1 degradation matrix).
 * Emitted instead of bare EMPTY so the component can surface an explicit error banner
 * and retry affordance (spec §3.1 mandates "5xx → explicit error + retry affordance").
 * 401 is intentionally NOT mapped here; stays EMPTY (refreshInterceptor/logout owns it).
 */
export interface PriceCalcServerError {
  kind: 'server_error';
}

/** Union of typed non-throwing error shapes emitted by PricingApiService.calc(). */
export type PriceCalcErrorShape =
  | PriceCalcUnavailableError
  | PriceCalcNoPricingDataError
  | PriceCalcValidationError
  | PriceCalcServerError;

// ─── i18n: static alert message map (transloco not wired — Wave-2B drop) ──────

/**
 * Static fallback for PriceCalcAlert.message_id resolution.
 * transloco chore deferred to post-Wave-D. Do NOT invent arbitrary copy.
 * Component renders: ALERT_MESSAGES[alert.message_id] ?? alert.message_id.
 *
 * KEY "pricing.alert.negative_settlement" must match the `message_id` W2 emits.
 * Coordinate with backend if the key name differs — the validation.generic.missing
 * class of bug (master memory 2026-06-17) will render blank if keys diverge.
 */
export const ALERT_MESSAGES: Record<string, string> = {
  'pricing.alert.negative_settlement':
    'This selling price results in a negative settlement — the fees exceed your price.',
};

/**
 * pricing.model.ts — Wire-contract DTOs for POST /api/v1/products/{id}/price-calc.
 *
 * SOURCE OF TRUTH: backend/app/modules/pricing/schemas.py (§12.M amendment 2026-06-18,
 * PR #285, commit fd4331d). Field names confirmed by direct schema inspection.
 *
 * R-W6-6 (Decimal wire-type, CONFIRMED 2026-06-12 / §12.M upheld):
 *   Pydantic v2 + FastAPI serialise Python Decimal → JSON STRING by default.
 *   Backend has NO json_encoders / float coercion.
 *   Therefore ALL monetary/pct fields in request and response are typed `string`.
 *   Parse for arithmetic: parseDecimal() from pricing.utils.ts
 *   Display: formatRupee() from pricing.utils.ts
 *   These helpers are KEPT (pure display/arithmetic — no local P&L math, DECISION-1).
 *
 * DECISION-1 (RULED 2026-06-11, §12.M 2026-06-18):
 *   Pricing is SERVER-CALC — FORWARD estimator mode.
 *   Seller enters meesho_price (the listed price); backend returns estimated_payout.
 *   target_margin_pct is DEAD (removed in §12.M). computePnlBreakdown / local math = DEAD.
 *   Any local-math fallback = AUTO-REJECT.
 *
 * §12.M (4): 422 pricing.commission.missing path REMOVED. Commission is now a
 *   seller-entered input (default 4%). PriceCalcCommissionMissingError DELETED.
 */

// ─── Request ──────────────────────────────────────────────────────────────────

/**
 * Body for POST /api/v1/products/{id}/price-calc (§12.M forward estimator).
 *
 * Primary inputs: meesho_price + input_cost (both required, gt 0).
 * Seller-entered estimator inputs: commission_pct (default "4"), return_rate_pct (default "0").
 * Optional display reference: mrp (struck-through; does NOT drive payout).
 * Optional per-request overrides: override_shipping / _logistics_fee / _fixed_fee /
 *   _gst_pct / _tcs_pct / _tds_pct (all nullable).
 *
 * Sending as Decimal strings avoids IEEE-754 float rounding (R-W6-6).
 * Backend extra="forbid" — only known fields accepted; omitted optional fields are fine.
 */
export interface PriceCalcRequest {
  /** Listed/selling price on Meesho, INR (gt 0, 2dp) — primary payout driver. */
  meesho_price: string;
  /** Cost of goods per unit, INR (gt 0, 2dp) — drives profit + markup. */
  input_cost: string;
  /** Meesho referral commission %, seller-entered (default "4", ge 0, le 100, 2dp). */
  commission_pct?: string;
  /** Expected return rate %, drives RTO expected-loss term (default "0", ge 0, le 100, 2dp). */
  return_rate_pct?: string;
  /** Struck-through reference price (display-only; does NOT drive payout, optional). */
  mrp?: string;
  /** Override bracketed shipping charge (INR, ge 0, 2dp). */
  override_shipping?: string;
  /** Override logistics fee (INR, ge 0, 2dp). */
  override_logistics_fee?: string;
  /** Override fixed/closing fee (INR, ge 0, 2dp). */
  override_fixed_fee?: string;
  /** Override GST % applied to fees (ge 0, le 100, 2dp). */
  override_gst_pct?: string;
  /** Override TCS % (ge 0, le 100, 2dp). */
  override_tcs_pct?: string;
  /** Override TDS % (ge 0, le 100, 2dp). */
  override_tds_pct?: string;
}

// ─── Alert ────────────────────────────────────────────────────────────────────

/** Severity literal for server-issued pricing alerts. */
export type AlertSeverity = 'warning' | 'info';

/**
 * Alert code literal — matches backend Literal["NEGATIVE_PAYOUT", "LOW_MARGIN", "SHIPPING_DOMINATES"].
 * §12.M (3): HIGH_MRP_MULTIPLIER + THIN_PROFIT are DEAD; replaced by NEGATIVE_PAYOUT + SHIPPING_DOMINATES.
 */
export type AlertCode = 'NEGATIVE_PAYOUT' | 'LOW_MARGIN' | 'SHIPPING_DOMINATES';

/**
 * PriceCalcAlert — wire shape from PriceCalcResponse.alerts[].
 * message_id is a validation_message_id key (spec §5A.H) resolved client-side via ALERT_MESSAGES.
 */
export interface PriceCalcAlert {
  code: AlertCode;
  /** Stable i18n key (e.g. "pricing.alert.negative_payout") — resolved via ALERT_MESSAGES. */
  message_id: string;
  severity: AlertSeverity;
}

// ─── Response ─────────────────────────────────────────────────────────────────

/**
 * 200-OK body for POST /api/v1/products/{id}/price-calc (§12.M forward estimator).
 *
 * ALL monetary / pct fields are Decimal-serialised as JSON strings (R-W6-6 confirmed).
 * Parse with parseDecimal() for arithmetic. Use formatRupee() for display.
 *
 * A negative estimated_payout does NOT cause a 4xx — it returns 200 with
 * a NEGATIVE_PAYOUT alert (§12.M (4)).
 *
 * Field layout mirrors backend PriceCalcResponse exactly (schemas.py §12.M):
 *   3-price model → mrp (nullable), meesho_price, wdrp_price
 *   Seller cost echo → input_cost
 *   Deduction breakdown → commission_pct, referral_commission, shipping_charge,
 *     logistics_fee, fixed_fee, gst_pct, gst_on_fees, tcs, tds,
 *     return_rate_pct, rto_expected_loss, total_deductions
 *   Outputs → estimated_payout, estimated_payout_wdrp, profit, margin_pct, markup_pct
 */
export interface PriceCalcResponse {
  // ── 3-price model ───────────────────────────────────────────────────────
  /** Struck-through reference price (echoed from request; null if not provided). */
  mrp: string | null;
  /** Listed/selling price on Meesho, INR. */
  meesho_price: string;
  /** Wrong/Defective Return Price = meesho_price minus WDRP_DELTA. */
  wdrp_price: string;

  // ── Seller cost (echo) ──────────────────────────────────────────────────
  /** Cost of goods per unit, INR (echoed from request). */
  input_cost: string;

  // ── Deduction breakdown ─────────────────────────────────────────────────
  /** Referral commission rate %. */
  commission_pct: string;
  /** Referral commission amount, INR. */
  referral_commission: string;
  /** Bracketed shipping charge, INR. */
  shipping_charge: string;
  /** Logistics fee, INR. */
  logistics_fee: string;
  /** Fixed/closing fee, INR. */
  fixed_fee: string;
  /** GST % applied to fees. */
  gst_pct: string;
  /** GST on fees, INR. */
  gst_on_fees: string;
  /** TCS amount, INR. */
  tcs: string;
  /** TDS amount, INR. */
  tds: string;
  /** Expected return rate %. */
  return_rate_pct: string;
  /** RTO expected loss, INR (return_rate x wdrp deduction). */
  rto_expected_loss: string;
  /** Sum of all deductions, INR. */
  total_deductions: string;

  // ── Outputs ─────────────────────────────────────────────────────────────
  /** Net payout to seller at meesho_price, INR. May be negative (NEGATIVE_PAYOUT alert). */
  estimated_payout: string;
  /** Net payout at wdrp_price (worst-case return scenario), INR. */
  estimated_payout_wdrp: string;
  /** Profit = estimated_payout minus input_cost, INR. */
  profit: string;
  /** Profit as % of meesho_price. */
  margin_pct: string;
  /** Profit as % of input_cost. */
  markup_pct: string;

  /** Server-issued pricing alerts. */
  alerts: PriceCalcAlert[];
  /** ISO-8601 datetime string of when this calculation was performed. */
  calculated_at: string;
}

// ─── Typed error surfaces ─────────────────────────────────────────────────────

/**
 * 404: flag off (FEATURE_PRICE_CALCULATOR_ENABLED=false) OR product not found / cross-tenant.
 * The breakdown stays null; component renders "Price Calculator unavailable" banner.
 * NO local-math fallback (DECISION-1).
 */
export interface PriceCalcUnavailableError {
  kind: 'unavailable';
  /** 'flag_off' when FEATURE_PRICE_CALCULATOR_ENABLED=false; 'not_found' for cross-tenant/404. */
  reason: 'flag_off' | 'not_found';
}

/**
 * 400: validation.price.invalid_input — Pydantic constraint violation (meesho_price<=0, etc.).
 * Form validators prevent most; surface if server returns 400.
 * §12.M: 422 commission.missing is DEAD — this is the only non-200 business error now.
 */
export interface PriceCalcValidationError {
  kind: 'validation';
  detail: string;
}

/**
 * 5xx or network/non-HTTP error (spec §3.1 degradation matrix).
 * Emitted instead of bare EMPTY so the component can surface an explicit error banner
 * and retry affordance — Spec §3.1 mandates "5xx → explicit error + retry affordance".
 * 401 is intentionally NOT mapped here; it stays EMPTY (refreshInterceptor/logout owns it).
 */
export interface PriceCalcServerError {
  kind: 'server_error';
}

/**
 * Union of typed non-throwing error shapes emitted by PricingApiService.calc().
 * §12.M: PriceCalcCommissionMissingError DELETED (422 path removed in §12.M (4)).
 */
export type PriceCalcErrorShape =
  | PriceCalcUnavailableError
  | PriceCalcValidationError
  | PriceCalcServerError;

// ─── i18n: static alert message map ──────────────────────────────────────────

/**
 * FE-local fallback for PriceCalcAlert.message_id resolution.
 * Backend en.json is missing these keys (§12.M alert codes not yet seeded in i18n).
 * Component renders: ALERT_MESSAGES[alert.message_id] ?? alert.message_id.
 *
 * Keys mirror backend message_ids per §5A.H convention:
 *   pricing.alert.negative_payout / pricing.alert.low_margin / pricing.alert.shipping_dominates
 *
 * §12.M DEAD keys: pricing.low_margin / pricing.high_mrp_multiplier / pricing.thin_profit REMOVED.
 */
export const ALERT_MESSAGES: Record<string, string> = {
  'pricing.alert.negative_payout':    "You'd lose money at this price — your payout is below zero.",
  'pricing.alert.low_margin':         'Low margin — under 10%. Consider raising the price or cutting cost.',
  'pricing.alert.shipping_dominates': 'Shipping is eating your margin — common on low-priced items.',
};

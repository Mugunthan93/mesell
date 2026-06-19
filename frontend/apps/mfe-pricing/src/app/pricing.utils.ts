/**
 * pricing.utils.ts — Display helpers for the pricing MFE.
 *
 * W3 UPDATE (2026-06-19): formatRupee upgraded to 2dp paise precision.
 * Reason: estimated_bank_settlement is ₹61.78 (proven real-order anchor) —
 * rounding to whole rupees would hide the paise the model is confirmed to produce.
 *
 * RETIRED (DECISION-1 + R-W6-1, ruled 2026-06-11):
 *   computePnlBreakdown — server computes settlement; client math is DEAD.
 *   COMMISSION_PCT, GST_PCT — server resolves from category lookup (NOT hardcoded).
 *   Any re-introduction of client math = AUTO-REJECT at merge gate.
 *
 * SURVIVORS + ADDITIONS:
 *   parseDecimal — convert Decimal strings from server to number for arithmetic.
 *   formatRupee  — 2dp paise precision (CHANGED from whole-rupee rounding).
 *   formatPct    — NEW: formats a commission_pct string/number as "x%" for row labels.
 */

/**
 * Convert a Decimal-string (or number) from the server to a JavaScript number.
 * Used for arithmetic comparisons (e.g. estimated_bank_settlement < 0 for alert state).
 * Returns 0 on NaN guard (defensive; should not occur with valid W2 server responses).
 */
export function parseDecimal(value: string | number): number {
  const n = typeof value === 'number' ? value : parseFloat(value);
  return isNaN(n) ? 0 : n;
}

/**
 * Format a Rupee amount for display in the settlement breakdown card.
 * Accepts both string Decimal (from server wire, R-W6-6) and number (for zero / static values).
 *
 * W3 CHANGE: shows 2 decimal places (paise precision) — NOT whole-rupee rounding.
 * The estimated_bank_settlement is ₹61.78 and must display to the paise to match
 * the Meesho portal breakdown the seller already knows.
 *
 * Examples:
 *   "61.78"  → "₹61.78"
 *   "70.00"  → "₹70.00"
 *   "8.10"   → "₹8.10"
 *   "1000.00"→ "₹1,000.00"  (en-IN locale comma separator + 2dp)
 *   "-5.00"  → "₹-5.00"    (negative settlement — component styles this as warning)
 *   0        → "₹0.00"
 */
export function formatRupee(amount: string | number): string {
  const n = parseDecimal(amount);
  return `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Format a commission percentage for row labels in the breakdown card.
 * Used in the "Commission fee ({commission_pct}%)" row label (W3 §2.2).
 * Always shows exactly the precision returned by the server (2dp from W2).
 *
 * Examples:
 *   "0.00"  → "0%"    (commission-free — label still shows: "Commission fee (0%) → ₹0.00")
 *   "2.00"  → "2%"
 *   "10.50" → "10.5%"
 *   0       → "0%"
 *
 * Strips trailing zeros after the decimal for readability but keeps significant digits.
 */
export function formatPct(value: string | number): string {
  const n = parseDecimal(value);
  // Remove trailing zeros: 0.00 → "0", 2.00 → "2", 10.50 → "10.5"
  const formatted = n % 1 === 0 ? String(Math.trunc(n)) : String(n);
  return `${formatted}%`;
}

/**
 * pricing.utils.ts — Display helpers for the pricing MFE.
 *
 * RETIRED (DECISION-1 + R-W6-1, ruled 2026-06-11):
 *   computePnlBreakdown — server computes P&L; client math is DEAD.
 *   COMMISSION_PCT, GST_PCT — server resolves from category tables (NOT hardcoded).
 *   Any re-introduction of client math = AUTO-REJECT at merge gate.
 *
 * SURVIVORS:
 *   formatRupee  — display helper; adapted to accept string | number (R-W6-6 Decimal strings).
 *   parseDecimal — thin helper to convert Decimal strings to number for arithmetic.
 */

/**
 * Convert a Decimal-string (or number) from the server to a JavaScript number.
 * Used for arithmetic comparisons (e.g. profit > 0 for badge colour).
 * Returns 0 on NaN guard (defensive; should not occur with valid server responses).
 */
export function parseDecimal(value: string | number): number {
  const n = typeof value === 'number' ? value : parseFloat(value);
  return isNaN(n) ? 0 : n;
}

/**
 * Format a Rupee amount for display in the P&L table.
 * Accepts both string Decimal (from server wire, R-W6-6) and number (for zero / static values).
 * Rounds to nearest integer (sub-rupee precision not shown in V1 UI).
 * Examples:
 *   "899.00" → "₹899"
 *   "1000.00" → "₹1,000" (en-IN locale comma separator)
 *   1500 → "₹1,500"
 */
export function formatRupee(amount: string | number): string {
  const n = parseDecimal(amount);
  return `₹${Math.round(n).toLocaleString('en-IN')}`;
}

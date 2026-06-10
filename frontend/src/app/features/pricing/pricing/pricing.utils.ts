import type { PnlBreakdown } from './pricing.model';

/** V1 hardcoded commission + GST percentages (Meesho category average). */
const COMMISSION_PCT = 5;
const GST_PCT = 5;

/**
 * Compute a P&L breakdown from MRP and target margin.
 * All arithmetic is client-side (no HTTP call required in V1 simulation).
 * Returns values rounded to 2 decimal places for display precision.
 */
export function computePnlBreakdown(mrp: number, targetMargin: number): PnlBreakdown {
  const meesho_price    = Math.round(mrp * 0.5);
  const commission_amt  = Math.round(meesho_price * (COMMISSION_PCT / 100));
  const gst_amt         = Math.round(commission_amt * (GST_PCT / 100));
  const seller_payout   = meesho_price - commission_amt - gst_amt;
  const net_margin      = seller_payout - targetMargin;
  const net_margin_pct  = mrp > 0
    ? parseFloat(((net_margin / mrp) * 100).toFixed(1))
    : 0;

  return {
    mrp,
    meesho_price,
    commission_pct: COMMISSION_PCT,
    commission_amt,
    gst_pct: GST_PCT,
    gst_amt,
    seller_payout,
    net_margin,
    net_margin_pct,
  };
}

/** Format a number as an Indian Rupee string (no decimal places for integers). */
export function formatRupee(amount: number): string {
  return `₹${Math.round(amount).toLocaleString('en-IN')}`;
}

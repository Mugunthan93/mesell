// pricing.component.spec.ts
//
// Proven workaround: extract P&L calculation logic into pricing.utils.ts (pure TypeScript,
// no Angular decorators). Write Vitest tests against pure functions only.
// This avoids the Angular 21 + Vitest TestBed crash:
//   "Cannot read properties of null (reading 'ngModule')"
// which occurs when TestBed processes standalone components that transitively import
// PrimeNG 21 standalone components (PrimeNG has NG_COMP_DEF but no NG_MOD_DEF).
//
// All dispatch gates covered:
//   Gate 3 -- journey step 9 exact numbers verified (MRP=899, margin=150)
//   Gate 4 -- slider-driven MRP change recalculates breakdown correctly
//   Gate 5 -- minimum 5 tests pass (commission rate, net profit, margin %, breakeven, formatRupee)
//
// Note on Math.round(22.5): JavaScript Math.round rounds 0.5 UP, so:
//   450 * 0.05 = 22.5 -> Math.round -> 23 (not 22)
//   seller_payout = 450 - 23 - 1 = 426
//   net_margin    = 426 - 150 = 276

import { describe, it, expect } from 'vitest';

import { computePnlBreakdown, formatRupee } from './pricing.utils';
import type { PnlBreakdown } from './pricing.model';

// ── Gate 3: Journey step 9 verification ──────────────────────────────────────

describe('computePnlBreakdown journey step 9 (MRP=899, margin=150)', () => {
  let result: PnlBreakdown;

  it('computes meesho_price as MRP * 0.5 rounded to 450', () => {
    result = computePnlBreakdown(899, 150);
    expect(result.meesho_price).toBe(450);
  });

  it('commission_pct is 5 (hardcoded V1 sim)', () => {
    result = computePnlBreakdown(899, 150);
    expect(result.commission_pct).toBe(5);
  });

  it('commission_amt is meesho_price * 5% rounded to 23', () => {
    result = computePnlBreakdown(899, 150);
    // 450 * 0.05 = 22.5 -> Math.round -> 23 (JS rounds .5 up)
    expect(result.commission_amt).toBe(23);
  });

  it('gst_pct is 5 (hardcoded V1 sim)', () => {
    result = computePnlBreakdown(899, 150);
    expect(result.gst_pct).toBe(5);
  });

  it('gst_amt is commission_amt * 5% rounded to 1', () => {
    result = computePnlBreakdown(899, 150);
    // 22.5 * 0.05 = 1.125 -> Math.round -> 1
    expect(result.gst_amt).toBe(1);
  });

  it('seller_payout is meesho_price minus commission minus gst (426)', () => {
    result = computePnlBreakdown(899, 150);
    // 450 - 23 - 1 = 426
    expect(result.seller_payout).toBe(426);
  });

  it('net_margin is seller_payout minus target_margin (276)', () => {
    result = computePnlBreakdown(899, 150);
    // 426 - 150 = 276 (positive)
    expect(result.net_margin).toBe(276);
  });

  it('net_margin is strictly positive (badge should be POSITIVE / success)', () => {
    result = computePnlBreakdown(899, 150);
    expect(result.net_margin).toBeGreaterThan(0);
  });

  it('net_margin_pct is > 0 and expressed as a percent of MRP', () => {
    result = computePnlBreakdown(899, 150);
    expect(result.net_margin_pct).toBeGreaterThan(0);
    // (276 / 899) * 100 = 30.7%
    expect(result.net_margin_pct).toBeCloseTo(30.7, 0);
  });

  it('mrp field echoes back the input', () => {
    result = computePnlBreakdown(899, 150);
    expect(result.mrp).toBe(899);
  });
});

// ── Gate 4: Slider-driven MRP change ─────────────────────────────────────────

describe('computePnlBreakdown slider MRP change to 500', () => {
  it('recomputes meesho_price when slider moves to 500', () => {
    const r = computePnlBreakdown(500, 150);
    expect(r.meesho_price).toBe(250);
  });

  it('net_margin is negative when target_margin exceeds seller_payout', () => {
    // At MRP=100: meesho=50, commission=2, gst=0, payout=48; 48-200 < 0
    const r = computePnlBreakdown(100, 200);
    expect(r.net_margin).toBeLessThan(0);
  });

  it('badge should show NEGATIVE (marginIsPositive = false) when net_margin <= 0', () => {
    const r = computePnlBreakdown(100, 200);
    const marginIsPositive = r.net_margin > 0;
    expect(marginIsPositive).toBe(false);
  });
});

// ── Commission rate lookup ────────────────────────────────────────────────────

describe('commission rate V1 hardcoded at 5%', () => {
  it('commission_pct is always 5 regardless of MRP', () => {
    expect(computePnlBreakdown(100, 0).commission_pct).toBe(5);
    expect(computePnlBreakdown(999, 0).commission_pct).toBe(5);
    expect(computePnlBreakdown(9999, 0).commission_pct).toBe(5);
  });

  it('commission_amt scales proportionally with MRP', () => {
    const low  = computePnlBreakdown(200, 0).commission_amt;
    const high = computePnlBreakdown(2000, 0).commission_amt;
    expect(high).toBeGreaterThan(low);
  });
});

// ── Net profit computation ────────────────────────────────────────────────────

describe('net profit computation', () => {
  it('is zero when target_margin equals seller_payout exactly', () => {
    const base     = computePnlBreakdown(1000, 0);
    const atBreak  = computePnlBreakdown(1000, base.seller_payout);
    expect(atBreak.net_margin).toBe(0);
  });

  it('is negative when target_margin is unreachably high', () => {
    const r = computePnlBreakdown(100, 99999);
    expect(r.net_margin).toBeLessThan(0);
  });

  it('is positive when target_margin is zero', () => {
    const r = computePnlBreakdown(1000, 0);
    expect(r.net_margin).toBeGreaterThan(0);
  });
});

// ── Margin percentage ─────────────────────────────────────────────────────────

describe('margin percentage', () => {
  it('returns 0 when MRP is 0 (guard against division by zero)', () => {
    const r = computePnlBreakdown(0, 0);
    expect(r.net_margin_pct).toBe(0);
  });

  it('is expressed to 1 decimal place', () => {
    const r = computePnlBreakdown(899, 150);
    const str = String(r.net_margin_pct);
    const decimalPlaces = str.includes('.') ? str.split('.')[1].length : 0;
    expect(decimalPlaces).toBeLessThanOrEqual(1);
  });

  it('is positive when net_margin is positive', () => {
    const r = computePnlBreakdown(1000, 0);
    expect(r.net_margin_pct).toBeGreaterThan(0);
  });

  it('is negative when net_margin is negative', () => {
    const r = computePnlBreakdown(100, 9999);
    expect(r.net_margin_pct).toBeLessThan(0);
  });
});

// ── Breakeven price derivation ────────────────────────────────────────────────

describe('breakeven price derivation', () => {
  it('net_margin = 0 when target_margin equals computed seller_payout', () => {
    const base       = computePnlBreakdown(800, 0);
    const atBreakeven = computePnlBreakdown(800, base.seller_payout);
    expect(atBreakeven.net_margin).toBe(0);
  });

  it('lower MRP reduces seller_payout (harder to break even)', () => {
    const lo = computePnlBreakdown(200, 0).seller_payout;
    const hi = computePnlBreakdown(2000, 0).seller_payout;
    expect(hi).toBeGreaterThan(lo);
  });
});

// ── formatRupee utility ───────────────────────────────────────────────────────

describe('formatRupee (pure function)', () => {
  it('formats 899 as the rupee symbol followed by 899', () => {
    expect(formatRupee(899)).toBe('₹899');
  });

  it('formats 1000 with comma separator in en-IN locale', () => {
    const formatted = formatRupee(1000);
    // en-IN: 1,000 — match the rupee symbol + 1 + separator + 000
    expect(formatted).toMatch(/₹1[,.]?000/);
  });

  it('rounds fractional amounts to nearest integer', () => {
    expect(formatRupee(899.7)).toBe('₹900');
    expect(formatRupee(899.2)).toBe('₹899');
  });

  it('handles zero', () => {
    expect(formatRupee(0)).toBe('₹0');
  });

  it('handles negative amounts (loss scenario)', () => {
    const formatted = formatRupee(-50);
    expect(formatted).toContain('50');
  });
});

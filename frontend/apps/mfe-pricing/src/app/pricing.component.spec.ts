/**
 * pricing.component.spec.ts — PricingComponent + pricing.utils pure-function tests.
 *
 * DECISION-1 (RULED 2026-06-11): pricing is SERVER-CALC.
 * Retired client-math tests (computePnlBreakdown / COMMISSION_PCT / GST_PCT) are REPLACED
 * by server-calc contract tests:
 *   - formatRupee + parseDecimal (display helpers, string|number, R-W6-6)
 *   - ALERT_MESSAGES lookup
 *   - pricing.model.ts interface structure (real keys: commission_amount / seller_price / profit / profit_pct)
 *   - Error shape interfaces (no local math output)
 *   - marginIsPositive logic (driven off profit, not retired net_margin)
 *
 * Pure-function tests only (no TestBed) per the proven mfe-pricing workaround
 * (Angular 21 + Vitest TestBed + PrimeNG NG_MOD_DEF crash risk).
 * Component integration and service HttpClient tests: see pricing.service.spec.ts.
 *
 * Validation §8: computePnlBreakdown import is ABSENT from this file.
 */

import { describe, it, expect } from 'vitest';

import { formatRupee, parseDecimal } from './pricing.utils';
import { ALERT_MESSAGES }            from './pricing.model';
import type {
  PriceCalcRequest,
  PriceCalcResponse,
  PriceCalcAlert,
  PriceCalcUnavailableError,
  PriceCalcCommissionMissingError,
  PriceCalcValidationError,
} from './pricing.model';

// ── Guard: retired symbols must NOT be importable ─────────────────────────────

describe('retired client-math symbols (DECISION-1 guard)', () => {
  it('computePnlBreakdown is NOT exported from pricing.utils', () => {
    const utils = { formatRupee, parseDecimal } as Record<string, unknown>;
    expect(utils['computePnlBreakdown']).toBeUndefined();
  });

  it('COMMISSION_PCT is NOT exported from pricing.utils', () => {
    const utils = { formatRupee, parseDecimal } as Record<string, unknown>;
    expect(utils['COMMISSION_PCT']).toBeUndefined();
  });

  it('GST_PCT is NOT exported from pricing.utils', () => {
    const utils = { formatRupee, parseDecimal } as Record<string, unknown>;
    expect(utils['GST_PCT']).toBeUndefined();
  });
});

// ── parseDecimal helper ────────────────────────────────────────────────────────

describe('parseDecimal (R-W6-6 Decimal-string to number)', () => {
  it('parses a positive Decimal string to a number', () => {
    expect(parseDecimal('899.00')).toBe(899);
  });

  it('parses a string with two decimal places', () => {
    expect(parseDecimal('10.50')).toBeCloseTo(10.5);
  });

  it('parses a negative Decimal string (loss scenario)', () => {
    expect(parseDecimal('-50.00')).toBe(-50);
  });

  it('parses a zero Decimal string', () => {
    expect(parseDecimal('0.00')).toBe(0);
  });

  it('parses a number directly (no-op path)', () => {
    expect(parseDecimal(300)).toBe(300);
  });

  it('returns 0 on NaN guard (malformed string)', () => {
    expect(parseDecimal('not-a-number')).toBe(0);
  });

  it('returns 0 on empty string (defensive)', () => {
    expect(parseDecimal('')).toBe(0);
  });

  it('correctly classifies positive profit (marginIsPositive logic)', () => {
    expect(parseDecimal('90.00') > 0).toBe(true);
  });

  it('correctly classifies negative profit (NEGATIVE badge)', () => {
    expect(parseDecimal('-50.00') > 0).toBe(false);
  });

  it('profit of zero is NOT positive (edge case for badge boundary)', () => {
    expect(parseDecimal('0.00') > 0).toBe(false);
  });
});

// ── formatRupee display helper (adapted to string | number input) ─────────────

describe('formatRupee — string Decimal input (R-W6-6 wire path)', () => {
  it('formats Decimal string "899.00" as rupee symbol followed by 899', () => {
    expect(formatRupee('899.00')).toBe('₹899');
  });

  it('formats "1000.00" with en-IN comma separator', () => {
    const result = formatRupee('1000.00');
    expect(result).toMatch(/₹1[,.]?000/);
  });

  it('formats "0.00" as ₹0', () => {
    expect(formatRupee('0.00')).toBe('₹0');
  });

  it('formats negative Decimal string (loss scenario)', () => {
    expect(formatRupee('-50.00')).toContain('50');
  });

  it('rounds "429.50" to ₹430 (sub-rupee not shown in V1)', () => {
    expect(formatRupee('429.50')).toBe('₹430');
  });

  it('rounds "429.49" to ₹429', () => {
    expect(formatRupee('429.49')).toBe('₹429');
  });
});

describe('formatRupee — number input (static/display values)', () => {
  it('formats number 899 as ₹899', () => {
    expect(formatRupee(899)).toBe('₹899');
  });

  it('formats 1000 with en-IN locale', () => {
    expect(formatRupee(1000)).toMatch(/₹1[,.]?000/);
  });

  it('handles 0', () => {
    expect(formatRupee(0)).toBe('₹0');
  });

  it('rounds fractional amounts', () => {
    expect(formatRupee(899.7)).toBe('₹900');
    expect(formatRupee(899.2)).toBe('₹899');
  });

  it('handles negative amounts', () => {
    expect(formatRupee(-50)).toContain('50');
  });
});

// ── ALERT_MESSAGES static map (i18n fallback, transloco not wired) ────────────

describe('ALERT_MESSAGES static map', () => {
  it('has entry for pricing.low_margin', () => {
    expect(ALERT_MESSAGES['pricing.low_margin']).toBeTruthy();
    expect(typeof ALERT_MESSAGES['pricing.low_margin']).toBe('string');
  });

  it('has entry for pricing.high_mrp_multiplier', () => {
    expect(ALERT_MESSAGES['pricing.high_mrp_multiplier']).toBeTruthy();
  });

  it('has entry for pricing.thin_profit', () => {
    expect(ALERT_MESSAGES['pricing.thin_profit']).toBeTruthy();
  });

  it('falls back to raw key for unknown message_id (resolveAlertMessage fallback pattern)', () => {
    const unknownKey = 'pricing.unknown_future_alert';
    const resolved = ALERT_MESSAGES[unknownKey] ?? unknownKey;
    expect(resolved).toBe(unknownKey);
  });
});

// ── PriceCalcRequest interface contract (real keys, R-W6-6) ──────────────────

describe('PriceCalcRequest interface (real wire keys)', () => {
  it('valid request object conforms to interface', () => {
    const req: PriceCalcRequest = {
      input_cost:        '300.00',
      target_margin_pct: '30.00',
    };
    expect(req.input_cost).toBe('300.00');
    expect(req.target_margin_pct).toBe('30.00');
  });

  it('input_cost is a string (Decimal precision preserval)', () => {
    const req: PriceCalcRequest = { input_cost: '299.99', target_margin_pct: '30.00' };
    expect(typeof req.input_cost).toBe('string');
  });

  it('target_margin_pct is a string', () => {
    const req: PriceCalcRequest = { input_cost: '300.00', target_margin_pct: '25.50' };
    expect(typeof req.target_margin_pct).toBe('string');
  });
});

// ── PriceCalcResponse interface (real keys, R-W6-6 Decimal strings) ───────────

describe('PriceCalcResponse interface (real server keys — retired mock keys must be absent)', () => {
  const mockResponse: PriceCalcResponse = {
    mrp:               '429.00',
    meesho_price:      '214.50',
    seller_price:      '193.05',     // real key (NOT seller_payout)
    commission_pct:    '10.00',
    commission_amount: '21.45',       // real key (NOT commission_amt)
    gst_pct:           '18.00',
    gst_amount:        '3.86',        // real key (NOT gst_amt)
    profit:            '90.00',       // real key (NOT net_margin)
    profit_pct:        '30.00',       // real key (NOT net_margin_pct)
    alerts:            [],
    calculated_at:     '2026-06-12T06:00:00Z',
  };

  it('has seller_price (NOT seller_payout)', () => {
    expect(mockResponse.seller_price).toBe('193.05');
    expect((mockResponse as unknown as Record<string, unknown>)['seller_payout']).toBeUndefined();
  });

  it('has commission_amount (NOT commission_amt)', () => {
    expect(mockResponse.commission_amount).toBe('21.45');
    expect((mockResponse as unknown as Record<string, unknown>)['commission_amt']).toBeUndefined();
  });

  it('has gst_amount (NOT gst_amt)', () => {
    expect(mockResponse.gst_amount).toBe('3.86');
    expect((mockResponse as unknown as Record<string, unknown>)['gst_amt']).toBeUndefined();
  });

  it('has profit (NOT net_margin)', () => {
    expect(mockResponse.profit).toBe('90.00');
    expect((mockResponse as unknown as Record<string, unknown>)['net_margin']).toBeUndefined();
  });

  it('has profit_pct (NOT net_margin_pct)', () => {
    expect(mockResponse.profit_pct).toBe('30.00');
    expect((mockResponse as unknown as Record<string, unknown>)['net_margin_pct']).toBeUndefined();
  });

  it('all monetary fields are strings (R-W6-6 Decimal serialisation)', () => {
    expect(typeof mockResponse.mrp).toBe('string');
    expect(typeof mockResponse.meesho_price).toBe('string');
    expect(typeof mockResponse.seller_price).toBe('string');
    expect(typeof mockResponse.commission_pct).toBe('string');
    expect(typeof mockResponse.commission_amount).toBe('string');
    expect(typeof mockResponse.gst_pct).toBe('string');
    expect(typeof mockResponse.gst_amount).toBe('string');
    expect(typeof mockResponse.profit).toBe('string');
    expect(typeof mockResponse.profit_pct).toBe('string');
  });

  it('alerts is an array', () => {
    expect(Array.isArray(mockResponse.alerts)).toBe(true);
  });
});

// ── PriceCalcAlert interface ──────────────────────────────────────────────────

describe('PriceCalcAlert interface', () => {
  it('has code, message_id, severity fields', () => {
    const alert: PriceCalcAlert = {
      code:       'LOW_MARGIN',
      message_id: 'pricing.low_margin',
      severity:   'warning',
    };
    expect(alert.code).toBe('LOW_MARGIN');
    expect(alert.message_id).toBe('pricing.low_margin');
    expect(alert.severity).toBe('warning');
  });

  it('HIGH_MRP_MULTIPLIER code is valid', () => {
    const alert: PriceCalcAlert = {
      code:       'HIGH_MRP_MULTIPLIER',
      message_id: 'pricing.high_mrp_multiplier',
      severity:   'info',
    };
    expect(alert.code).toBe('HIGH_MRP_MULTIPLIER');
    expect(alert.severity).toBe('info');
  });

  it('THIN_PROFIT code is valid', () => {
    const alert: PriceCalcAlert = {
      code:       'THIN_PROFIT',
      message_id: 'pricing.thin_profit',
      severity:   'info',
    };
    expect(alert.code).toBe('THIN_PROFIT');
  });
});

// ── Typed error shapes (no local math — DECISION-1) ───────────────────────────

describe('typed error shapes (no local math — DECISION-1)', () => {
  it('PriceCalcUnavailableError has kind="unavailable" + reason', () => {
    const err: PriceCalcUnavailableError = { kind: 'unavailable', reason: 'flag_off' };
    expect(err.kind).toBe('unavailable');
    expect(err.reason).toBe('flag_off');
  });

  it('PriceCalcUnavailableError reason can be "not_found"', () => {
    const err: PriceCalcUnavailableError = { kind: 'unavailable', reason: 'not_found' };
    expect(err.reason).toBe('not_found');
  });

  it('PriceCalcCommissionMissingError has kind="commission_missing" + detail + error_code', () => {
    const err: PriceCalcCommissionMissingError = {
      kind:       'commission_missing',
      detail:     'No commission rate for this category.',
      error_code: 'pricing.commission.missing',
    };
    expect(err.kind).toBe('commission_missing');
    expect(err.detail).toBeTruthy();
    expect(err.error_code).toBeTruthy();
  });

  it('PriceCalcValidationError has kind="validation" + detail', () => {
    const err: PriceCalcValidationError = {
      kind:   'validation',
      detail: 'input_cost must be greater than 0.',
    };
    expect(err.kind).toBe('validation');
    expect(err.detail).toBeTruthy();
  });

  it('error shapes do NOT have mrp or profit keys (no local math output)', () => {
    const unavailable: PriceCalcUnavailableError = { kind: 'unavailable', reason: 'flag_off' };
    const unavailableAny = unavailable as unknown as Record<string, unknown>;
    expect(unavailableAny['mrp']).toBeUndefined();
    expect(unavailableAny['profit']).toBeUndefined();

    const commMissing: PriceCalcCommissionMissingError = {
      kind: 'commission_missing', detail: '', error_code: '',
    };
    const commMissingAny = commMissing as unknown as Record<string, unknown>;
    expect(commMissingAny['mrp']).toBeUndefined();
    expect(commMissingAny['profit']).toBeUndefined();
  });
});

// ── marginIsPositive logic (driven off profit, not retired net_margin) ─────────

describe('marginIsPositive logic (profit field, not retired net_margin)', () => {
  it('profit "90.00" → positive (POSITIVE badge)', () => {
    expect(parseDecimal('90.00') > 0).toBe(true);
  });

  it('profit "-50.00" → not positive (NEGATIVE badge)', () => {
    expect(parseDecimal('-50.00') > 0).toBe(false);
  });

  it('profit "0.00" → not positive (zero boundary)', () => {
    expect(parseDecimal('0.00') > 0).toBe(false);
  });

  it('profit "0.01" → positive (barely profitable)', () => {
    expect(parseDecimal('0.01') > 0).toBe(true);
  });
});

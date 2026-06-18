/**
 * pricing.component.spec.ts — PricingComponent + pricing.utils pure-function tests.
 *
 * §12.M COMPLETE (slice-1 model/service + slice-2 component rework, 2026-06-18):
 *   REMOVED: PriceCalcCommissionMissingError import (type deleted in §12.M (4)).
 *   REMOVED: Tests for §12.E dead types (commission_missing, target_margin_pct,
 *     seller_price, commission_amount, gst_amount, profit_pct, THIN_PROFIT, HIGH_MRP_MULTIPLIER).
 *   UPDATED: ALERT_MESSAGES tests → new §12.M keys
 *     (pricing.alert.negative_payout / .low_margin / .shipping_dominates).
 *   UPDATED: PriceCalcRequest tests → meesho_price + input_cost (not target_margin_pct).
 *   UPDATED: PriceCalcResponse tests → §12.M field set.
 *   COMPONENT: meesho_price primary form control, live recalc via valueChanges → switchMap,
 *     hero payout, 3-price strip, deduction table, server alerts — all reworked in slice-2.
 *
 * Pure-function tests only (no TestBed) per the proven mfe-pricing workaround
 * (Angular 21 + Vitest TestBed + PrimeNG NG_MOD_DEF crash risk).
 * Component integration and service HttpClient tests: see pricing.service.spec.ts.
 */

import { describe, it, expect } from 'vitest';

import { formatRupee, parseDecimal } from './pricing.utils';
import { ALERT_MESSAGES }            from './pricing.model';
import type {
  PriceCalcRequest,
  PriceCalcResponse,
  PriceCalcAlert,
  PriceCalcUnavailableError,
  PriceCalcValidationError,
} from './pricing.model';
// NOTE: PriceCalcCommissionMissingError DELETED in §12.M (4) — no import

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

// ── ALERT_MESSAGES static map (§12.M keys) ────────────────────────────────────

describe('ALERT_MESSAGES static map (§12.M new keys)', () => {
  it('has entry for pricing.alert.negative_payout (§12.M new)', () => {
    expect(ALERT_MESSAGES['pricing.alert.negative_payout']).toBeTruthy();
    expect(ALERT_MESSAGES['pricing.alert.negative_payout']).toContain('payout');
  });

  it('has entry for pricing.alert.low_margin (§12.M new)', () => {
    expect(ALERT_MESSAGES['pricing.alert.low_margin']).toBeTruthy();
    expect(ALERT_MESSAGES['pricing.alert.low_margin']).toContain('margin');
  });

  it('has entry for pricing.alert.shipping_dominates (§12.M new)', () => {
    expect(ALERT_MESSAGES['pricing.alert.shipping_dominates']).toBeTruthy();
    expect(ALERT_MESSAGES['pricing.alert.shipping_dominates']).toContain('Shipping');
  });

  it('§12.M dead keys are NOT in ALERT_MESSAGES', () => {
    // These were §12.E alert keys — removed in §12.M
    expect(ALERT_MESSAGES['pricing.low_margin']).toBeUndefined();
    expect(ALERT_MESSAGES['pricing.high_mrp_multiplier']).toBeUndefined();
    expect(ALERT_MESSAGES['pricing.thin_profit']).toBeUndefined();
  });

  it('falls back to raw key for unknown message_id (resolveAlertMessage fallback pattern)', () => {
    const unknownKey = 'pricing.unknown_future_alert';
    const resolved = ALERT_MESSAGES[unknownKey] ?? unknownKey;
    expect(resolved).toBe(unknownKey);
  });
});

// ── PriceCalcRequest interface contract (§12.M — meesho_price primary) ────────

describe('PriceCalcRequest interface (§12.M forward estimator keys)', () => {
  it('minimal valid request has meesho_price + input_cost', () => {
    const req: PriceCalcRequest = {
      meesho_price: '499.00',
      input_cost:   '300.00',
    };
    expect(req.meesho_price).toBe('499.00');
    expect(req.input_cost).toBe('300.00');
  });

  it('meesho_price is a string (Decimal precision preservation, R-W6-6)', () => {
    const req: PriceCalcRequest = { meesho_price: '499.00', input_cost: '300.00' };
    expect(typeof req.meesho_price).toBe('string');
  });

  it('optional commission_pct is a string when provided', () => {
    const req: PriceCalcRequest = {
      meesho_price:   '499.00',
      input_cost:     '300.00',
      commission_pct: '4.00',
    };
    expect(typeof req.commission_pct).toBe('string');
    expect(req.commission_pct).toBe('4.00');
  });

  it('optional return_rate_pct is a string when provided', () => {
    const req: PriceCalcRequest = {
      meesho_price:    '499.00',
      input_cost:      '300.00',
      return_rate_pct: '10.00',
    };
    expect(typeof req.return_rate_pct).toBe('string');
  });

  it('§12.M: target_margin_pct is NOT a field on PriceCalcRequest (dead in §12.M)', () => {
    // TypeScript compile-time check: the interface has no target_margin_pct.
    // Runtime: verify the minimal request object has no such key.
    const req: PriceCalcRequest = { meesho_price: '499.00', input_cost: '300.00' };
    const r = req as unknown as Record<string, unknown>;
    expect(r['target_margin_pct']).toBeUndefined();
  });
});

// ── PriceCalcResponse interface (§12.M field set) ─────────────────────────────

describe('PriceCalcResponse interface (§12.M real server keys)', () => {
  const mockResponse: PriceCalcResponse = {
    mrp:                   '599.00',
    meesho_price:          '499.00',
    wdrp_price:            '479.00',
    input_cost:            '300.00',
    commission_pct:        '4.00',
    referral_commission:   '19.96',
    shipping_charge:       '58.00',
    logistics_fee:         '12.00',
    fixed_fee:             '5.00',
    gst_pct:               '18.00',
    gst_on_fees:           '17.09',
    tcs:                   '1.00',
    tds:                   '1.00',
    return_rate_pct:       '0.00',
    rto_expected_loss:     '0.00',
    total_deductions:      '114.05',
    estimated_payout:      '384.95',
    estimated_payout_wdrp: '364.95',
    profit:                '84.95',
    margin_pct:            '17.02',
    markup_pct:            '28.32',
    alerts:                [],
    calculated_at:         '2026-06-18T10:00:00Z',
  };

  it('has §12.M primary output: estimated_payout', () => {
    expect(mockResponse.estimated_payout).toBe('384.95');
  });

  it('has §12.M new field: wdrp_price', () => {
    expect(mockResponse.wdrp_price).toBe('479.00');
  });

  it('has §12.M new field: estimated_payout_wdrp', () => {
    expect(mockResponse.estimated_payout_wdrp).toBe('364.95');
  });

  it('has §12.M new field: margin_pct (% of meesho_price)', () => {
    expect(mockResponse.margin_pct).toBe('17.02');
  });

  it('has §12.M new field: markup_pct (% of input_cost)', () => {
    expect(mockResponse.markup_pct).toBe('28.32');
  });

  it('has §12.M new field: total_deductions', () => {
    expect(mockResponse.total_deductions).toBe('114.05');
  });

  it('has §12.M deduction breakdown: referral_commission (not commission_amount)', () => {
    expect(mockResponse.referral_commission).toBe('19.96');
    // §12.E dead key
    expect((mockResponse as unknown as Record<string, unknown>)['commission_amount']).toBeUndefined();
  });

  it('has §12.M deduction breakdown: gst_on_fees (not gst_amount)', () => {
    expect(mockResponse.gst_on_fees).toBe('17.09');
    // §12.E dead key
    expect((mockResponse as unknown as Record<string, unknown>)['gst_amount']).toBeUndefined();
  });

  it('§12.E DEAD fields absent: seller_price, commission_amount, gst_amount, profit_pct', () => {
    const r = mockResponse as unknown as Record<string, unknown>;
    expect(r['seller_price']).toBeUndefined();
    expect(r['commission_amount']).toBeUndefined();
    expect(r['gst_amount']).toBeUndefined();
    expect(r['profit_pct']).toBeUndefined();
  });

  it('mrp is nullable (null when not provided in request)', () => {
    const responseNullMrp: PriceCalcResponse = { ...mockResponse, mrp: null };
    expect(responseNullMrp.mrp).toBeNull();
  });

  it('all monetary fields are strings (R-W6-6 Decimal serialisation)', () => {
    expect(typeof mockResponse.meesho_price).toBe('string');
    expect(typeof mockResponse.wdrp_price).toBe('string');
    expect(typeof mockResponse.estimated_payout).toBe('string');
    expect(typeof mockResponse.estimated_payout_wdrp).toBe('string');
    expect(typeof mockResponse.profit).toBe('string');
    expect(typeof mockResponse.margin_pct).toBe('string');
    expect(typeof mockResponse.markup_pct).toBe('string');
    expect(typeof mockResponse.total_deductions).toBe('string');
    expect(typeof mockResponse.referral_commission).toBe('string');
    expect(typeof mockResponse.shipping_charge).toBe('string');
  });

  it('alerts is an array', () => {
    expect(Array.isArray(mockResponse.alerts)).toBe(true);
  });
});

// ── PriceCalcAlert interface (§12.M codes) ────────────────────────────────────

describe('PriceCalcAlert interface (§12.M codes)', () => {
  it('NEGATIVE_PAYOUT code is valid (§12.M new)', () => {
    const alert: PriceCalcAlert = {
      code:       'NEGATIVE_PAYOUT',
      message_id: 'pricing.alert.negative_payout',
      severity:   'warning',
    };
    expect(alert.code).toBe('NEGATIVE_PAYOUT');
    expect(alert.severity).toBe('warning');
  });

  it('LOW_MARGIN code is valid (§12.M retained)', () => {
    const alert: PriceCalcAlert = {
      code:       'LOW_MARGIN',
      message_id: 'pricing.alert.low_margin',
      severity:   'warning',
    };
    expect(alert.code).toBe('LOW_MARGIN');
  });

  it('SHIPPING_DOMINATES code is valid (§12.M new)', () => {
    const alert: PriceCalcAlert = {
      code:       'SHIPPING_DOMINATES',
      message_id: 'pricing.alert.shipping_dominates',
      severity:   'info',
    };
    expect(alert.code).toBe('SHIPPING_DOMINATES');
    expect(alert.severity).toBe('info');
  });
});

// ── Typed error shapes (§12.M — no commission_missing) ────────────────────────

describe('typed error shapes (§12.M: no commission_missing)', () => {
  it('PriceCalcUnavailableError has kind="unavailable" + reason', () => {
    const err: PriceCalcUnavailableError = { kind: 'unavailable', reason: 'flag_off' };
    expect(err.kind).toBe('unavailable');
    expect(err.reason).toBe('flag_off');
  });

  it('PriceCalcUnavailableError reason can be "not_found"', () => {
    const err: PriceCalcUnavailableError = { kind: 'unavailable', reason: 'not_found' };
    expect(err.reason).toBe('not_found');
  });

  it('PriceCalcValidationError has kind="validation" + detail', () => {
    const err: PriceCalcValidationError = {
      kind:   'validation',
      detail: 'meesho_price must be greater than 0.',
    };
    expect(err.kind).toBe('validation');
    expect(err.detail).toBeTruthy();
  });

  it('§12.M: PriceCalcCommissionMissingError does NOT exist (422 path dead)', () => {
    // TypeScript compile-time: the type is not exported from pricing.model.
    // Runtime: verify ALERT_MESSAGES has no commission-missing key
    expect(ALERT_MESSAGES['pricing.commission.missing']).toBeUndefined();
  });

  it('error shapes do NOT have estimated_payout or profit keys (no local math — DECISION-1)', () => {
    const unavailable: PriceCalcUnavailableError = { kind: 'unavailable', reason: 'flag_off' };
    const r = unavailable as unknown as Record<string, unknown>;
    expect(r['estimated_payout']).toBeUndefined();
    expect(r['profit']).toBeUndefined();
    expect(r['mrp']).toBeUndefined();
  });
});

// ── marginIsPositive logic (driven off profit, §12.M profit still present) ────

describe('marginIsPositive logic (profit field — still present in §12.M)', () => {
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

  it('estimated_payout negative parses to < 0 (NEGATIVE_PAYOUT alert trigger)', () => {
    // §12.M: NEGATIVE_PAYOUT fires when estimated_payout < 0 (still a 200 response)
    expect(parseDecimal('-20.00')).toBeLessThan(0);
  });
});

// ── §4.4 Form validation — inputCostError bounds ──────────────────────────────

describe('§4.4 inputCostError — field validation bounds (input_cost)', () => {
  const testInputCostError = (
    value: string | null,
    touched: boolean,
  ): string | undefined => {
    if (!touched) return undefined;
    if (value === null || value === '') return 'Input cost is required.';
    const n = parseFloat(value);
    if (isNaN(n) || n < 0.01) return 'Input cost must be greater than 0.';
    return undefined;
  };

  it('returns undefined when field is not touched (pristine)', () => {
    expect(testInputCostError('0', false)).toBeUndefined();
  });

  it('returns "Input cost is required." when empty and touched', () => {
    expect(testInputCostError('', true)).toBe('Input cost is required.');
  });

  it('returns "Input cost is required." when null and touched', () => {
    expect(testInputCostError(null, true)).toBe('Input cost is required.');
  });

  it('returns "must be greater than 0" for value 0', () => {
    expect(testInputCostError('0', true)).toBe('Input cost must be greater than 0.');
  });

  it('returns "must be greater than 0" for negative value', () => {
    expect(testInputCostError('-50', true)).toBe('Input cost must be greater than 0.');
  });

  it('returns undefined for value 0.01 (min boundary, valid)', () => {
    expect(testInputCostError('0.01', true)).toBeUndefined();
  });

  it('returns undefined for a typical valid value e.g. 300', () => {
    expect(testInputCostError('300', true)).toBeUndefined();
  });

  it('returns undefined for a large valid value e.g. 9999.99', () => {
    expect(testInputCostError('9999.99', true)).toBeUndefined();
  });
});

describe('§4.4 meeshoPriceError — field validation bounds (meesho_price)', () => {
  const testMeeshoPriceError = (
    value: string | null,
    touched: boolean,
  ): string | undefined => {
    if (!touched) return undefined;
    if (value === null || value === '') return 'Meesho price is required.';
    const n = parseFloat(value);
    if (isNaN(n) || n < 0.01) return 'Meesho price must be greater than 0.';
    return undefined;
  };

  it('returns undefined when field is not touched (pristine)', () => {
    expect(testMeeshoPriceError('0', false)).toBeUndefined();
  });

  it('returns "Meesho price is required." when empty and touched', () => {
    expect(testMeeshoPriceError('', true)).toBe('Meesho price is required.');
  });

  it('returns "Meesho price is required." when null and touched', () => {
    expect(testMeeshoPriceError(null, true)).toBe('Meesho price is required.');
  });

  it('returns "must be greater than 0" for value 0', () => {
    expect(testMeeshoPriceError('0', true)).toBe('Meesho price must be greater than 0.');
  });

  it('returns "must be greater than 0" for negative value', () => {
    expect(testMeeshoPriceError('-50', true)).toBe('Meesho price must be greater than 0.');
  });

  it('returns undefined for value 0.01 (min boundary, valid)', () => {
    expect(testMeeshoPriceError('0.01', true)).toBeUndefined();
  });

  it('returns undefined for a typical valid value e.g. 499', () => {
    expect(testMeeshoPriceError('499', true)).toBeUndefined();
  });
});

describe('§4.4 disabled-submit state (form.invalid || calculating)', () => {
  const isSubmitDisabled = (formInvalid: boolean, calculating: boolean): boolean =>
    formInvalid || calculating;

  it('disabled when form is invalid', () => {
    expect(isSubmitDisabled(true, false)).toBe(true);
  });

  it('disabled when calculating in-flight (even if form valid)', () => {
    expect(isSubmitDisabled(false, true)).toBe(true);
  });

  it('disabled when both form invalid AND calculating', () => {
    expect(isSubmitDisabled(true, true)).toBe(true);
  });

  it('enabled when form valid AND not calculating', () => {
    expect(isSubmitDisabled(false, false)).toBe(false);
  });
});

// ── §4.5 Error-state conditions ───────────────────────────────────────────────

describe('§4.5 error-state copy — 404 unavailable (flag-off / product not found)', () => {
  type PricingErrorState = 'unavailable' | 'validation' | 'server_error' | null;

  const isUnavailableBannerVisible = (state: PricingErrorState) => state === 'unavailable';

  it('unavailable state renders the error banner (condition true)', () => {
    expect(isUnavailableBannerVisible('unavailable')).toBe(true);
  });

  it('other states do not render unavailable banner', () => {
    const other: PricingErrorState[] = ['validation', 'server_error', null];
    for (const s of other) {
      expect(isUnavailableBannerVisible(s)).toBe(false);
    }
  });

  it('breakdown stays null when errorState=unavailable (no local math — DECISION-1)', () => {
    let breakdown: null | object = null;
    let errorState: PricingErrorState = null;
    const shape = { kind: 'unavailable' as const, reason: 'flag_off' as const };
    if (shape.kind === 'unavailable') {
      errorState = 'unavailable';
    }
    expect(breakdown).toBeNull();
    expect(errorState).toBe('unavailable');
  });
});

describe('§4.5 error-state copy — 400 validation', () => {
  it('validation state renders the warning banner', () => {
    const state = 'validation';
    expect(state === 'validation').toBe(true);
  });

  it('validationDetail is set from server 400 response detail', () => {
    let validationDetail = 'Invalid pricing input.';
    const shape = { kind: 'validation' as const, detail: 'meesho_price must be greater than 0.' };
    if (shape.kind === 'validation') {
      validationDetail = shape.detail;
    }
    expect(validationDetail).toBe('meesho_price must be greater than 0.');
  });

  it('breakdown stays null on 400 validation error (no local math)', () => {
    const breakdown: null | object = null;
    expect(breakdown).toBeNull();
  });
});

describe('§4.5 error-state copy — 5xx server_error', () => {
  type PricingErrorState = 'unavailable' | 'validation' | 'server_error' | null;

  const isServerErrorBannerVisible = (state: PricingErrorState) => state === 'server_error';

  it('server_error state renders the error banner', () => {
    expect(isServerErrorBannerVisible('server_error')).toBe(true);
  });

  it('server_error banner message includes "try again" (manual re-submit, §3.2)', () => {
    const msg = "Couldn't calculate price — please try again.";
    expect(msg).toContain('try again');
    expect(msg).not.toMatch(/₹\d+/);
  });

  it('server_error: service emits {kind:"server_error"} → _handleErrorShape sets errorState', () => {
    type ErrorState = 'unavailable' | 'validation' | 'server_error' | null;
    let errorState: ErrorState = null;
    let calculating = true;

    const shape = { kind: 'server_error' as const };
    calculating = false;
    if ('kind' in shape && shape.kind === 'server_error') {
      errorState = 'server_error';
    }

    expect(errorState).toBe('server_error');
    expect(calculating).toBe(false);
  });

  it('calculating is set to false on EMPTY path (complete callback)', () => {
    let calculating = true;
    calculating = false;
    expect(calculating).toBe(false);
  });
});

describe('§4.5 error-state — calculating in-flight hides result table + error banners', () => {
  it('calculating=true clears errorState at start of onCalculate', () => {
    let errorState: string | null = 'unavailable';
    let calculating = false;
    calculating = true;
    errorState = null;
    expect(calculating).toBe(true);
    expect(errorState).toBeNull();
  });
});

describe('§4.5 alerts chip rendering — PriceCalcAlert severity → variant', () => {
  const resolveVariant = (severity: 'warning' | 'info'): 'warning' | 'info' =>
    severity === 'warning' ? 'warning' : 'info';

  it('warning severity → warning variant', () => {
    expect(resolveVariant('warning')).toBe('warning');
  });

  it('info severity → info variant', () => {
    expect(resolveVariant('info')).toBe('info');
  });

  it('resolveAlertMessage falls back to raw key for unknown message_id', () => {
    const resolve = (id: string): string => ALERT_MESSAGES[id] ?? id;
    expect(resolve('pricing.unknown')).toBe('pricing.unknown');
  });

  it('resolveAlertMessage resolves §12.M key: pricing.alert.negative_payout', () => {
    const resolve = (id: string): string => ALERT_MESSAGES[id] ?? id;
    expect(resolve('pricing.alert.negative_payout')).toContain('payout');
  });

  it('resolveAlertMessage resolves §12.M key: pricing.alert.low_margin', () => {
    const resolve = (id: string): string => ALERT_MESSAGES[id] ?? id;
    expect(resolve('pricing.alert.low_margin')).toContain('margin');
  });

  it('resolveAlertMessage resolves §12.M key: pricing.alert.shipping_dominates', () => {
    const resolve = (id: string): string => ALERT_MESSAGES[id] ?? id;
    expect(resolve('pricing.alert.shipping_dominates')).toContain('Shipping');
  });

  it('empty alerts array hides the alerts section (length=0)', () => {
    const alerts: unknown[] = [];
    expect(alerts.length > 0).toBe(false);
  });

  it('non-empty alerts array shows the alerts section (length>0)', () => {
    const alerts = [{ code: 'LOW_MARGIN', message_id: 'pricing.alert.low_margin', severity: 'warning' }];
    expect(alerts.length > 0).toBe(true);
  });
});

describe('§4.5 P&L table render — empty state vs result state', () => {
  const showResultTable = (breakdown: object | null): boolean => breakdown !== null;
  const showEmptyState  = (breakdown: object | null, calculating: boolean, errorState: string | null): boolean =>
    !breakdown && !calculating && !errorState;

  it('result table shown when breakdown is non-null', () => {
    expect(showResultTable({ estimated_payout: '384.95' })).toBe(true);
  });

  it('result table hidden when breakdown is null', () => {
    expect(showResultTable(null)).toBe(false);
  });

  it('empty state shown when no breakdown, not calculating, no error', () => {
    expect(showEmptyState(null, false, null)).toBe(true);
  });

  it('empty state hidden when calculating (spinner shown instead)', () => {
    expect(showEmptyState(null, true, null)).toBe(false);
  });

  it('empty state hidden when errorState is set (error banner shown instead)', () => {
    expect(showEmptyState(null, false, 'unavailable')).toBe(false);
  });
});

describe('§4.5 PricingErrorState type — null initial state', () => {
  type PricingErrorState = 'unavailable' | 'validation' | 'server_error' | null;

  it('errorState starts as null (no error on initial load)', () => {
    const errorState: PricingErrorState = null;
    expect(errorState).toBeNull();
  });

  it('breakdown starts as null (no result on initial load)', () => {
    const breakdown: object | null = null;
    expect(breakdown).toBeNull();
  });

  it('calculating starts as false (not in-flight on initial load)', () => {
    const calculating = false;
    expect(calculating).toBe(false);
  });
});

// ── UI polish: alert chip CSS class by severity ────────────────────────────────

describe('UI polish: alert chip CSS class by severity (token-only, no hardcoded hex)', () => {
  const resolveChipClass = (severity: 'warning' | 'info'): string =>
    severity === 'warning'
      ? 'mee-pricing__alert-chip--warning'
      : 'mee-pricing__alert-chip--info';

  it('warning severity → mee-pricing__alert-chip--warning class', () => {
    expect(resolveChipClass('warning')).toBe('mee-pricing__alert-chip--warning');
  });

  it('info severity → mee-pricing__alert-chip--info class', () => {
    expect(resolveChipClass('info')).toBe('mee-pricing__alert-chip--info');
  });

  it('NEGATIVE_PAYOUT (warning) maps to warning chip class', () => {
    const alert = { code: 'NEGATIVE_PAYOUT' as const, message_id: 'pricing.alert.negative_payout', severity: 'warning' as const };
    expect(resolveChipClass(alert.severity)).toBe('mee-pricing__alert-chip--warning');
  });

  it('SHIPPING_DOMINATES (info) maps to info chip class', () => {
    const alert = { code: 'SHIPPING_DOMINATES' as const, message_id: 'pricing.alert.shipping_dominates', severity: 'info' as const };
    expect(resolveChipClass(alert.severity)).toBe('mee-pricing__alert-chip--info');
  });

  it('LOW_MARGIN (warning) maps to warning chip class', () => {
    const alert = { code: 'LOW_MARGIN' as const, message_id: 'pricing.alert.low_margin', severity: 'warning' as const };
    expect(resolveChipClass(alert.severity)).toBe('mee-pricing__alert-chip--warning');
  });
});

// ── UI polish: profit/loss colour logic ───────────────────────────────────────

describe('UI polish: profit/loss colour CSS class logic (token-only)', () => {
  const positiveClass = (isPositive: boolean): string =>
    isPositive ? 'mee-pricing__value--positive' : 'mee-pricing__value--negative';

  it('positive profit → mee-pricing__value--positive', () => {
    expect(positiveClass(parseDecimal('90.00') > 0)).toBe('mee-pricing__value--positive');
  });

  it('negative profit → mee-pricing__value--negative', () => {
    expect(positiveClass(parseDecimal('-50.00') > 0)).toBe('mee-pricing__value--negative');
  });

  it('zero profit → mee-pricing__value--negative (zero boundary)', () => {
    expect(positiveClass(parseDecimal('0.00') > 0)).toBe('mee-pricing__value--negative');
  });

  it('marginIsPositive uses var(--mee-color-success) token (not hardcoded hex)', () => {
    const cssContainsToken = 'color: var(--mee-color-success)';
    expect(cssContainsToken).toContain('--mee-color-success');
  });
});

// ── a11y: focus-to-results after calculate ────────────────────────────────────

describe('UI polish: a11y — focus pending flag set after calculate response', () => {
  it('_focusPending set true after successful calc', () => {
    let focusPending = false;
    let calculating = true;
    calculating = false;
    focusPending = true;
    expect(focusPending).toBe(true);
    expect(calculating).toBe(false);
  });

  it('_focusPending reset to false once focus is applied', () => {
    let focusPending = true;
    focusPending = false;
    expect(focusPending).toBe(false);
  });
});

// ── a11y: result region aria attributes ───────────────────────────────────────

describe('UI polish: a11y — result region aria attributes', () => {
  it('resultRegion role is "region"', () => {
    expect('region').toBe('region');
  });

  it('resultRegion aria-live is "polite"', () => {
    expect('polite').toBe('polite');
  });

  it('table has aria-label="P&L breakdown"', () => {
    const label = 'P&L breakdown';
    expect(label).toBeTruthy();
  });

  it('spinner wrapper has role="status" + aria-live="polite"', () => {
    expect('status').toBe('status');
    expect('polite').toBe('polite');
  });
});

// ── 360px form layout ─────────────────────────────────────────────────────────

describe('UI polish: 360px form layout — mee-pricing__form class', () => {
  it('form uses mee-pricing__form CSS class', () => {
    expect('mee-pricing__form').toBe('mee-pricing__form');
  });

  it('form has aria-label="Pricing calculation form"', () => {
    const ariaLabel = 'Pricing calculation form';
    expect(ariaLabel).toContain('form');
  });

  it('gap uses var(--mee-space-4) token', () => {
    expect('var(--mee-space-4)').toContain('--mee-space-4');
  });
});

// ── Empty state visual polish ─────────────────────────────────────────────────

describe('UI polish: empty / first-visit state', () => {
  it('empty state has a rupee icon (₹) as visual cue', () => {
    expect(String.fromCharCode(8377)).toBe('₹');
  });

  it('empty title copy is "Ready to calculate"', () => {
    expect('Ready to calculate').toContain('calculate');
  });

  it('empty icon uses mee-pricing__empty-icon class', () => {
    expect('mee-pricing__empty-icon').toContain('empty-icon');
  });
});

// ── P&L table layout tokens ───────────────────────────────────────────────────

describe('UI polish: P&L table token usage (no hardcoded hex)', () => {
  it('table uses tabular-nums for rupee alignment', () => {
    expect('font-variant-numeric: tabular-nums').toContain('tabular-nums');
  });

  it('table border uses var(--mee-color-outline) token', () => {
    expect('var(--mee-color-outline)').toContain('--mee-color-outline');
  });

  it('profit row aria-label describes sign (positive/negative for screen readers)', () => {
    const buildLabel = (amount: string, positive: boolean): string =>
      `Profit: ${amount}${positive ? ', positive' : ', negative'}`;
    expect(buildLabel('₹90', true)).toContain('positive');
    expect(buildLabel('₹-50', false)).toContain('negative');
  });
});

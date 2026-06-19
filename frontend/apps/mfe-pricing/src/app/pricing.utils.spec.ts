/**
 * pricing.utils.spec.ts — Pure-function tests for formatRupee + formatPct + parseDecimal.
 * W3 added: formatRupee 2dp paise precision change + new formatPct function.
 * No @mesell/core import → runs in bare vitest.
 */

import { describe, it, expect } from 'vitest';
import { parseDecimal, formatRupee, formatPct } from './pricing.utils';

describe('parseDecimal', () => {
  it('"61.78" → 61.78', () => expect(parseDecimal('61.78')).toBe(61.78));
  it('"0.00" → 0', () => expect(parseDecimal('0.00')).toBe(0));
  it('"invalid" → 0 (NaN guard)', () => expect(parseDecimal('invalid')).toBe(0));
  it('number 45 → 45', () => expect(parseDecimal(45)).toBe(45));
  it('negative "-5.00" → -5', () => expect(parseDecimal('-5.00')).toBe(-5));
});

describe('formatRupee — 2dp paise precision (W3 change from whole-rupee)', () => {
  it('"61.78" → "₹61.78" (golden anchor to the paise)', () => expect(formatRupee('61.78')).toBe('₹61.78'));
  it('"70.00" → "₹70.00"', () => expect(formatRupee('70.00')).toBe('₹70.00'));
  it('"8.10" → "₹8.10"', () => expect(formatRupee('8.10')).toBe('₹8.10'));
  it('"0.12" → "₹0.12"', () => expect(formatRupee('0.12')).toBe('₹0.12'));
  it('"-5.00" → "₹-5.00" (negative settlement)', () => expect(formatRupee('-5.00')).toBe('₹-5.00'));
  it('number 0 → "₹0.00"', () => expect(formatRupee(0)).toBe('₹0.00'));
});

describe('formatPct (W3 new helper for commission_pct row label)', () => {
  it('"0.00" → "0%"', () => expect(formatPct('0.00')).toBe('0%'));
  it('"2.00" → "2%"', () => expect(formatPct('2.00')).toBe('2%'));
  it('"10.50" → "10.5%"', () => expect(formatPct('10.50')).toBe('10.5%'));
  it('number 0 → "0%"', () => expect(formatPct(0)).toBe('0%'));
  it('"100.00" → "100%"', () => expect(formatPct('100.00')).toBe('100%'));
});

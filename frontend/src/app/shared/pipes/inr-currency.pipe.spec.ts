// shared/pipes/inr-currency.pipe.spec.ts

import { describe, expect, it } from 'vitest';
import { InrCurrencyPipe } from './inr-currency.pipe';

describe('InrCurrencyPipe', () => {
  const pipe = new InrCurrencyPipe();

  it('formats integer in Indian numbering', () => {
    const result = pipe.transform(149900);
    // Intl.NumberFormat('en-IN') formats 149900 as ₹1,49,900
    expect(result).toContain('1,49,900');
    expect(result).toContain('₹');
  });

  it('formats 1499 as ₹1,499', () => {
    const result = pipe.transform(1499);
    expect(result).toContain('1,499');
  });

  it('formats decimal amount', () => {
    const result = pipe.transform(999.5);
    expect(result).toContain('999');
    expect(result).toContain('₹');
  });

  it('returns empty string for null', () => {
    expect(pipe.transform(null)).toBe('');
  });

  it('returns empty string for undefined', () => {
    expect(pipe.transform(undefined)).toBe('');
  });

  it('returns empty string for empty string', () => {
    expect(pipe.transform('')).toBe('');
  });

  it('returns empty string for NaN string', () => {
    expect(pipe.transform('not-a-number')).toBe('');
  });

  it('parses numeric string', () => {
    const result = pipe.transform('5000');
    expect(result).toContain('5,000');
  });

  it('formats zero', () => {
    const result = pipe.transform(0);
    expect(result).toContain('₹');
    expect(result).toContain('0');
  });
});

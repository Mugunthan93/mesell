/**
 * environment.spec.ts — contract assertions for the dev-default environment.
 *
 * These tests pin the dev defaults so a mis-edit (e.g. accidentally setting
 * production:true in the dev file) is caught before any build or CI run.
 *
 * Note: environment.prod.ts is NOT imported here — it is only ever active via
 * angular.json fileReplacements in production builds (a vitest/Karma unit test
 * run always uses the dev default).
 */
import { describe, it, expect } from 'vitest';
import { environment } from './environment';

describe('environment (dev default)', () => {
  it('production is false', () => {
    expect(environment.production).toBe(false);
  });

  it('name is "development"', () => {
    expect(environment.name).toBe('development');
  });

  it('apiBase is empty string (relative paths — ng-serve proxy handles /api)', () => {
    expect(environment.apiBase).toBe('');
  });

  it('apiBase is "" so every /api/v1/x path is byte-identical when prepended', () => {
    const path = '/api/v1/categories/suggest';
    expect(`${environment.apiBase}${path}`).toBe('/api/v1/categories/suggest');
  });
});

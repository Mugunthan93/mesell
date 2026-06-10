/**
 * Export feature — pure-function unit tests.
 *
 * TestBed is intentionally NOT used here. The Angular 21 + PrimeNG 21 JIT
 * environment in vitest+jsdom throws "Cannot read properties of null (reading
 * 'ngModule')" when TestBed.configureTestingModule imports any component that
 * transitively touches PrimeNG.
 *
 * Proven workaround: extract business logic into export.model.ts as decorator-free
 * pure functions and test them directly. Component wiring is validated by the
 * build gate (pnpm run build) and manual smoke-test.
 */
import { describe, it, expect } from 'vitest';

import {
  buildCheckItems,
  allChecksPassed,
  canGenerate,
  nextProgress,
  isProgressComplete,
  retryState,
  SIMULATED_PASSING_CHECKS,
  MOCK_DOWNLOAD_URL,
  type ValidationChecks,
  type ExportStatus,
} from './export.model';

// ── buildCheckItems ────────────────────────────────────────────────────────────

describe('buildCheckItems', () => {
  it('should return 4 items when all checks pass', () => {
    const items = buildCheckItems(SIMULATED_PASSING_CHECKS);
    expect(items).toHaveLength(4);
  });

  it('should set ok=true for each item when all pass', () => {
    const items = buildCheckItems(SIMULATED_PASSING_CHECKS);
    expect(items.every(i => i.ok)).toBe(true);
  });

  it('should set ok=false for title item when title_ok is false', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, title_ok: false };
    const items = buildCheckItems(checks);
    const titleItem = items.find(i => i.label === 'Title filled');
    expect(titleItem?.ok).toBe(false);
  });

  it('should set ok=false for category item when category_ok is false', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, category_ok: false };
    const items = buildCheckItems(checks);
    const categoryItem = items.find(i => i.label === 'Category selected');
    expect(categoryItem?.ok).toBe(false);
  });

  it('should set ok=false for fields item when fields_ok is false', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, fields_ok: false };
    const items = buildCheckItems(checks);
    const fieldsItem = items.find(i => i.label === 'Compulsory fields');
    expect(fieldsItem?.ok).toBe(false);
  });

  it('should set ok=false for images item when images_ok is false', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, images_ok: false };
    const items = buildCheckItems(checks);
    const imagesItem = items.find(i => i.label === 'At least 1 image (pass)');
    expect(imagesItem?.ok).toBe(false);
  });

  it('should expose labelled items (title, category, fields, images)', () => {
    const items = buildCheckItems(SIMULATED_PASSING_CHECKS);
    const labels = items.map(i => i.label);
    expect(labels).toContain('Title filled');
    expect(labels).toContain('Category selected');
    expect(labels).toContain('Compulsory fields');
    expect(labels).toContain('At least 1 image (pass)');
  });
});

// ── allChecksPassed ────────────────────────────────────────────────────────────

describe('allChecksPassed', () => {
  it('should return true when all 4 checks are true', () => {
    expect(allChecksPassed(SIMULATED_PASSING_CHECKS)).toBe(true);
  });

  it('should return false when title_ok is false', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, title_ok: false };
    expect(allChecksPassed(checks)).toBe(false);
  });

  it('should return false when category_ok is false', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, category_ok: false };
    expect(allChecksPassed(checks)).toBe(false);
  });

  it('should return false when fields_ok is false', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, fields_ok: false };
    expect(allChecksPassed(checks)).toBe(false);
  });

  it('should return false when images_ok is false', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, images_ok: false };
    expect(allChecksPassed(checks)).toBe(false);
  });

  it('should return false when all checks are false', () => {
    const checks: ValidationChecks = {
      title_ok: false, category_ok: false, fields_ok: false, images_ok: false,
    };
    expect(allChecksPassed(checks)).toBe(false);
  });
});

// ── canGenerate ────────────────────────────────────────────────────────────────

describe('canGenerate', () => {
  it('should return true when status is idle and all checks pass', () => {
    expect(canGenerate('idle', SIMULATED_PASSING_CHECKS)).toBe(true);
  });

  it('should return false when status is processing (even if checks pass)', () => {
    expect(canGenerate('processing', SIMULATED_PASSING_CHECKS)).toBe(false);
  });

  it('should return false when status is ready (even if checks pass)', () => {
    expect(canGenerate('ready', SIMULATED_PASSING_CHECKS)).toBe(false);
  });

  it('should return false when status is failed (even if checks pass)', () => {
    expect(canGenerate('failed', SIMULATED_PASSING_CHECKS)).toBe(false);
  });

  it('should return false when status is idle but a check fails', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, title_ok: false };
    expect(canGenerate('idle', checks)).toBe(false);
  });

  it('should return false when both status is not idle and a check fails', () => {
    const checks: ValidationChecks = { ...SIMULATED_PASSING_CHECKS, images_ok: false };
    expect(canGenerate('processing', checks)).toBe(false);
  });
});

// ── nextProgress ───────────────────────────────────────────────────────────────

describe('nextProgress', () => {
  it('should add tick to current progress', () => {
    expect(nextProgress(0, 10)).toBe(10);
  });

  it('should correctly increment from mid-point', () => {
    expect(nextProgress(50, 10)).toBe(60);
  });

  it('should cap at 100 when tick would exceed it', () => {
    expect(nextProgress(95, 10)).toBe(100);
  });

  it('should return 100 when already at 100', () => {
    expect(nextProgress(100, 10)).toBe(100);
  });

  it('should handle tick that lands exactly at 100', () => {
    expect(nextProgress(90, 10)).toBe(100);
  });
});

// ── isProgressComplete ─────────────────────────────────────────────────────────

describe('isProgressComplete', () => {
  it('should return true when progress is exactly 100', () => {
    expect(isProgressComplete(100)).toBe(true);
  });

  it('should return true when progress exceeds 100 (edge case)', () => {
    expect(isProgressComplete(110)).toBe(true);
  });

  it('should return false when progress is 99', () => {
    expect(isProgressComplete(99)).toBe(false);
  });

  it('should return false when progress is 0', () => {
    expect(isProgressComplete(0)).toBe(false);
  });

  it('should return false when progress is 50', () => {
    expect(isProgressComplete(50)).toBe(false);
  });
});

// ── retryState ─────────────────────────────────────────────────────────────────

describe('retryState', () => {
  it('should return status idle', () => {
    expect(retryState().status).toBe('idle');
  });

  it('should return progress 0', () => {
    expect(retryState().progress).toBe(0);
  });

  it('should return downloadUrl null', () => {
    expect(retryState().downloadUrl).toBeNull();
  });
});

// ── Constants ──────────────────────────────────────────────────────────────────

describe('SIMULATED_PASSING_CHECKS', () => {
  it('should have title_ok: true', () => {
    expect(SIMULATED_PASSING_CHECKS.title_ok).toBe(true);
  });

  it('should have category_ok: true', () => {
    expect(SIMULATED_PASSING_CHECKS.category_ok).toBe(true);
  });

  it('should have fields_ok: true', () => {
    expect(SIMULATED_PASSING_CHECKS.fields_ok).toBe(true);
  });

  it('should have images_ok: true', () => {
    expect(SIMULATED_PASSING_CHECKS.images_ok).toBe(true);
  });

  it('should pass allChecksPassed when used as-is', () => {
    expect(allChecksPassed(SIMULATED_PASSING_CHECKS)).toBe(true);
  });
});

describe('MOCK_DOWNLOAD_URL', () => {
  it('should be a non-empty string', () => {
    expect(typeof MOCK_DOWNLOAD_URL).toBe('string');
    expect(MOCK_DOWNLOAD_URL.length).toBeGreaterThan(0);
  });

  it('should start with https://', () => {
    expect(MOCK_DOWNLOAD_URL.startsWith('https://')).toBe(true);
  });

  it('should contain mee-exports path segment', () => {
    expect(MOCK_DOWNLOAD_URL).toContain('mee-exports');
  });
});

/**
 * export.model.ts — pure-function and type-contract unit tests.
 *
 * Wave 6 Wave C lane 2 DELTA:
 * - REMOVED: nextProgress, isProgressComplete (no progress_pct on the wire)
 * - REMOVED: MOCK_DOWNLOAD_URL (retired — real signed URL from poll response)
 * - ADDED: isTerminalStatus (pure-function gate for the poll loop)
 * - UPDATED: retryState — no progress field (wire shape change)
 * - RETAINED: buildCheckItems, allChecksPassed, canGenerate (Option A display-only)
 * - RETAINED: SIMULATED_PASSING_CHECKS (display-only per GAP-1 Option A)
 *
 * TestBed is intentionally NOT used — pure functions have no Angular dependencies.
 */
import { describe, it, expect } from 'vitest';

import {
  buildCheckItems,
  allChecksPassed,
  canGenerate,
  isTerminalStatus,
  retryState,
  SIMULATED_PASSING_CHECKS,
  type ValidationChecks,
  type ExportStatus,
  type ExportWireStatus,
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

// ── isTerminalStatus ───────────────────────────────────────────────────────────

describe('isTerminalStatus', () => {
  it('should return true for status=ready', () => {
    expect(isTerminalStatus('ready')).toBe(true);
  });

  it('should return true for status=failed', () => {
    expect(isTerminalStatus('failed')).toBe(true);
  });

  it('should return false for status=pending', () => {
    expect(isTerminalStatus('pending')).toBe(false);
  });

  it('both terminal statuses should cause clearInterval (proof by enum exhaustion)', () => {
    const terminalStatuses: ExportWireStatus[] = ['ready', 'failed'];
    const nonTerminalStatuses: ExportWireStatus[] = ['pending'];
    terminalStatuses.forEach(s => expect(isTerminalStatus(s)).toBe(true));
    nonTerminalStatuses.forEach(s => expect(isTerminalStatus(s)).toBe(false));
  });
});

// ── retryState ─────────────────────────────────────────────────────────────────

describe('retryState', () => {
  it('should return status idle', () => {
    expect(retryState().status).toBe('idle');
  });

  it('should return downloadUrl null', () => {
    expect(retryState().downloadUrl).toBeNull();
  });

  it('should NOT have a progress field (no progress_pct on the wire)', () => {
    const state = retryState();
    expect('progress' in state).toBe(false);
  });
});

// ── SIMULATED_PASSING_CHECKS ───────────────────────────────────────────────────

describe('SIMULATED_PASSING_CHECKS (display-only per GAP-1 Option A)', () => {
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

// ── Wire status contract ───────────────────────────────────────────────────────

describe('ExportWireStatus type contract', () => {
  it('pending is a non-terminal status', () => {
    const s: ExportWireStatus = 'pending';
    expect(isTerminalStatus(s)).toBe(false);
  });

  it('ready is a terminal status', () => {
    const s: ExportWireStatus = 'ready';
    expect(isTerminalStatus(s)).toBe(true);
  });

  it('failed is a terminal status', () => {
    const s: ExportWireStatus = 'failed';
    expect(isTerminalStatus(s)).toBe(true);
  });
});

// ── ExportStatus UI-local type exhaustion ──────────────────────────────────────

describe('ExportStatus (UI-local)', () => {
  it('idle is the initial state', () => {
    const s: ExportStatus = 'idle';
    expect(canGenerate(s, SIMULATED_PASSING_CHECKS)).toBe(true);
  });

  it('processing prevents canGenerate', () => {
    const s: ExportStatus = 'processing';
    expect(canGenerate(s, SIMULATED_PASSING_CHECKS)).toBe(false);
  });

  it('ready prevents canGenerate', () => {
    const s: ExportStatus = 'ready';
    expect(canGenerate(s, SIMULATED_PASSING_CHECKS)).toBe(false);
  });

  it('failed prevents canGenerate', () => {
    const s: ExportStatus = 'failed';
    expect(canGenerate(s, SIMULATED_PASSING_CHECKS)).toBe(false);
  });
});

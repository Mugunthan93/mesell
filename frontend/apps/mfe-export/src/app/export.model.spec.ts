/**
 * export.model.ts — pure-function and type-contract unit tests.
 *
 * PR #291 delta:
 * - REMOVED: buildCheckItems, allChecksPassed, SIMULATED_PASSING_CHECKS, ValidationChecks
 *   (simulated display-only checklist retired; real gate is backend 422 failed_checks[])
 * - ADDED: ExportFailedCheck, EXPORT_CHECK_MESSAGES, EXPORT_CHECK_FALLBACK, resolveCheckMessage
 * - UPDATED: canGenerate — now single-arg (status only), no checks parameter
 * - RETAINED: isTerminalStatus, retryState, ExportWireStatus, ExportStatus
 *
 * TestBed is intentionally NOT used — pure functions have no Angular dependencies.
 */
import { describe, it, expect } from 'vitest';

import {
  canGenerate,
  isTerminalStatus,
  retryState,
  resolveCheckMessage,
  EXPORT_CHECK_MESSAGES,
  EXPORT_CHECK_FALLBACK,
  type ExportFailedCheck,
  type ExportStatus,
  type ExportWireStatus,
} from './export.model';

// ── canGenerate ────────────────────────────────────────────────────────────────

describe('canGenerate', () => {
  it('should return true when status is idle', () => {
    expect(canGenerate('idle')).toBe(true);
  });

  it('should return false when status is processing', () => {
    expect(canGenerate('processing')).toBe(false);
  });

  it('should return false when status is ready', () => {
    expect(canGenerate('ready')).toBe(false);
  });

  it('should return false when status is failed', () => {
    expect(canGenerate('failed')).toBe(false);
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

// ── resolveCheckMessage ────────────────────────────────────────────────────────

describe('resolveCheckMessage', () => {
  it('should resolve export.check.quality_status to a non-empty string', () => {
    const check: ExportFailedCheck = {
      check_id: 'quality_status',
      message_key: 'export.check.quality_status',
    };
    const msg = resolveCheckMessage(check);
    expect(msg.length).toBeGreaterThan(0);
    expect(msg).not.toBe(EXPORT_CHECK_FALLBACK);
    expect(msg).toBe(EXPORT_CHECK_MESSAGES['export.check.quality_status']);
  });

  it('should resolve export.check.front_image_missing to a non-empty string', () => {
    const check: ExportFailedCheck = {
      check_id: 'front_image_missing',
      message_key: 'export.check.front_image_missing',
    };
    const msg = resolveCheckMessage(check);
    expect(msg.length).toBeGreaterThan(0);
    expect(msg).not.toBe(EXPORT_CHECK_FALLBACK);
    expect(msg).toBe(EXPORT_CHECK_MESSAGES['export.check.front_image_missing']);
  });

  it('should return EXPORT_CHECK_FALLBACK for unknown message_key (never blank)', () => {
    const check: ExportFailedCheck = {
      check_id: 'some_unknown_check',
      message_key: 'export.check.unknown_key_xyz',
    };
    const msg = resolveCheckMessage(check);
    expect(msg).toBe(EXPORT_CHECK_FALLBACK);
    expect(msg.length).toBeGreaterThan(0);
  });

  it('should return EXPORT_CHECK_FALLBACK for empty string message_key', () => {
    const check: ExportFailedCheck = { check_id: 'x', message_key: '' };
    const msg = resolveCheckMessage(check);
    expect(msg).toBe(EXPORT_CHECK_FALLBACK);
  });

  it('EXPORT_CHECK_FALLBACK must not contain a raw message_key (no key bleed)', () => {
    const check: ExportFailedCheck = {
      check_id: 'x',
      message_key: 'export.check.not_in_map',
    };
    const msg = resolveCheckMessage(check);
    expect(msg).not.toContain('export.check.not_in_map');
  });
});

// ── EXPORT_CHECK_MESSAGES contract ────────────────────────────────────────────

describe('EXPORT_CHECK_MESSAGES', () => {
  it('should have a non-empty entry for export.check.quality_status', () => {
    expect(EXPORT_CHECK_MESSAGES['export.check.quality_status']).toBeTruthy();
  });

  it('should have a non-empty entry for export.check.front_image_missing', () => {
    expect(EXPORT_CHECK_MESSAGES['export.check.front_image_missing']).toBeTruthy();
  });

  it('all entries should be non-empty strings (no blanks in map)', () => {
    Object.values(EXPORT_CHECK_MESSAGES).forEach(msg => {
      expect(msg.length).toBeGreaterThan(0);
    });
  });
});

// ── EXPORT_CHECK_FALLBACK contract ────────────────────────────────────────────

describe('EXPORT_CHECK_FALLBACK', () => {
  it('should be a non-empty string', () => {
    expect(EXPORT_CHECK_FALLBACK.length).toBeGreaterThan(0);
  });

  it('should NOT contain a raw message key (acts as user-facing text only)', () => {
    expect(EXPORT_CHECK_FALLBACK).not.toContain('export.check.');
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
  it('idle is the only status where canGenerate returns true', () => {
    const allStatuses: ExportStatus[] = ['idle', 'processing', 'ready', 'failed'];
    const idleOnly = allStatuses.filter(s => canGenerate(s));
    expect(idleOnly).toEqual(['idle']);
  });

  it('idle is the initial state (canGenerate returns true)', () => {
    const s: ExportStatus = 'idle';
    expect(canGenerate(s)).toBe(true);
  });

  it('processing prevents canGenerate', () => {
    const s: ExportStatus = 'processing';
    expect(canGenerate(s)).toBe(false);
  });

  it('ready prevents canGenerate', () => {
    const s: ExportStatus = 'ready';
    expect(canGenerate(s)).toBe(false);
  });

  it('failed prevents canGenerate', () => {
    const s: ExportStatus = 'failed';
    expect(canGenerate(s)).toBe(false);
  });
});

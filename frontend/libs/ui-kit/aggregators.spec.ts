/**
 * Aggregator membership assertions — Phase 2 (UI Design-System Decoupling)
 *
 * These are static-value assertions: no TestBed, no Angular Zone, no DOM.
 * They verify the exact composition of the seven aggregator arrays so that a
 * future barrel edit cannot silently break the membership or count invariants.
 */
import { describe, it, expect } from 'vitest';

import {
  MEE_FORM,
  MEE_OVERLAY,
  MEE_FEEDBACK,
  MEE_DATA,
  MEE_COMMON,
  MEE_FILE,
  MEE_UI_ALL,
} from './aggregators';

// Import services to assert they are NOT in any array (compile-time guarantee
// is already enforced by the `readonly Type<unknown>[]` typing, but the runtime
// assertion documents intent and survives a typing regression).
import { MeeToastService }   from './toast/toast.service';
import { MeeConfirmService } from './confirm-dialog/confirm-dialog.component';

// Import specific components to assert explicit membership.
import { MeeIconComponent }  from './icon/icon.component';

describe('MEE_FORM', () => {
  it('has exactly 6 members', () => {
    expect(MEE_FORM.length).toBe(6);
  });
});

describe('MEE_OVERLAY', () => {
  it('has exactly 3 members', () => {
    expect(MEE_OVERLAY.length).toBe(3);
  });
});

describe('MEE_FEEDBACK', () => {
  it('has exactly 5 members', () => {
    expect(MEE_FEEDBACK.length).toBe(5);
  });
});

describe('MEE_DATA', () => {
  it('has exactly 2 members', () => {
    expect(MEE_DATA.length).toBe(2);
  });
});

describe('MEE_COMMON', () => {
  it('has exactly 4 members', () => {
    expect(MEE_COMMON.length).toBe(4);
  });

  it('includes MeeIconComponent (Phase 1 addition — explicit guard)', () => {
    // Prevent a future barrel/aggregator edit from silently dropping mee-icon.
    expect(MEE_COMMON).toContain(MeeIconComponent);
  });
});

describe('MEE_FILE', () => {
  it('has exactly 1 member', () => {
    expect(MEE_FILE.length).toBe(1);
  });
});

describe('MEE_UI_ALL', () => {
  it('has exactly 21 members (6+3+5+2+4+1)', () => {
    expect(MEE_UI_ALL.length).toBe(21);
  });

  it('has no duplicate entries (set size === 21)', () => {
    expect(new Set(MEE_UI_ALL).size).toBe(21);
  });

  it('does NOT include MeeToastService (provider — must stay out of imports[])', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((MEE_UI_ALL as readonly any[]).includes(MeeToastService)).toBe(false);
  });

  it('does NOT include MeeConfirmService (provider — must stay out of imports[])', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((MEE_UI_ALL as readonly any[]).includes(MeeConfirmService)).toBe(false);
  });
});

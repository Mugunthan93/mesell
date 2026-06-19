/**
 * Aggregator membership assertions — Phase 2 (UI Design-System Decoupling)
 *
 * These are static-value assertions: no TestBed, no Angular Zone, no DOM.
 * They verify the exact composition of the eight aggregator arrays so that a
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
  MEE_SURFACE,
  MEE_UI_ALL,
} from './aggregators';

// Import services to assert they are NOT in any array (compile-time guarantee
// is already enforced by the `readonly Type<unknown>[]` typing, but the runtime
// assertion documents intent and survives a typing regression).
import { MeeToastService }   from './toast/toast.service';
import { MeeConfirmService } from './confirm-dialog/confirm-dialog.component';

// Import specific components to assert explicit membership.
import { MeeIconComponent }       from './icon/icon.component';
import { MeeCheckboxComponent }   from './checkbox/checkbox.component';
import { MeeRadioComponent }      from './radio/radio.component';
import { MeeBreadcrumbComponent } from './breadcrumb/breadcrumb.component';
import { MeeTabsComponent }       from './tabs/tabs.component';
import { MeeMessageComponent }    from './message/message.component';
import { MeePanelComponent }      from './panel/panel.component';
import { MeeDividerComponent }    from './divider/divider.component';
import { MeeScrollPanelComponent } from './scroll-panel/scroll-panel.component';

describe('MEE_FORM', () => {
  it('has exactly 8 members (6 original + checkbox + radio)', () => {
    expect(MEE_FORM.length).toBe(8);
  });

  it('includes MeeCheckboxComponent', () => {
    expect(MEE_FORM).toContain(MeeCheckboxComponent);
  });

  it('includes MeeRadioComponent', () => {
    expect(MEE_FORM).toContain(MeeRadioComponent);
  });
});

describe('MEE_OVERLAY', () => {
  it('has exactly 3 members', () => {
    expect(MEE_OVERLAY.length).toBe(3);
  });
});

describe('MEE_FEEDBACK', () => {
  it('has exactly 6 members (5 original + message)', () => {
    expect(MEE_FEEDBACK.length).toBe(6);
  });

  it('includes MeeMessageComponent', () => {
    expect(MEE_FEEDBACK).toContain(MeeMessageComponent);
  });
});

describe('MEE_DATA', () => {
  it('has exactly 3 members (2 original + tabs)', () => {
    expect(MEE_DATA.length).toBe(3);
  });

  it('includes MeeTabsComponent', () => {
    expect(MEE_DATA).toContain(MeeTabsComponent);
  });
});

describe('MEE_COMMON', () => {
  it('has exactly 5 members (4 original + breadcrumb)', () => {
    expect(MEE_COMMON.length).toBe(5);
  });

  it('includes MeeIconComponent (Phase 1 addition — explicit guard)', () => {
    expect(MEE_COMMON).toContain(MeeIconComponent);
  });

  it('includes MeeBreadcrumbComponent', () => {
    expect(MEE_COMMON).toContain(MeeBreadcrumbComponent);
  });
});

describe('MEE_FILE', () => {
  it('has exactly 1 member', () => {
    expect(MEE_FILE.length).toBe(1);
  });
});

describe('MEE_SURFACE', () => {
  it('has exactly 3 members (panel + divider + scroll-panel)', () => {
    expect(MEE_SURFACE.length).toBe(3);
  });

  it('includes MeePanelComponent', () => {
    expect(MEE_SURFACE).toContain(MeePanelComponent);
  });

  it('includes MeeDividerComponent', () => {
    expect(MEE_SURFACE).toContain(MeeDividerComponent);
  });

  it('includes MeeScrollPanelComponent', () => {
    expect(MEE_SURFACE).toContain(MeeScrollPanelComponent);
  });
});

describe('MEE_UI_ALL', () => {
  it('has exactly 29 members (8+3+6+3+5+1+3)', () => {
    expect(MEE_UI_ALL.length).toBe(29);
  });

  it('has no duplicate entries (set size === 29)', () => {
    expect(new Set(MEE_UI_ALL).size).toBe(29);
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

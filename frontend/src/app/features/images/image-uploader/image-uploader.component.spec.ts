// image-uploader.component.spec.ts
//
// Proven workaround: extract business logic into image-uploader.model.ts (pure TypeScript,
// no Angular decorators). Write Vitest tests against pure functions.
// This avoids the Angular 21 + Vitest TestBed crash:
//   "Cannot read properties of null (reading 'ngModule')"
// which occurs when TestBed processes standalone components that transitively import
// PrimeNG 21 standalone components (PrimeNG has NG_COMP_DEF but no NG_MOD_DEF).
//
// All dispatch gates are covered via pure function semantics.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import {
  buildPrecheckItems,
  slotProgress,
  computeCanContinue,
  computeActiveExpandedImage,
  toggleExpandedSlot,
  addSlots,
  resetSlot,
  applySimulationResult,
  statusForMeeStatusBadge,
  ProductImage,
  PrecheckItem,
  PRECHECK_HINTS,
  PRECHECK_LABELS,
} from './image-uploader.model';

// ── Test data helpers ─────────────────────────────────────────────────────────

function makePassImage(slotIndex = 0): ProductImage {
  return {
    id:          `pass-${slotIndex}`,
    slot_index:  slotIndex,
    gcs_url:     null,
    status:      'pass',
    precheck: {
      jpeg_format:     true,
      color_space_rgb: true,
      min_resolution:  true,
      white_bg:        true,
      no_watermark:    true,
    },
  };
}

function makeFailImage(slotIndex = 1): ProductImage {
  return {
    id:          `fail-${slotIndex}`,
    slot_index:  slotIndex,
    gcs_url:     null,
    status:      'fail',
    precheck: {
      jpeg_format:     true,
      color_space_rgb: false,   // CMYK fail — journey step 7
      min_resolution:  true,
      white_bg:        true,
      no_watermark:    true,
    },
  };
}

function makePendingImage(slotIndex = 0): ProductImage {
  return {
    id:         `pending-${slotIndex}`,
    slot_index: slotIndex,
    gcs_url:    null,
    status:     'pending',
    precheck:   null,
  };
}

// ── Gate 1: buildPrecheckItems — 5-check matrix ───────────────────────────────

describe('buildPrecheckItems()', () => {
  it('returns 5 items for a fully resolved image', () => {
    const items = buildPrecheckItems(makePassImage());
    expect(items).toHaveLength(5);
  });

  it('marks color_space_rgb as fail with CMYK hint for slot-1 simulation', () => {
    const items = buildPrecheckItems(makeFailImage());
    const rgb   = items.find((i: PrecheckItem) => i.key === 'color_space_rgb');
    expect(rgb).toBeDefined();
    expect(rgb!.pass).toBe(false);
    expect(rgb!.hint).toBe(PRECHECK_HINTS.color_space_rgb);
    expect(rgb!.hint).toContain('CMYK detected');
  });

  it('returns empty array when precheck is null (pending image)', () => {
    expect(buildPrecheckItems(makePendingImage())).toHaveLength(0);
  });

  it('all 5 items pass for a fully passing image', () => {
    const items = buildPrecheckItems(makePassImage());
    expect(items.every((i: PrecheckItem) => i.pass)).toBe(true);
  });

  it('hint is null for every passing check', () => {
    const items = buildPrecheckItems(makePassImage());
    expect(items.every((i: PrecheckItem) => i.hint === null)).toBe(true);
  });

  it('returns correct label for each check key', () => {
    const items = buildPrecheckItems(makePassImage());
    for (const item of items) {
      expect(item.label).toBe(PRECHECK_LABELS[item.key]);
    }
  });

  it('hint is non-null for every failing check', () => {
    // Image where ALL checks fail
    const allFail: ProductImage = {
      ...makePassImage(),
      status: 'fail',
      precheck: {
        jpeg_format: false,
        color_space_rgb: false,
        min_resolution: false,
        white_bg: false,
        no_watermark: false,
      },
    };
    const items = buildPrecheckItems(allFail);
    expect(items.every((i: PrecheckItem) => i.hint !== null)).toBe(true);
  });
});

// ── Gate 2: slotProgress — progress bar animation ────────────────────────────

describe('slotProgress()', () => {
  it('returns 0 for a pending image', () => {
    expect(slotProgress(makePendingImage())).toBe(0);
  });

  it('returns 100 for a passed image', () => {
    expect(slotProgress(makePassImage())).toBe(100);
  });

  it('returns 100 for a failed image (CMYK fail)', () => {
    expect(slotProgress(makeFailImage())).toBe(100);
  });
});

// ── Gate 3: computeCanContinue — navigation gate ─────────────────────────────

describe('computeCanContinue()', () => {
  it('returns false for empty images array', () => {
    expect(computeCanContinue([])).toBe(false);
  });

  it('returns false when any image has status "fail"', () => {
    expect(computeCanContinue([makePassImage(0), makeFailImage(1)])).toBe(false);
  });

  it('returns false when any image has status "pending"', () => {
    expect(computeCanContinue([makePassImage(0), makePendingImage(1)])).toBe(false);
  });

  it('returns true only when all images have status "pass"', () => {
    expect(computeCanContinue([makePassImage(0), makePassImage(1)])).toBe(true);
  });

  it('slot 1 CMYK fail blocks canContinue (journey step 7)', () => {
    // Dispatch spec: slot 1 fails color_space_rgb — must block "Continue to Preview"
    const images = [makePassImage(0), makeFailImage(1), makePassImage(2), makePassImage(3)];
    expect(computeCanContinue(images)).toBe(false);
  });
});

// ── Gate 4: computeActiveExpandedImage — precheck report panel ───────────────

describe('computeActiveExpandedImage()', () => {
  it('returns null when expandedSlot is null', () => {
    expect(computeActiveExpandedImage([makePassImage(0)], null)).toBeNull();
  });

  it('returns the image matching expandedSlot index', () => {
    const images = [makePassImage(0), makeFailImage(1)];
    const result = computeActiveExpandedImage(images, 1);
    expect(result?.slot_index).toBe(1);
  });

  it('returns null when expandedSlot does not match any image', () => {
    const images = [makePassImage(0)];
    expect(computeActiveExpandedImage(images, 5)).toBeNull();
  });
});

// ── Gate 5: toggleExpandedSlot — expand/collapse toggle ──────────────────────

describe('toggleExpandedSlot()', () => {
  it('sets expandedSlot to index when current is null', () => {
    expect(toggleExpandedSlot(null, 1)).toBe(1);
  });

  it('collapses to null when same index is clicked again', () => {
    expect(toggleExpandedSlot(1, 1)).toBeNull();
  });

  it('switches to new index without collapsing', () => {
    expect(toggleExpandedSlot(0, 2)).toBe(2);
  });
});

// ── addSlots — max-6 enforcement ─────────────────────────────────────────────

describe('addSlots()', () => {
  it('adds new pending slots for each file name', () => {
    const slots = addSlots([], ['img0.jpg', 'img1.jpg']);
    expect(slots).toHaveLength(2);
    expect(slots[0].status).toBe('pending');
    expect(slots[0].precheck).toBeNull();
    expect(slots[0].slot_index).toBe(0);
    expect(slots[1].slot_index).toBe(1);
  });

  it('enforces max 6 total — truncates overflow files', () => {
    const existing = [
      makePassImage(0), makePassImage(1), makePassImage(2),
      makePassImage(3), makePassImage(4),
    ];
    const slots = addSlots(existing, ['a.jpg', 'b.jpg', 'c.jpg']);
    expect(slots).toHaveLength(1);
    expect(slots[0].slot_index).toBe(5);
  });

  it('returns empty array when already at max 6', () => {
    const existing = Array.from({ length: 6 }, (_, i) => makePassImage(i));
    expect(addSlots(existing, ['x.jpg'])).toHaveLength(0);
  });

  it('new slots have status "pending" and precheck null', () => {
    const slots = addSlots([], ['test.jpg']);
    expect(slots[0].status).toBe('pending');
    expect(slots[0].precheck).toBeNull();
    expect(slots[0].gcs_url).toBeNull();
  });
});

// ── resetSlot — re-upload ──────────────────────────────────────────────────────

describe('resetSlot()', () => {
  it('resets targeted slot to pending with null precheck', () => {
    const images = [makePassImage(0), makeFailImage(1)];
    const result = resetSlot(images, 1);
    expect(result[1].status).toBe('pending');
    expect(result[1].precheck).toBeNull();
  });

  it('leaves other slots untouched', () => {
    const images = [makePassImage(0), makeFailImage(1)];
    const result = resetSlot(images, 1);
    expect(result[0].status).toBe('pass');
    expect(result[0].slot_index).toBe(0);
  });

  it('returns a new array (immutable)', () => {
    const images = [makePassImage(0)];
    const result = resetSlot(images, 0);
    expect(result).not.toBe(images);
  });
});

// ── applySimulationResult ──────────────────────────────────────────────────────

describe('applySimulationResult()', () => {
  it('sets slot to pass when all precheck values are true', () => {
    const images  = [makePendingImage(0)];
    const precheck = { jpeg_format: true, color_space_rgb: true, min_resolution: true, white_bg: true, no_watermark: true };
    const result  = applySimulationResult(images, 0, precheck);
    expect(result[0].status).toBe('pass');
    expect(result[0].precheck).toEqual(precheck);
  });

  it('sets slot to fail when color_space_rgb is false (CMYK simulation, slot 1)', () => {
    const images  = [makePendingImage(0), makePendingImage(1)];
    const precheck = { jpeg_format: true, color_space_rgb: false, min_resolution: true, white_bg: true, no_watermark: true };
    const result  = applySimulationResult(images, 1, precheck);
    expect(result[1].status).toBe('fail');
    expect(result[1].precheck?.color_space_rgb).toBe(false);
  });

  it('leaves other slots unchanged (immutable)', () => {
    const images  = [makePendingImage(0), makePendingImage(1)];
    const precheck = { jpeg_format: true, color_space_rgb: true, min_resolution: true, white_bg: true, no_watermark: true };
    const result  = applySimulationResult(images, 0, precheck);
    expect(result[1].status).toBe('pending');
    expect(result).not.toBe(images);
  });
});

// ── statusForMeeStatusBadge ────────────────────────────────────────────────────

describe('statusForMeeStatusBadge()', () => {
  it('maps "pass" to "ready"', () => {
    expect(statusForMeeStatusBadge('pass')).toBe('ready');
  });

  it('maps "fail" to "failed"', () => {
    expect(statusForMeeStatusBadge('fail')).toBe('failed');
  });

  it('maps "pending" to "pending"', () => {
    expect(statusForMeeStatusBadge('pending')).toBe('pending');
  });
});

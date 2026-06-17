/**
 * icon.swap.spec.ts — Phase 7 swap-proof assertions (vitest, no Angular TestBed)
 *
 * Asserts that:
 *   1. Alt theme preset is a distinct object from the default preset (module independence)
 *   2. ActiveIcons is the same reference as MEE_ICONS (default state — no swap active)
 *   3. MEE_ICONS_ALT has the same set of keys as MEE_ICONS (key parity)
 *   4. Every MEE_ICONS_ALT value is a non-empty string containing 'material-icons'
 *   5. No MEE_ICONS_ALT value matches the FE-2 forbidden pattern /pi\s+pi-[a-z]/
 *   6. Every MeeIconName resolves to a defined non-empty string in MEE_ICONS_ALT
 */
import { describe, it, expect } from 'vitest';

import { MeeSellPreset }    from '../theme';
import { MeeSellAltPreset } from '../theme.alt';
import { MEE_ICONS }        from './icon.registry';
import { MEE_ICONS_ALT }    from './icon.registry.alt';
import { ActiveIcons }      from './icon.selector';

// ── FE-2 forbidden pattern (mirrors fe2_no_raw_pi_icons.mjs scanner rule) ──
const PI_RE = /pi\s+pi-[a-z]/;

// ── 1. Module independence — theme presets are distinct objects ──────────────
describe('Phase 7 — theme preset independence', () => {
  it('MeeSellAltPreset !== MeeSellPreset (distinct objects, not the same reference)', () => {
    expect(MeeSellAltPreset).not.toBe(MeeSellPreset);
  });

  it('MeeSellAltPreset is defined and is an object', () => {
    expect(MeeSellAltPreset).toBeDefined();
    expect(typeof MeeSellAltPreset).toBe('object');
  });

  it('MeeSellPreset is defined and is an object', () => {
    expect(MeeSellPreset).toBeDefined();
    expect(typeof MeeSellPreset).toBe('object');
  });
});

// ── 2. Default state — ActiveIcons is MEE_ICONS (same reference) ─────────────
describe('Phase 7 — icon selector default state', () => {
  it('ActiveIcons === MEE_ICONS (selector points at primary registry by default)', () => {
    expect(ActiveIcons).toBe(MEE_ICONS);
  });
});

// ── 3. Key parity — alt registry has exactly the same keys as primary ─────────
describe('Phase 7 — MEE_ICONS_ALT key parity', () => {
  it('Object.keys(MEE_ICONS_ALT).sort() deep-equals Object.keys(MEE_ICONS).sort()', () => {
    expect(Object.keys(MEE_ICONS_ALT).sort()).toEqual(Object.keys(MEE_ICONS).sort());
  });

  it('MEE_ICONS_ALT has the same number of entries as MEE_ICONS', () => {
    expect(Object.keys(MEE_ICONS_ALT).length).toBe(Object.keys(MEE_ICONS).length);
  });
});

// ── 4. All alt values contain 'material-icons' ───────────────────────────────
describe('Phase 7 — MEE_ICONS_ALT values are Material Icons strings', () => {
  for (const [key, value] of Object.entries(MEE_ICONS_ALT)) {
    it(`MEE_ICONS_ALT["${key}"] is a non-empty string containing 'material-icons'`, () => {
      expect(typeof value).toBe('string');
      expect(value.length).toBeGreaterThan(0);
      expect(value).toContain('material-icons');
    });
  }
});

// ── 5. FE-2 clean — no alt value matches /pi\s+pi-[a-z]/ ────────────────────
describe('Phase 7 — FE-2 contract: MEE_ICONS_ALT has no pi pi-* strings', () => {
  it('no MEE_ICONS_ALT value matches the FE-2 forbidden pattern /pi\\s+pi-[a-z]/', () => {
    const violations = Object.entries(MEE_ICONS_ALT)
      .filter(([, value]) => PI_RE.test(value))
      .map(([key]) => key);

    expect(violations).toEqual([]);
  });

  for (const [key, value] of Object.entries(MEE_ICONS_ALT)) {
    it(`MEE_ICONS_ALT["${key}"] does not contain a raw pi pi-* class`, () => {
      expect(PI_RE.test(value)).toBe(false);
    });
  }
});

// ── 6. All MeeIconName keys resolve to defined non-empty strings in alt ───────
describe('Phase 7 — every MeeIconName resolves in MEE_ICONS_ALT', () => {
  for (const key of Object.keys(MEE_ICONS) as Array<keyof typeof MEE_ICONS>) {
    it(`MeeIconName "${key}" resolves to a defined non-empty string in MEE_ICONS_ALT`, () => {
      const resolved = MEE_ICONS_ALT[key];
      expect(resolved).toBeDefined();
      expect(typeof resolved).toBe('string');
      expect(resolved.length).toBeGreaterThan(0);
    });
  }
});

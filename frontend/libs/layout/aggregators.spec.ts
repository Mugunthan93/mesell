/**
 * Aggregator membership assertions — Phase 3 (UI Design-System Decoupling)
 *
 * These are static-value assertions: no TestBed, no Angular Zone, no DOM.
 * They verify the exact composition of MEE_LAYOUT so that a future barrel
 * edit cannot silently break the membership or count invariants.
 *
 * The spread type-check (`[...MEE_LAYOUT]` in a component imports) is a
 * compile-time invariant enforced by:
 *   `as const satisfies readonly Type<unknown>[]`
 * in aggregators.ts — tsc (invoked via `npx tsc -p tsconfig.json --noEmit`)
 * catches any type regression; we do not need a TestBed throwaway here.
 */
import { describe, it, expect } from 'vitest';
import { Type } from '@angular/core';

import { MEE_LAYOUT } from './aggregators';
import { MeePageComponent }       from './page/page.component';
import { MeeSectionComponent }    from './section/section.component';
import { MeeToolbarComponent }    from './toolbar/toolbar.component';
import { MeeGridComponent }       from './grid/grid.component';
import { MeeStackComponent }      from './stack/stack.component';
import { MeeFormLayoutComponent } from './form-layout/form-layout.component';

describe('MEE_LAYOUT', () => {
  it('has exactly 6 members', () => {
    expect(MEE_LAYOUT.length).toBe(6);
  });

  it('has no duplicate entries (set size === 6)', () => {
    expect(new Set(MEE_LAYOUT).size).toBe(6);
  });

  it('includes MeePageComponent', () => {
    expect(MEE_LAYOUT).toContain(MeePageComponent);
  });

  it('includes MeeSectionComponent', () => {
    expect(MEE_LAYOUT).toContain(MeeSectionComponent);
  });

  it('includes MeeToolbarComponent', () => {
    expect(MEE_LAYOUT).toContain(MeeToolbarComponent);
  });

  it('includes MeeGridComponent', () => {
    expect(MEE_LAYOUT).toContain(MeeGridComponent);
  });

  it('includes MeeStackComponent', () => {
    expect(MEE_LAYOUT).toContain(MeeStackComponent);
  });

  it('includes MeeFormLayoutComponent', () => {
    expect(MEE_LAYOUT).toContain(MeeFormLayoutComponent);
  });

  it('satisfies readonly Type<unknown>[] constraint (runtime-visible typing proof)', () => {
    // This assignment is the runtime-visible form of
    // `as const satisfies readonly Type<unknown>[]` in aggregators.ts.
    // If the typing regresses, tsc --noEmit will catch it before this test runs.
    const typed: readonly Type<unknown>[] = MEE_LAYOUT;
    expect(typed).toBeTruthy();
    expect(typed.length).toBe(6);
  });
});

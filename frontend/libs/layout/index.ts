/**
 * @mesell/layout — Phase 0 scaffolding.
 *
 * This lib is the MIDDLE tier in the three-tier MeeSell design-system DAG:
 *   @mesell/ui-kit (rank 0, atoms + PrimeNG wrappers)
 *       ↑
 *   @mesell/layout (rank 1, page primitives + chrome primitives)  ← you are here
 *       ↑
 *   @mesell/composites (rank 2, composed cross-lib patterns)
 *
 * Page primitives (`mee-page`, `mee-section`, `mee-toolbar`, `mee-grid`,
 * `mee-stack`, `mee-form-layout`) landed in Phase 3 — see below.
 *
 * Chrome primitives (`MeeAppBarComponent`, `MeeSideNavComponent`,
 * `MeeNavItemComponent`, `MeeUserMenuComponent`) landed in Phase 4 — see below.
 * `ShellComponent` remains a host singleton in `apps/shell` and must NOT
 * be imported by any MFE — FE-3 enforces this at CI.
 *
 * DO NOT add PrimeNG / @primeuix imports here directly — route through
 * @mesell/ui-kit wrappers so the PrimeNG seal (FE-1) is preserved.
 *
 * Phase 3: page primitives shipped — see Page primitives section below.
 * Phase 4: chrome primitives shipped — exported from this barrel ROOT but
 *   SHELL-ONLY. FE-3 (fe3_chrome_shell_only.mjs) seals them by symbol name so
 *   MFEs cannot import them; only apps/shell composes the chrome. There is
 *   deliberately NO MEE_CHROME aggregator (an aggregator symbol would bypass
 *   the FE-3 symbol seal).
 */

// ---------------------------------------------------------------------------
// MEE_LAYOUT aggregator — spread into standalone component imports
// ---------------------------------------------------------------------------
export { MEE_LAYOUT } from './aggregators';

// ---------------------------------------------------------------------------
// Page primitives (Phase 3)
// ---------------------------------------------------------------------------
export { MeePageComponent }       from './page/page.component';
export { MeeSectionComponent }    from './section/section.component';
export { MeeToolbarComponent }    from './toolbar/toolbar.component';
export { MeeGridComponent }       from './grid/grid.component';
export { MeeStackComponent }      from './stack/stack.component';
export { MeeFormLayoutComponent } from './form-layout/form-layout.component';

// ---------------------------------------------------------------------------
// Chrome primitives (Phase 4) — SHELL-ONLY (FE-3 sealed; MFEs must NOT import).
// Exported from the barrel root (keeps the shell's import FE-5 barrel-clean);
// MFE misuse is caught by FE-3's chrome symbol-name seal. No MEE_CHROME array.
// ---------------------------------------------------------------------------
export { MeeAppBarComponent }   from './chrome/app-bar/app-bar.component';
export { MeeSideNavComponent }  from './chrome/side-nav/side-nav.component';
export { MeeNavItemComponent }  from './chrome/nav-item/nav-item.component';
export { MeeUserMenuComponent } from './chrome/user-menu/user-menu.component';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------
export type { MeeLayoutGap, MeePageMaxWidth, MeeFormMaxWidth } from './layout.types';
export type { MeeToolbarAlign }   from './toolbar/toolbar.component';
export type { MeeGridCols }       from './grid/grid.component';
export type { MeeStackDirection, MeeStackAlign, MeeStackJustify } from './stack/stack.component';
export type { MeeNavItem, MeeNavGroup } from './chrome/chrome.types';

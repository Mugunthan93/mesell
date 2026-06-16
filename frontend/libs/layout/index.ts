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
 * `MeeNavItemComponent`, `MeeUserMenuComponent`) land in Phase 4.
 * `ShellComponent` remains a host singleton in `apps/shell` and must NOT
 * be imported by any MFE — FE-3 enforces this at CI.
 *
 * DO NOT add PrimeNG / @primeuix imports here directly — route through
 * @mesell/ui-kit wrappers so the PrimeNG seal (FE-1) is preserved.
 *
 * Phase 3: page primitives shipped — see Page primitives section below.
 * TODO(Phase 4): add chrome primitives (app-bar, side-nav, nav-item, user-menu)
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
// Public types
// ---------------------------------------------------------------------------
export type { MeeLayoutGap, MeePageMaxWidth, MeeFormMaxWidth } from './layout.types';
export type { MeeToolbarAlign }   from './toolbar/toolbar.component';
export type { MeeGridCols }       from './grid/grid.component';
export type { MeeStackDirection, MeeStackAlign, MeeStackJustify } from './stack/stack.component';

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
 * `mee-form-layout`) land in Phase 3 and are spread from this barrel into
 * standalone component `imports`.
 *
 * Chrome primitives (`MeeAppBarComponent`, `MeeSideNavComponent`,
 * `MeeNavItemComponent`, `MeeUserMenuComponent`) land in Phase 4.
 * `ShellComponent` remains a host singleton in `apps/shell` and must NOT
 * be imported by any MFE — FE-3 enforces this at CI.
 *
 * DO NOT add PrimeNG / @primeuix imports here directly — route through
 * @mesell/ui-kit wrappers so the PrimeNG seal (FE-1) is preserved.
 *
 * TODO(Phase 3): add mee-page, mee-section, mee-toolbar, mee-grid, mee-form-layout
 * TODO(Phase 4): add chrome primitives (app-bar, side-nav, nav-item, user-menu)
 */

/**
 * MEE_LAYOUT — aggregator array for the layout tier.
 *
 * Phase 0: empty placeholder (no components yet).
 * Phase 3+: spread into standalone `imports` alongside MEE_FORM, MEE_FEEDBACK etc.
 *
 * Usage (Phase 3+):
 *   @Component({ imports: [...MEE_LAYOUT, ...MEE_FORM] })
 */
export const MEE_LAYOUT: readonly never[] = [] as const;

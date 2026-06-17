import type { MeeIconName } from '@mesell/ui-kit';

/**
 * @mesell/layout — chrome nav contract types (Phase 4, UI Design-System Decoupling)
 *
 * The presentational contract between the host `ShellComponent` (which owns the
 * nav DATA + AuthService wiring) and the `mee-side-nav` / `mee-nav-item` chrome
 * primitives (which render it). The shell maps its richer internal nav model
 * (with `prefixMatch` + `visible` predicates) down to this clean shape:
 * it applies the `visible` predicate, drops empty groups, and maps
 * `prefixMatch → exact: !prefixMatch` BEFORE passing `MeeNavGroup[]` in.
 *
 * Chrome is SHELL-ONLY (FE-3). MFEs must never import these or the components
 * that consume them.
 */

/** A single navigable sidebar entry. */
export interface MeeNavItem {
  readonly label: string;
  readonly route: string;
  /** Semantic icon name resolved via the ui-kit MEE_ICONS registry. */
  readonly icon: MeeIconName;
  /** Render as a filled accent/primary CTA (e.g. "+ New Catalog"). */
  readonly accent?: boolean;
  /**
   * `routerLinkActive` match mode. `true` (default) = exact-match active
   * highlighting (so e.g. /catalogs does not bleed onto /categories/*);
   * `false` = prefix match (so /catalogs stays active on /catalogs/new and
   * /catalogs/:id/*). The shell derives this from its `prefixMatch` flag.
   */
  readonly exact?: boolean;
}

/** A labelled group of sidebar items (e.g. Home / Catalogs / Categories / Account). */
export interface MeeNavGroup {
  readonly label: string;
  readonly items: readonly MeeNavItem[];
}

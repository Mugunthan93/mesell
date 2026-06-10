/**
 * MeeSell-semantic menu item. A narrowed subset of PrimeNG's MenuItem that
 * exposes only the props MeeSell needs. Keeps PrimeNG's full API off the
 * feature/layout surface.
 */
export interface MeeMenuItem {
  /** Visible label. Omit when `separator` is true. */
  label?: string;
  /** Icon class (e.g. 'pi pi-user'). */
  icon?: string;
  /** Router link target for navigation items. */
  routerLink?: string | unknown[];
  /** Click handler for action items. */
  command?: () => void;
  /** Renders a divider instead of an actionable row. */
  separator?: boolean;
}

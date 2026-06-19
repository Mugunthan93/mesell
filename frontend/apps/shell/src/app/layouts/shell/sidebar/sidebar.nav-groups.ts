// sidebar.nav-groups.ts — pure data, no Angular imports.
// Keeping MeeIconName as a plain string alias here avoids transitively importing
// @mesell/ui-kit Angular components in vitest specs (no JIT issue).
// The component file imports MeeIconName from @mesell/ui-kit directly for type safety.

export interface NavItem {
  label: string;
  icon: string;
  route: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

/**
 * SIDEBAR_NAV_GROUPS — canonical top-level navigation for MeeSell shell sidebar.
 *
 * V1 routes represented here:
 *   /dashboard        — Home
 *   /catalogs         — My Catalogs
 *   /catalogs/new     — New Product  (Fix 1: was /catalog/new — singular typo)
 *   /categories/browse — Categories  (Fix 2: was /categories — missing /browse suffix)
 *   /profile          — Profile
 *
 * Deliberately absent (Director ruling — Option A):
 *   /pricing, /export — these are param-bound (/catalogs/:id/pricing, /catalogs/:id/export)
 *   and must NOT appear as top-level sidebar routes.
 *
 * Exported for unit testing — pure data, no Angular DI required.
 */
export const SIDEBAR_NAV_GROUPS: NavGroup[] = [
  {
    label: 'Main',
    items: [{ label: 'Home', icon: 'home', route: '/dashboard' }],
  },
  {
    label: 'Catalogs',
    items: [
      { label: 'My Catalogs', icon: 'list', route: '/catalogs' },
      { label: 'New Product', icon: 'add', route: '/catalogs/new' },
      { label: 'Categories', icon: 'tag', route: '/categories/browse' },
    ],
  },
  {
    label: 'Account',
    items: [{ label: 'Profile', icon: 'user', route: '/profile' }],
  },
];

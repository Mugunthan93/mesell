// sidebar.nav-groups.ts — pure data, no Angular imports.
// Keeping MeeIconName as a plain string alias here avoids transitively importing
// @mesell/ui-kit Angular components in vitest specs (no JIT issue).
// The component file imports MeeIconName from @mesell/ui-kit directly for type safety.

export interface NavItem {
  label: string;
  icon: string;
  route: string;
  /** When true (default), active state matches ONLY on an exact route match.
   *  Set false only for routes that should also highlight on child paths. */
  exact?: boolean;
  /** data-testid for Playwright E2E targeting. Optional — absent = no attribute. */
  testId?: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

/**
 * ONBOARDING_NAV_ITEM — shown ONLY when AuthUser.onboarding_complete === false.
 * Consumed by SidebarComponent to prepend a transient "Getting started" group.
 * Pure data — no Angular imports (vitest-safe).
 */
export const ONBOARDING_NAV_ITEM: NavItem = {
  label: 'Complete your profile',
  icon: 'user',
  route: '/onboarding',
  exact: true,
  testId: 'nav-onboarding',
};

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
    items: [{ label: 'Home', icon: 'home', route: '/dashboard', exact: true, testId: 'nav-home' }],
  },
  {
    label: 'Catalogs',
    items: [
      // exact:true — /catalogs must NOT stay active on /catalogs/new or /catalogs/:id/* (F-NAV-1).
      { label: 'My Catalogs', icon: 'list', route: '/catalogs', exact: true, testId: 'nav-catalogs' },
      { label: 'New Product', icon: 'add', route: '/catalogs/new', exact: true, testId: 'nav-new-product' },
      { label: 'Categories', icon: 'tag', route: '/categories/browse', exact: true, testId: 'nav-categories' },
    ],
  },
  {
    label: 'Account',
    items: [
      { label: 'Profile', icon: 'user', route: '/profile', exact: true, testId: 'nav-profile' },
      // Wave 5 (Razorpay) — billing vertical. Routes to the mfe-billing remote's
      // /billing/plans (tier selection + checkout). 'wallet' is a registered
      // MeeIconName; the raw PrimeIcons class it maps to lives only in
      // icon.registry.ts (per FE-2).
      { label: 'Plans', icon: 'wallet', route: '/billing/plans', exact: true, testId: 'nav-plans' },
    ],
  },
];

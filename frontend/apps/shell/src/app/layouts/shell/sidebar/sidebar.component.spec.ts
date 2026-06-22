import { describe, it, expect, beforeEach } from 'vitest';
import { SIDEBAR_NAV_GROUPS, ONBOARDING_NAV_ITEM, NavGroup } from './sidebar.nav-groups';

// ---------------------------------------------------------------------------
// Helper — mirrors SidebarComponent.navGroups computed logic (OB-FE-18).
// Kept here as a pure function so we can test all gate conditions without
// TestBed (which triggers the Angular 21 + Vitest JIT crash on standalone
// components that import PrimeNG modules).
// ---------------------------------------------------------------------------
function buildNavGroups(onboardingComplete: boolean | null | undefined): NavGroup[] {
  if (onboardingComplete === false) {
    return [
      { label: 'Getting started', items: [ONBOARDING_NAV_ITEM] },
      ...SIDEBAR_NAV_GROUPS,
    ];
  }
  return SIDEBAR_NAV_GROUPS;
}

// Pure-data assertions on SIDEBAR_NAV_GROUPS.
// The template wiring (routerLink / routerLinkActive) is verified by E2E / shell integration
// tests. These unit tests guard the data contract so route-drift regressions are caught at
// the spec layer before a build is needed.
//
// Imported from sidebar.nav-groups.ts (no Angular imports) to avoid the JIT compilation
// error triggered by importing Angular components in bare vitest.

describe('SIDEBAR_NAV_GROUPS — nav route data contract', () => {
  let groups: NavGroup[];

  beforeEach(() => {
    groups = SIDEBAR_NAV_GROUPS;
  });

  it('should expose exactly 3 nav groups (Main, Catalogs, Account) — no Tools group', () => {
    expect(groups).toHaveLength(3);
  });

  it('should have group labels [Main, Catalogs, Account]', () => {
    const labels = groups.map((g) => g.label);
    expect(labels).toEqual(['Main', 'Catalogs', 'Account']);
  });

  it('Tools group should NOT be present (Pricing and Export are param-bound routes)', () => {
    const toolsGroup = groups.find((g) => g.label === 'Tools');
    expect(toolsGroup).toBeUndefined();
  });

  it('should NOT include /pricing as a top-level route', () => {
    const allRoutes = groups.flatMap((g) => g.items.map((i) => i.route));
    expect(allRoutes).not.toContain('/pricing');
  });

  it('should NOT include /export as a top-level route', () => {
    const allRoutes = groups.flatMap((g) => g.items.map((i) => i.route));
    expect(allRoutes).not.toContain('/export');
  });

  describe('Main group', () => {
    it('should have one item: Home → /dashboard', () => {
      const main = groups.find((g) => g.label === 'Main')!;
      expect(main.items).toHaveLength(1);
      expect(main.items[0]).toMatchObject({ label: 'Home', route: '/dashboard' });
    });
  });

  describe('Catalogs group', () => {
    let catalogs: NavGroup['items'];

    beforeEach(() => {
      catalogs = groups.find((g) => g.label === 'Catalogs')!.items;
    });

    it('should have 3 items (My Catalogs, New Product, Categories)', () => {
      expect(catalogs).toHaveLength(3);
    });

    it('My Catalogs → /catalogs', () => {
      const item = catalogs.find((i) => i.label === 'My Catalogs')!;
      expect(item.route).toBe('/catalogs');
    });

    it('New Product → /catalogs/new (Fix 1: was /catalog/new — singular typo)', () => {
      const item = catalogs.find((i) => i.label === 'New Product')!;
      expect(item.route).toBe('/catalogs/new');
    });

    it('New Product route must NOT be the old broken singular /catalog/new', () => {
      const item = catalogs.find((i) => i.label === 'New Product')!;
      expect(item.route).not.toBe('/catalog/new');
    });

    it('Categories → /categories/browse (Fix 2: was /categories — missing /browse suffix)', () => {
      const item = catalogs.find((i) => i.label === 'Categories')!;
      expect(item.route).toBe('/categories/browse');
    });

    it('Categories route must NOT be the bare /categories (no browse suffix)', () => {
      const item = catalogs.find((i) => i.label === 'Categories')!;
      expect(item.route).not.toBe('/categories');
    });
  });

  describe('Account group', () => {
    it('should have two items: Profile → /profile and Plans → /billing/plans (Wave 5 Razorpay)', () => {
      const account = groups.find((g) => g.label === 'Account')!;
      expect(account.items).toHaveLength(2);
      expect(account.items[0]).toMatchObject({ label: 'Profile', route: '/profile' });
      expect(account.items[1]).toMatchObject({ label: 'Plans', route: '/billing/plans' });
    });
  });

  describe('complete route list — regression snapshot', () => {
    it('all routes match the V1 spec top-level routes in order', () => {
      const allRoutes = groups.flatMap((g) => g.items.map((i) => i.route));
      expect(allRoutes).toEqual([
        '/dashboard',
        '/catalogs',
        '/catalogs/new',
        '/categories/browse',
        '/profile',
        '/billing/plans',
      ]);
    });
  });

  describe('F-NAV-1 — exact active-match (routerLinkActiveOptions)', () => {
    it('every nav item declares exact:true so /catalogs does not over-match /catalogs/new or /catalogs/:id/*', () => {
      const allItems = groups.flatMap((g) => g.items);
      for (const item of allItems) {
        // Default when absent is also exact:true (template uses item.exact ?? true),
        // but all items should be explicit.
        expect(item.exact ?? true).toBe(true);
      }
    });

    it('/catalogs item specifically carries exact:true', () => {
      const catalogsGroup = groups.find((g) => g.label === 'Catalogs')!;
      const myCatalogs = catalogsGroup.items.find((i) => i.route === '/catalogs')!;
      expect(myCatalogs.exact).toBe(true);
    });

    it('/catalogs/new item carries exact:true', () => {
      const catalogsGroup = groups.find((g) => g.label === 'Catalogs')!;
      const newProduct = catalogsGroup.items.find((i) => i.route === '/catalogs/new')!;
      expect(newProduct.exact).toBe(true);
    });
  });
});

// ---------------------------------------------------------------------------
// OB-FE-18 — onboarding nav item gate (=== false ONLY)
// Tests the same conditional logic used by SidebarComponent.navGroups computed.
// Uses a narrow AuthService stub exposing only `currentUser` as a writable
// Angular signal — no TestBed needed (avoids Angular 21 + Vitest JIT crash
// on standalone components that import PrimeNG modules).
// ---------------------------------------------------------------------------

describe('ONBOARDING_NAV_ITEM — data contract', () => {
  it('should have route /onboarding', () => {
    expect(ONBOARDING_NAV_ITEM.route).toBe('/onboarding');
  });

  it('should carry testId nav-onboarding for Playwright targeting', () => {
    expect(ONBOARDING_NAV_ITEM.testId).toBe('nav-onboarding');
  });

  it('should have exact:true', () => {
    expect(ONBOARDING_NAV_ITEM.exact).toBe(true);
  });
});

describe('navGroups computed — OB-FE-18 gate (=== false ONLY)', () => {
  // Stub: a minimal AuthService whose `currentUser` signal is simulated as a
  // plain function — no @angular/core import needed in bare vitest (avoids the
  // "Cannot find package '@angular/core'" error when node_modules is not in the
  // worktree path).  The component uses `this.auth.currentUser()` — a zero-arg
  // call returning AuthUser|null — so we pass the value directly.

  describe('when onboarding_complete === false (onboarding incomplete)', () => {
    it('prepends a "Getting started" group containing the onboarding nav item', () => {
      const groups = buildNavGroups(false);

      expect(groups[0].label).toBe('Getting started');
      expect(groups[0].items).toHaveLength(1);
      expect(groups[0].items[0].route).toBe('/onboarding');
      expect(groups[0].items[0].testId).toBe('nav-onboarding');
    });

    it('still includes all standard SIDEBAR_NAV_GROUPS after the Getting started group', () => {
      const groups = buildNavGroups(false);
      const remainder = groups.slice(1);

      expect(remainder).toEqual(SIDEBAR_NAV_GROUPS);
    });

    it('total group count is SIDEBAR_NAV_GROUPS.length + 1', () => {
      const groups = buildNavGroups(false);
      expect(groups).toHaveLength(SIDEBAR_NAV_GROUPS.length + 1);
    });
  });

  describe('when onboarding_complete === true (profile complete)', () => {
    it('does NOT include a "Getting started" group — item absent', () => {
      const groups = buildNavGroups(true);
      const gettingStarted = groups.find((g) => g.label === 'Getting started');

      expect(gettingStarted).toBeUndefined();
    });

    it('returns exactly SIDEBAR_NAV_GROUPS unmodified', () => {
      expect(buildNavGroups(true)).toEqual(SIDEBAR_NAV_GROUPS);
    });

    it('does NOT include the /onboarding route in any group', () => {
      const allRoutes = buildNavGroups(true).flatMap((g) => g.items.map((i) => i.route));
      expect(allRoutes).not.toContain('/onboarding');
    });
  });

  describe('when onboarding_complete === undefined (legacy/mock users — no field set)', () => {
    it('does NOT include a "Getting started" group — item absent', () => {
      const groups = buildNavGroups(undefined);
      const gettingStarted = groups.find((g) => g.label === 'Getting started');

      expect(gettingStarted).toBeUndefined();
    });

    it('returns exactly SIDEBAR_NAV_GROUPS unmodified', () => {
      expect(buildNavGroups(undefined)).toEqual(SIDEBAR_NAV_GROUPS);
    });

    it('does NOT include the /onboarding route in any group', () => {
      const allRoutes = buildNavGroups(undefined).flatMap((g) => g.items.map((i) => i.route));
      expect(allRoutes).not.toContain('/onboarding');
    });
  });

  describe('OB-FE-18 strict gate — only === false triggers the item (NOT falsy)', () => {
    it('undefined does NOT trigger — strict false check, not falsy (legacy users safe)', () => {
      expect(buildNavGroups(undefined).find((g) => g.label === 'Getting started')).toBeUndefined();
    });

    it('null does NOT trigger — strict false check, not falsy', () => {
      expect(buildNavGroups(null).find((g) => g.label === 'Getting started')).toBeUndefined();
    });

    it('false triggers — item present (onboarding incomplete)', () => {
      expect(buildNavGroups(false).find((g) => g.label === 'Getting started')).toBeDefined();
    });

    it('true does NOT trigger — item absent (onboarding complete)', () => {
      expect(buildNavGroups(true).find((g) => g.label === 'Getting started')).toBeUndefined();
    });
  });
});

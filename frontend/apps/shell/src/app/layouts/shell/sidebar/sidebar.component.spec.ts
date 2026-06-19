import { describe, it, expect, beforeEach } from 'vitest';
import { SIDEBAR_NAV_GROUPS, NavGroup } from './sidebar.nav-groups';

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
    it('should have one item: Profile → /profile', () => {
      const account = groups.find((g) => g.label === 'Account')!;
      expect(account.items).toHaveLength(1);
      expect(account.items[0]).toMatchObject({ label: 'Profile', route: '/profile' });
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
      ]);
    });
  });
});

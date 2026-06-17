import { describe, it, expect, vi, beforeEach } from 'vitest';
import { loadRemoteModule } from '@angular-architects/native-federation';

// Mock the native-federation runtime so the helper can be exercised headlessly
// (no live remoteEntry.json fetch). Proves the success-resolution shape (§9.A-4)
// and the D12 fallback path (§9.A-5) without a browser.
//
// WAVE 6A FIX (test-isolation): reference the mock via `vi.mocked(loadRemoteModule)`
// instead of a module-level closure (`const loadRemoteModuleMock = vi.fn()` captured by
// the vi.mock factory). When this spec and `csp-smoke.spec.ts` (which mocks the SAME
// module with its OWN closure) land in the same Vitest worker, the two factory closures
// alias one shared module export — the closure-captured `vi.fn` invoked at runtime was
// the OTHER file's instance, so `mockResolvedValue` here had no effect and the helper
// saw `undefined` → fell back to RemoteFailureComponent (4 order-dependent failures).
// Binding through `vi.mocked(loadRemoteModule)` resolves to the actual mocked export
// regardless of co-located factories. Pre-existing latent defect surfaced by Wave A's
// added spec files shifting worker sharding; not a Wave A code regression.
vi.mock('@angular-architects/native-federation', () => ({
  loadRemoteModule: vi.fn(),
}));

const loadRemoteModuleMock = vi.mocked(loadRemoteModule);

import { loadRemoteWithFallback, loadRemoteRoutesWithFallback } from './load-remote';
import { RemoteFailureComponent } from './remote-failure.component';

class FakePricingComponent {}

const FAKE_CATALOG_ROUTES = [
  { path: '', component: class FakeCatalogListComponent {} },
  { path: 'new', component: class FakeCatalogNewComponent {} },
];

describe('loadRemoteWithFallback (MF Sub-Plan 01 — D12 / §6.4)', () => {
  beforeEach(() => {
    loadRemoteModuleMock.mockReset();
  });

  it('calls loadRemoteModule with the correct remoteName + exposedModule', async () => {
    loadRemoteModuleMock.mockResolvedValue({ PricingComponent: FakePricingComponent });
    await loadRemoteWithFallback('mfe-pricing', './PricingComponent')();
    expect(loadRemoteModuleMock).toHaveBeenCalledWith({
      remoteName: 'mfe-pricing',
      exposedModule: './PricingComponent',
    });
  });

  it('resolves the remote-exposed component on success (§9.A-4 plumbing)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ PricingComponent: FakePricingComponent });
    const resolved = await loadRemoteWithFallback('mfe-pricing', './PricingComponent')();
    expect(resolved).toBe(FakePricingComponent);
  });

  it('falls back to RemoteFailureComponent when the remote fails to load (§9.A-5 / D12)', async () => {
    loadRemoteModuleMock.mockRejectedValue(new Error('remoteEntry.json 404'));
    const resolved = await loadRemoteWithFallback('mfe-pricing', './PricingComponent')();
    expect(resolved).toBe(RemoteFailureComponent);
  });
});

describe('loadRemoteRoutesWithFallback (SP05 — D31 Routes-array expose / §6.D)', () => {
  beforeEach(() => {
    loadRemoteModuleMock.mockReset();
  });

  it('calls loadRemoteModule with the correct remoteName + exposedModule', async () => {
    loadRemoteModuleMock.mockResolvedValue({ CATALOG_ROUTES: FAKE_CATALOG_ROUTES });
    await loadRemoteRoutesWithFallback('mfe-catalog', './CatalogRoutes')();
    expect(loadRemoteModuleMock).toHaveBeenCalledWith({
      remoteName: 'mfe-catalog',
      exposedModule: './CatalogRoutes',
    });
  });

  it('resolves CATALOG_ROUTES array on success (§6.D R-SP5-1)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ CATALOG_ROUTES: FAKE_CATALOG_ROUTES });
    const resolved = await loadRemoteRoutesWithFallback('mfe-catalog', './CatalogRoutes')();
    expect(resolved).toBe(FAKE_CATALOG_ROUTES);
  });

  it('falls back to [{path:"**",component:RemoteFailureComponent}] on remote load failure (D12)', async () => {
    loadRemoteModuleMock.mockRejectedValue(new Error('remoteEntry.json 404'));
    const resolved = await loadRemoteRoutesWithFallback('mfe-catalog', './CatalogRoutes')();
    expect(Array.isArray(resolved)).toBeTruthy();
    expect((resolved as unknown[])[0]).toMatchObject({ path: '**', component: RemoteFailureComponent });
  });
});

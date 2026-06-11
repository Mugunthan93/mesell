import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the native-federation runtime so the helper can be exercised headlessly
// (no live remoteEntry.json fetch). Proves the success-resolution shape (§9.A-4)
// and the D12 fallback path (§9.A-5) without a browser.
const loadRemoteModuleMock = vi.fn();
vi.mock('@angular-architects/native-federation', () => ({
  loadRemoteModule: (...args: unknown[]) => loadRemoteModuleMock(...args),
}));

import { loadRemoteWithFallback } from './load-remote';
import { RemoteFailureComponent } from './remote-failure.component';

class FakePricingComponent {}

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

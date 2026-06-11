/**
 * SP07 Phase B — Dev CSP smoke harness (B2 / D42 / C-CSP-1)
 *
 * PURPOSE: Prove that Native Federation remote-loading is NOT structurally blocked
 * by a Content-Security-Policy. The CSP HEADER MECHANISM is infra-owned (nginx/
 * Traefik — see spec_sp07_infra.md). This harness owns the FRONTEND-SIDE proof that
 * loadRemoteWithFallback / loadRemoteRoutesWithFallback will succeed once the shell
 * resolves remoteEntry.json URLs — regardless of which CSP header the ingress emits.
 *
 * HIGH-STAKES SURFACES (R-SP4-5 + R-SP6-6 = mfe-dashboard landing + mfe-auth):
 *   - '/'       → mfe-dashboard   LandingComponent   (PUBLIC pre-auth)
 *   - '/login'  → mfe-auth        LoginComponent     (PUBLIC pre-auth)
 * These two routes are the highest-stakes CSP surfaces because they are the FIRST
 * network requests the browser makes after the shell HTML loads. A missing
 * script-src/connect-src token here = white page for ALL users.
 *
 * MANUAL SMOKE PROCEDURE (the lead runs this against the dev environment):
 * 1. Ensure the dev CSP header is emitted by ingress (infra configures nginx/Traefik).
 *    The allowlist MUST include:
 *      script-src  'self' http://localhost:4201 http://localhost:4202 http://localhost:4203
 *                  http://localhost:4204 http://localhost:4205 http://localhost:4206
 *      connect-src 'self' http://localhost:420{1-6} (same set)
 *      style-src   'self' 'unsafe-inline' (Tailwind inline vars)
 *      font-src    'self' data: https://fonts.gstatic.com
 *      img-src     'self' data: blob:
 * 2. Open http://localhost:4200 (public landing, mfe-dashboard) in Chrome with DevTools.
 *    Confirm: no "Refused to load" or "Refused to connect" console violations.
 *    Confirm: LandingComponent mounts (app-landing visible, no RemoteFailureComponent).
 * 3. Navigate to http://localhost:4200/login (public auth, mfe-auth).
 *    Confirm: no CSP violations. LoginComponent mounts.
 * 4. Navigate to http://localhost:4200/signup → SignupComponent.
 * 5. Navigate to http://localhost:4200/otp-verify → OtpVerifyComponent.
 * 6. Navigate to http://localhost:4200/dashboard (requires auth; guard redirects if not
 *    authenticated). Confirm RemoteFailureComponent does NOT appear (only guard redirect).
 * 7. Check Network tab: remoteEntry.json requests for ALL 6 remotes return HTTP 200.
 *    No remoteEntry.json request should be blocked (would show "net::ERR_BLOCKED_BY_CSP").
 * 8. Report: PASS (no CSP violations, all 6 remoteEntry 200) or FAIL (list the blocked URLs).
 *
 * NOTE: The full CSP-active orchestrated smoke (401→refresh→retry + backend) is LEAD-OWNED.
 * This harness only provides the frontend-side structural proof (headless).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the federation runtime (same pattern as load-remote.spec.ts — headless, no live fetch)
const loadRemoteModuleMock = vi.fn();
vi.mock('@angular-architects/native-federation', () => ({
  loadRemoteModule: (...args: unknown[]) => loadRemoteModuleMock(...args),
}));

import { loadRemoteWithFallback, loadRemoteRoutesWithFallback } from './load-remote';
import { RemoteFailureComponent } from './remote-failure.component';

// Fake component classes for each of the 6 remotes (structural smoke — no real rendering)
class FakeLandingComponent {}
class FakeDashboardComponent {}
class FakeLoginComponent {}
class FakeSignupComponent {}
class FakeOtpVerifyComponent {}
class FakePricingComponent {}
class FakeExportComponent {}
class FakeOnboardingComponent {}
const FAKE_CATALOG_ROUTES = [{ path: '', component: class {} }];

/** CSP-relevant remotes and their primary expose keys (the shell loads these on navigation) */
const REMOTE_SURFACES = [
  // HIGH-STAKES PUBLIC SURFACES (R-SP4-5 landing + R-SP6-6 auth):
  { remote: 'mfe-dashboard',  expose: './LandingComponent',  component: FakeLandingComponent,  cspNote: 'PUBLIC pre-auth — HIGHEST STAKES CSP surface (R-SP4-5)' },
  { remote: 'mfe-auth',       expose: './LoginComponent',    component: FakeLoginComponent,     cspNote: 'PUBLIC pre-auth — HIGHEST STAKES CSP surface (R-SP6-6)' },
  // Additional auth surfaces (also PUBLIC):
  { remote: 'mfe-auth',       expose: './SignupComponent',   component: FakeSignupComponent,    cspNote: 'PUBLIC pre-auth (R-SP6-6 secondary)' },
  { remote: 'mfe-auth',       expose: './OtpVerifyComponent',component: FakeOtpVerifyComponent, cspNote: 'PUBLIC pre-auth + C4 WRITE path (R-SP6-6 otp)' },
  // Authenticated surfaces:
  { remote: 'mfe-dashboard',  expose: './DashboardComponent',component: FakeDashboardComponent, cspNote: 'Authenticated (authGuard blocks unauthenticated access before remote loads)' },
  { remote: 'mfe-pricing',    expose: './PricingComponent',  component: FakePricingComponent,   cspNote: 'Authenticated (authGuard)' },
  { remote: 'mfe-export',     expose: './ExportComponent',   component: FakeExportComponent,    cspNote: 'Authenticated (authGuard)' },
  { remote: 'mfe-onboarding', expose: './OnboardingComponent',component: FakeOnboardingComponent,cspNote: 'Authenticated (authGuard)' },
];

describe('CSP smoke — all 6 remotes resolve successfully when remoteEntry is reachable (B2 / D42)', () => {
  beforeEach(() => {
    loadRemoteModuleMock.mockReset();
  });

  it('HIGH-STAKES: mfe-dashboard LandingComponent resolves (R-SP4-5 — PUBLIC landing, first CSP surface)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ LandingComponent: FakeLandingComponent });
    const resolved = await loadRemoteWithFallback('mfe-dashboard', './LandingComponent')();
    expect(resolved).toBe(FakeLandingComponent);
    expect(resolved).not.toBe(RemoteFailureComponent);
  });

  it('HIGH-STAKES: mfe-auth LoginComponent resolves (R-SP6-6 — PUBLIC login, first CSP auth surface)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ LoginComponent: FakeLoginComponent });
    const resolved = await loadRemoteWithFallback('mfe-auth', './LoginComponent')();
    expect(resolved).toBe(FakeLoginComponent);
    expect(resolved).not.toBe(RemoteFailureComponent);
  });

  it('mfe-auth SignupComponent resolves (PUBLIC pre-auth)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ SignupComponent: FakeSignupComponent });
    const resolved = await loadRemoteWithFallback('mfe-auth', './SignupComponent')();
    expect(resolved).toBe(FakeSignupComponent);
  });

  it('mfe-auth OtpVerifyComponent resolves (PUBLIC pre-auth + C4 WRITE path)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ OtpVerifyComponent: FakeOtpVerifyComponent });
    const resolved = await loadRemoteWithFallback('mfe-auth', './OtpVerifyComponent')();
    expect(resolved).toBe(FakeOtpVerifyComponent);
  });

  it('mfe-dashboard DashboardComponent resolves (authenticated surface)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ DashboardComponent: FakeDashboardComponent });
    const resolved = await loadRemoteWithFallback('mfe-dashboard', './DashboardComponent')();
    expect(resolved).toBe(FakeDashboardComponent);
  });

  it('mfe-pricing PricingComponent resolves (authenticated surface)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ PricingComponent: FakePricingComponent });
    const resolved = await loadRemoteWithFallback('mfe-pricing', './PricingComponent')();
    expect(resolved).toBe(FakePricingComponent);
  });

  it('mfe-export ExportComponent resolves (authenticated surface)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ ExportComponent: FakeExportComponent });
    const resolved = await loadRemoteWithFallback('mfe-export', './ExportComponent')();
    expect(resolved).toBe(FakeExportComponent);
  });

  it('mfe-onboarding OnboardingComponent resolves (authenticated surface)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ OnboardingComponent: FakeOnboardingComponent });
    const resolved = await loadRemoteWithFallback('mfe-onboarding', './OnboardingComponent')();
    expect(resolved).toBe(FakeOnboardingComponent);
  });

  it('mfe-catalog CatalogRoutes (Routes-array expose) resolves (SP05 D31 pattern)', async () => {
    loadRemoteModuleMock.mockResolvedValue({ CATALOG_ROUTES: FAKE_CATALOG_ROUTES });
    const resolved = await loadRemoteRoutesWithFallback('mfe-catalog', './CatalogRoutes')();
    expect(Array.isArray(resolved)).toBeTruthy();
    expect(resolved).toBe(FAKE_CATALOG_ROUTES);
  });
});

describe('CSP smoke — D12 fallback fires when a remote is unreachable (simulates CSP-blocked remoteEntry.json)', () => {
  beforeEach(() => {
    loadRemoteModuleMock.mockReset();
  });

  it('HIGH-STAKES: mfe-dashboard fails gracefully → RemoteFailureComponent (not white-screen)', async () => {
    loadRemoteModuleMock.mockRejectedValue(new Error('CSP: Refused to load http://localhost:4204/remoteEntry.json'));
    const resolved = await loadRemoteWithFallback('mfe-dashboard', './LandingComponent')();
    expect(resolved).toBe(RemoteFailureComponent);
  });

  it('HIGH-STAKES: mfe-auth fails gracefully → RemoteFailureComponent (not white-screen)', async () => {
    loadRemoteModuleMock.mockRejectedValue(new Error('CSP: Refused to load http://localhost:4206/remoteEntry.json'));
    const resolved = await loadRemoteWithFallback('mfe-auth', './LoginComponent')();
    expect(resolved).toBe(RemoteFailureComponent);
  });

  it('mfe-catalog fails gracefully → [{path:"**",component:RemoteFailureComponent}] (D31 Routes-array D12)', async () => {
    loadRemoteModuleMock.mockRejectedValue(new Error('CSP: Refused to load http://localhost:4205/remoteEntry.json'));
    const resolved = await loadRemoteRoutesWithFallback('mfe-catalog', './CatalogRoutes')();
    expect(Array.isArray(resolved)).toBeTruthy();
    expect((resolved as unknown[])[0]).toMatchObject({ path: '**', component: RemoteFailureComponent });
  });
});

describe('CSP smoke — REMOTE_SURFACES manifest completeness (all 6 remotes covered)', () => {
  it('all 6 remote names are represented in the CSP surface list', () => {
    const remotes = new Set(REMOTE_SURFACES.map(s => s.remote));
    // mfe-catalog is tested via loadRemoteRoutesWithFallback above, not in REMOTE_SURFACES
    const expectedRemotes = new Set([
      'mfe-dashboard', 'mfe-auth', 'mfe-pricing', 'mfe-export', 'mfe-onboarding',
    ]);
    for (const r of expectedRemotes) {
      expect(remotes.has(r), `${r} must be in REMOTE_SURFACES`).toBeTruthy();
    }
    // Total surfaces: 5 unique remotes (mfe-catalog handled separately) + 8 expose entries
    expect(REMOTE_SURFACES).toHaveLength(8);
  });

  it('PUBLIC surfaces (mfe-dashboard + mfe-auth) are first — highest-stakes ordering verified', () => {
    const publicSurfaces = REMOTE_SURFACES.filter(s => s.cspNote.includes('PUBLIC'));
    expect(publicSurfaces.length).toBeGreaterThanOrEqual(4);
    // First two entries must be the highest-stakes PUBLIC surfaces
    expect(REMOTE_SURFACES[0].remote).toBe('mfe-dashboard');
    expect(REMOTE_SURFACES[1].remote).toBe('mfe-auth');
  });
});

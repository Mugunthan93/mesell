/**
 * SP06 D38 C4 — WRITE-path singleton smoke test (the migration's auth WRITE go/no-go).
 *
 * This is the INVERSE of SP03 D22 C5 (`apps/mfe-onboarding/src/app/auth-singleton.smoke.spec.ts`).
 * That spec proved the READ/LOGOUT path across the federation boundary: shell sets session →
 * remote ProfileComponent reads it → remote logout clears the shell's singleton.
 *
 * THIS spec proves the WRITE path: the mfe-auth REMOTE's OtpVerifyComponent calls
 * `setSession('mock-token', {...})` → the SHELL's AuthService singleton reflects the mutation
 * (isAuthenticated=true, currentUser.name='Seller', getToken='mock-token') → the authGuard
 * now passes for /dashboard.
 *
 * The test models the federation boundary with a single root injector (exactly what the
 * shared import-map + `singleton: true` in federation.config.js produce). AuthService is
 * `@Injectable({ providedIn: 'root' })` (D22 C2 — ZERO changes to auth.service.ts allowed).
 * Under Native Federation the shell's import-map URL for `@mesell/core` resolves for both
 * the shell and the remote, so they share ONE provider in ONE root injector.
 *
 * Steps (D38 C4):
 *   1. Unauthenticated start: shellAuth.isAuthenticated()===false, authGuard BLOCKS /dashboard.
 *   2. Confirm OtpVerifyComponent's injected auth IS the shell's instance (single-instance proof).
 *   3. Trigger WRITE: set otpValue to 6 chars, call onSubmit(); advance fake timers by 1500ms
 *      to flush the setTimeout that wraps setSession (vi.useFakeTimers — no Zone.js, per
 *      established pattern in profile.component.spec.ts).
 *   4. ASSERT post-WRITE: isAuthenticated===true, currentUser.name==='Seller',
 *      currentUser.id===1, getToken==='mock-token'.
 *   5. ASSERT authGuard now PASSES: returns true (not a UrlTree) — /dashboard is reachable.
 *   6. Verify resend-timer cleanup: ngOnDestroy clears the setInterval (no orphaned timer after
 *      fixture.destroy()).
 *
 * HARD RULE: this test MUST NOT touch auth.service.ts. If setSession mutates a duplicate
 * AuthService instance instead of the shell's, assertions 4+5 will fail with visible evidence
 * (the P0 drift, MASTER_PLAN R1). Do NOT weaken assertions to make it pass — HARD STOP instead.
 */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  provideRouter,
  Router,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { runInInjectionContext, EnvironmentInjector } from '@angular/core';

import { AuthService, authGuard } from '@mesell/core';
import { OtpVerifyComponent } from './otp-verify.component';

describe('SP06 D38 C4 — OtpVerifyComponent WRITE-path: setSession crosses the federation boundary into the shell singleton', () => {
  let fixture: ComponentFixture<OtpVerifyComponent>;
  let comp: OtpVerifyComponent;
  let shellAuth: AuthService;
  let envInjector: EnvironmentInjector;
  let router: Router;

  beforeEach(async () => {
    // Use real timers as baseline; individual tests that need fake timers
    // call vi.useFakeTimers() and restore with vi.useRealTimers().
    vi.useRealTimers();

    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [OtpVerifyComponent],
      providers: [
        // Stub /login + /dashboard routes (SP03 NG04002 gotcha: a router.navigate(['/dashboard'])
        // with no matching route throws NavigationError and silently poisons the suite even if
        // the test "passes"). Both stubs are required here because the guard redirects to /login
        // (pre-write) and onSubmit navigates to /dashboard (post-write).
        provideRouter([
          { path: 'login', children: [] },
          { path: 'dashboard', children: [] },
        ]),
        provideAnimationsAsync('noop'),
      ],
    }).compileComponents();

    // "Shell" handle on the shared singleton (providedIn:'root' → one instance in the injector).
    shellAuth   = TestBed.inject(AuthService);
    envInjector = TestBed.inject(EnvironmentInjector);
    router      = TestBed.inject(Router);

    // Ensure we start unauthenticated (clean slate, independent of test order).
    shellAuth.logout();

    // Create the "remote" OtpVerifyComponent — its ngOnInit starts the resend-countdown
    // setInterval. We use fake timers in the setSession test to flush the onSubmit setTimeout
    // (1500 ms), then restore real timers so the interval does not interfere with other tests.
    fixture = TestBed.createComponent(OtpVerifyComponent);
    comp    = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    // Destroy component to fire ngOnDestroy → clearInterval (no orphaned interval after test).
    fixture.destroy();
    vi.useRealTimers();
    TestBed.resetTestingModule();
  });

  // ── Step 1+2: Unauthenticated start + guard BLOCKS /dashboard ─────────────────

  it('C4-pre: shell starts unauthenticated and authGuard blocks /dashboard (pre-write)', () => {
    // Step 1 — unauthenticated.
    expect(shellAuth.isAuthenticated()).toBe(false);
    expect(shellAuth.currentUser()).toBeNull();

    // Guard returns a redirect UrlTree to /login, NOT true.
    const guardResult = runInInjectionContext(envInjector, () =>
      authGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/dashboard' } as RouterStateSnapshot,
      ),
    );
    expect(guardResult).toBeInstanceOf(UrlTree);
    expect(router.serializeUrl(guardResult as UrlTree)).toContain('/login');
  });

  it('C4-instance: the remote OtpVerifyComponent injects the SAME AuthService as the shell (single-instance)', () => {
    // Step 2 — the remote's auth field IS the shell singleton (no duplicate copy).
    const remoteAuth = (comp as unknown as { auth: AuthService }).auth;
    expect(remoteAuth).toBe(shellAuth);
  });

  // ── Steps 3-6: Trigger WRITE and assert post-write shell state ────────────────

  it('C4 (THE CRUX) — remote onSubmit setSession WRITES through the boundary: shell reflects isAuthenticated, currentUser, getToken; authGuard now passes', () => {
    vi.useFakeTimers();

    // Step 1 (guard blocked, re-asserted in same test for full trace):
    expect(shellAuth.isAuthenticated()).toBe(false);

    const preWriteGuard = runInInjectionContext(envInjector, () =>
      authGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/dashboard' } as RouterStateSnapshot,
      ),
    );
    expect(preWriteGuard).toBeInstanceOf(UrlTree);

    // Step 2 (instance identity):
    const remoteAuth = (comp as unknown as { auth: AuthService }).auth;
    expect(remoteAuth).toBe(shellAuth);

    // Step 3 — trigger WRITE: set a 6-char OTP value and call onSubmit.
    // onSubmit → loading.set(true) → setTimeout(1500) → setSession('mock-token', {...}) → navigate(['/dashboard']).
    comp.onOtpCompleted('123456');
    expect(comp.otpValue()).toBe('123456');

    comp.onSubmit();
    // Before the setTimeout fires: shell is still unauthenticated.
    expect(shellAuth.isAuthenticated()).toBe(false);

    // Advance fake timers by 1500 ms to flush the setTimeout.
    vi.advanceTimersByTime(1500);

    // Step 4 (THE CRUX) — shell's singleton now reflects the remote's setSession WRITE.
    expect(shellAuth.isAuthenticated()).toBe(true);
    expect(shellAuth.currentUser()?.name).toBe('Seller');
    expect(shellAuth.currentUser()?.id).toBe(1);
    expect(shellAuth.getToken()).toBe('mock-token');

    // Step 5 — authGuard now PASSES (returns true, not a UrlTree).
    const postWriteGuard = runInInjectionContext(envInjector, () =>
      authGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/dashboard' } as RouterStateSnapshot,
      ),
    );
    expect(postWriteGuard).toBe(true);

    vi.useRealTimers();
  });

  it('C4-abort: onSubmit is a no-op when otpValue is fewer than 6 chars (guard to prevent premature setSession)', () => {
    vi.useFakeTimers();

    comp.onOtpCompleted('12345'); // 5 chars — below threshold
    comp.onSubmit();
    vi.advanceTimersByTime(2000);

    // No setSession fired — shell remains unauthenticated.
    expect(shellAuth.isAuthenticated()).toBe(false);
    expect(shellAuth.getToken()).toBeNull();

    vi.useRealTimers();
  });

  it('C4-timer: ngOnDestroy clears the resend-countdown setInterval (no orphaned timer after fixture.destroy())', async () => {
    // The component in beforeEach was created with real timers (its setInterval is real).
    // For this timer isolation test we create a FRESH component under fake timers so the
    // setInterval is registered in the fake-timer clock and can be advanced deterministically.
    vi.useFakeTimers();

    let timerFixture: ComponentFixture<OtpVerifyComponent>;
    let timerComp: OtpVerifyComponent;

    // Create a fresh component — ngOnInit runs with fake timers active, so the
    // resend-countdown setInterval is registered in the fake clock.
    timerFixture = TestBed.createComponent(OtpVerifyComponent);
    timerComp    = timerFixture.componentInstance;
    timerFixture.detectChanges();

    // Countdown starts at 30.
    expect(timerComp.countdown()).toBe(30);

    // Advance 5 seconds — the setInterval (1 s period) fires 5 times → countdown=25.
    vi.advanceTimersByTime(5000);
    expect(timerComp.countdown()).toBe(25);

    // Destroy the component — ngOnDestroy calls clearInterval.
    timerFixture.destroy();

    // Capture the value at destruction time.
    const valueAtDestroy = timerComp.countdown();

    // Advance further — countdown must NOT change (interval is cleared).
    vi.advanceTimersByTime(10000);
    expect(timerComp.countdown()).toBe(valueAtDestroy);

    vi.useRealTimers();
  });
});

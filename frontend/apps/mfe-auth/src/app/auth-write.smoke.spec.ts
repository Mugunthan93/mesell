/**
 * SP06 D38 C4 — WRITE-path singleton smoke test (the migration's auth WRITE go/no-go).
 *
 * This is the INVERSE of SP03 D22 C5 (`apps/mfe-onboarding/src/app/auth-singleton.smoke.spec.ts`).
 * That spec proved the READ/LOGOUT path across the federation boundary: shell sets session →
 * remote ProfileComponent reads it → remote logout clears the shell's singleton.
 *
 * THIS spec proves the WRITE path: the mfe-auth REMOTE's OtpVerifyComponent calls
 * `auth.setSession(token, user)` → the SHELL's AuthService singleton reflects the mutation
 * (isAuthenticated=true, getToken=real-access-token) → the authGuard now passes for /dashboard.
 *
 * WAVE 6 UPDATE: OtpVerifyComponent now wires real HTTP (verifyOtp + me() from AuthApiService).
 * The onSubmit() path is:
 *   verifyOtp(phone, otp) → me() → auth.setSession(access_token, user) → scheduleRefresh → navigate.
 * Tests use HttpTestingController to flush the HTTP calls synchronously (no fake timers needed).
 *
 * The singleton crux (steps 2+4+5) is UNCHANGED: the write still crosses the boundary via
 * `providedIn:'root'` + federation shared import-map → ONE root injector. The mechanism being
 * tested is IDENTICAL; only the trigger path (real HTTP vs setTimeout mock) has changed.
 *
 * HARD RULE: this test MUST NOT touch auth.service.ts. If setSession mutates a duplicate
 * AuthService instance instead of the shell's, assertions 4+5 will fail with visible evidence
 * (the P0 drift, MASTER_PLAN R1). Do NOT weaken assertions to make it pass — HARD STOP instead.
 *
 * Steps (D38 C4 — Wave 6 real-HTTP variant):
 *   1. Unauthenticated start: shellAuth.isAuthenticated()===false, authGuard BLOCKS /dashboard.
 *   2. Confirm OtpVerifyComponent's injected auth IS the shell's instance (single-instance proof).
 *   3. Trigger WRITE: set otpValue to 6 chars, call onSubmit().
 *      - Flush POST /api/v1/auth/otp/verify → respond with {access_token, expires_in}
 *      - Flush GET /api/v1/auth/me → respond with MeResponse
 *   4. ASSERT post-WRITE: isAuthenticated===true, getToken===the flushed access_token.
 *   5. ASSERT authGuard now PASSES: returns true (not a UrlTree) — /dashboard is reachable.
 *   6. Verify resend-timer cleanup: ngOnDestroy clears the setInterval (no orphaned timer).
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
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { runInInjectionContext, EnvironmentInjector } from '@angular/core';

import { AuthService, authGuard } from '@mesell/core';
import { OtpVerifyComponent } from './otp-verify.component';

/** Fake verify response matching VerifyOtpResponse shape */
const FAKE_VERIFY_RESP = {
  access_token: 'real-access-token-from-backend',
  expires_in: 3600,
  token_type: 'bearer' as const,
};

/** Fake /me response matching MeResponse shape */
const FAKE_ME_RESP = {
  user_id: 'user-uuid-123',
  phone: '+919876543210',
  plan: 'free' as const,
  created_at: '2026-06-11T00:00:00Z',
  last_login_at: null,
};

describe('SP06 D38 C4 — OtpVerifyComponent WRITE-path: setSession crosses the federation boundary into the shell singleton', () => {
  let fixture: ComponentFixture<OtpVerifyComponent>;
  let comp: OtpVerifyComponent;
  let shellAuth: AuthService;
  let envInjector: EnvironmentInjector;
  let router: Router;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
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
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    // "Shell" handle on the shared singleton (providedIn:'root' → one instance in the injector).
    shellAuth   = TestBed.inject(AuthService);
    envInjector = TestBed.inject(EnvironmentInjector);
    router      = TestBed.inject(Router);
    httpMock    = TestBed.inject(HttpTestingController);

    // Ensure we start unauthenticated (clean slate, independent of test order).
    shellAuth.logout();

    // Navigate with state so OtpVerifyComponent picks up the phone (avoids redirect-to-login).
    await router.navigate(['/login']);
    await router.navigate(['/dashboard'], { state: { phone: '+919876543210' } });

    // Create the "remote" OtpVerifyComponent.
    fixture = TestBed.createComponent(OtpVerifyComponent);
    comp    = fixture.componentInstance;

    // Patch the navigation state so ngOnInit reads the phone correctly in tests.
    // We spy on getCurrentNavigation to provide a state since Angular's test harness
    // doesn't fully replay navigation state on component creation.
    vi.spyOn(router, 'getCurrentNavigation').mockReturnValue({
      extras: { state: { phone: '+919876543210' } },
    } as unknown as ReturnType<Router['getCurrentNavigation']>);

    fixture.detectChanges();
  });

  afterEach(() => {
    // Destroy component to fire ngOnDestroy → clearInterval (no orphaned interval after test).
    fixture.destroy();
    httpMock.verify();
    vi.useRealTimers();
    vi.restoreAllMocks();
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

  it('C4 (THE CRUX) — remote onSubmit setSession WRITES through the boundary: shell reflects isAuthenticated, getToken; authGuard now passes', () => {
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
    comp.onOtpCompleted('123456');
    expect(comp.otpValue()).toBe('123456');

    comp.onSubmit();
    // Before HTTP flushes: shell is still unauthenticated.
    expect(shellAuth.isAuthenticated()).toBe(false);

    // Flush POST /api/v1/auth/otp/verify
    const verifyReq = httpMock.expectOne('/api/v1/auth/otp/verify');
    expect(verifyReq.request.method).toBe('POST');
    expect(verifyReq.request.withCredentials).toBe(true);
    verifyReq.flush(FAKE_VERIFY_RESP);

    // Flush GET /api/v1/auth/me
    const meReq = httpMock.expectOne('/api/v1/auth/me');
    expect(meReq.request.method).toBe('GET');
    meReq.flush(FAKE_ME_RESP);

    // Step 4 (THE CRUX) — shell's singleton now reflects the remote's setSession WRITE.
    expect(shellAuth.isAuthenticated()).toBe(true);
    expect(shellAuth.getToken()).toBe(FAKE_VERIFY_RESP.access_token);
    expect(shellAuth.currentUser()?.phone).toBe(FAKE_ME_RESP.phone);
    expect(shellAuth.currentUser()?.user_id).toBe(FAKE_ME_RESP.user_id);

    // Step 5 — authGuard now PASSES (returns true, not a UrlTree).
    const postWriteGuard = runInInjectionContext(envInjector, () =>
      authGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/dashboard' } as RouterStateSnapshot,
      ),
    );
    expect(postWriteGuard).toBe(true);
  });

  it('C4-abort: onSubmit is a no-op when otpValue is fewer than 6 chars (guard to prevent premature setSession)', () => {
    comp.onOtpCompleted('12345'); // 5 chars — below threshold
    comp.onSubmit();

    // No HTTP should be fired — onSubmit returns early
    httpMock.expectNone('/api/v1/auth/otp/verify');

    // No setSession fired — shell remains unauthenticated.
    expect(shellAuth.isAuthenticated()).toBe(false);
    expect(shellAuth.getToken()).toBeNull();
  });

  it('C4-error-400: onSubmit shows error message when verifyOtp returns 400 (invalid/expired OTP)', () => {
    comp.onOtpCompleted('999999');
    comp.onSubmit();

    const verifyReq = httpMock.expectOne('/api/v1/auth/otp/verify');
    verifyReq.flush({ detail: 'Invalid OTP', code: 'OTP_INVALID', validation_message_id: 'v1', request_id: 'r1' }, { status: 400, statusText: 'Bad Request' });

    // Shell stays unauthenticated
    expect(shellAuth.isAuthenticated()).toBe(false);
    // Component shows error
    expect(comp.errorMessage()).toBeTruthy();
    expect(comp.errorMessage()).toContain('Invalid or expired');
  });

  it('C4-timer: ngOnDestroy clears the resend-countdown setInterval (no orphaned timer after fixture.destroy())', () => {
    vi.useFakeTimers();

    let timerFixture: ComponentFixture<OtpVerifyComponent>;
    let timerComp: OtpVerifyComponent;

    // Mock getCurrentNavigation for this sub-fixture too
    vi.spyOn(router, 'getCurrentNavigation').mockReturnValue({
      extras: { state: { phone: '+919876543210' } },
    } as unknown as ReturnType<Router['getCurrentNavigation']>);

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

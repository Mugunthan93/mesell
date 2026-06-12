import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { OtpVerifyComponent } from './otp-verify.component';
import { AuthService } from '@mesell/core';

const FAKE_VERIFY_RESP = {
  access_token: 'real-token-abc',
  expires_in: 3600,
  token_type: 'bearer' as const,
};

const FAKE_ME_RESP = {
  user_id: 'uuid-seller-1',
  phone: '+919876543210',
  plan: 'free' as const,
  created_at: '2026-06-11T00:00:00Z',
  last_login_at: null,
};

describe('OtpVerifyComponent', () => {
  let fixture: ComponentFixture<OtpVerifyComponent>;
  let comp: OtpVerifyComponent;
  let httpMock: HttpTestingController;
  let router: Router;
  let authSvc: AuthService;

  const makeFixture = async () => {
    await TestBed.configureTestingModule({
      imports: [OtpVerifyComponent, NoopAnimationsModule],
      providers: [
        provideRouter([
          { path: 'login', children: [] },
          { path: 'dashboard', children: [] },
        ]),
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    router   = TestBed.inject(Router);
    httpMock = TestBed.inject(HttpTestingController);
    authSvc  = TestBed.inject(AuthService);
    authSvc.logout();

    // Provide phone via navigation state spy so ngOnInit doesn't redirect to /login
    vi.spyOn(router, 'getCurrentNavigation').mockReturnValue({
      extras: { state: { phone: '+919876543210' } },
    } as unknown as ReturnType<Router['getCurrentNavigation']>);

    fixture = TestBed.createComponent(OtpVerifyComponent);
    comp    = fixture.componentInstance;
    fixture.detectChanges();
  };

  beforeEach(async () => {
    vi.useRealTimers();
    TestBed.resetTestingModule();
    await makeFixture();
  });

  afterEach(() => {
    fixture.destroy();
    httpMock.verify();
    vi.useRealTimers();
    vi.restoreAllMocks();
    TestBed.resetTestingModule();
  });

  // ── Initial state ──────────────────────────────────────────────────────────

  it('should render mee-auth-layout', () => {
    expect(fixture.nativeElement.querySelector('mee-auth-layout')).toBeTruthy();
  });

  it('should initialise countdown at 30', () => {
    expect(comp.countdown()).toBe(30);
  });

  it('should not call auth.setSession on init', () => {
    expect(authSvc.isAuthenticated()).toBeFalsy();
  });

  it('should initialise otpValue as empty string', () => {
    expect(comp.otpValue()).toBe('');
  });

  it('should set otpValue when onOtpCompleted is called', () => {
    comp.onOtpCompleted('123456');
    expect(comp.otpValue()).toBe('123456');
  });

  // ── Happy-path: verifyOtp + me() → setSession + scheduleRefresh + navigate ─

  it('happy-path: verifyOtp → me() → setSession with real token, then navigate to /dashboard', () => {
    comp.onOtpCompleted('654321');

    const navigateSpy = vi.spyOn(router, 'navigate');

    comp.onSubmit();
    expect(comp.loading()).toBe(true);

    // 1. Flush POST /api/v1/auth/otp/verify
    const verifyReq = httpMock.expectOne('/api/v1/auth/otp/verify');
    expect(verifyReq.request.method).toBe('POST');
    expect(verifyReq.request.body).toEqual({ phone: '+919876543210', otp: '654321' });
    expect(verifyReq.request.withCredentials).toBe(true);  // R-W6-5: cookie path
    verifyReq.flush(FAKE_VERIFY_RESP);

    // 2. Flush GET /api/v1/auth/me
    const meReq = httpMock.expectOne('/api/v1/auth/me');
    expect(meReq.request.method).toBe('GET');
    meReq.flush(FAKE_ME_RESP);

    // 3. Auth state updated (REPLACING the old mock-token)
    expect(authSvc.isAuthenticated()).toBe(true);
    expect(authSvc.getToken()).toBe('real-token-abc');
    expect(authSvc.currentUser()?.phone).toBe('+919876543210');
    expect(authSvc.currentUser()?.user_id).toBe('uuid-seller-1');

    // 4. Loading cleared + navigation
    expect(comp.loading()).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(['/dashboard']);
  });

  it('/me failure: falls back to minimal user with phone only (graceful degradation)', () => {
    comp.onOtpCompleted('123456');
    comp.onSubmit();

    const verifyReq = httpMock.expectOne('/api/v1/auth/otp/verify');
    verifyReq.flush(FAKE_VERIFY_RESP);

    // /me returns error
    const meReq = httpMock.expectOne('/api/v1/auth/me');
    meReq.flush({}, { status: 500, statusText: 'Server Error' });

    // Still authenticated with the token, minimal user (phone only)
    expect(authSvc.isAuthenticated()).toBe(true);
    expect(authSvc.getToken()).toBe('real-token-abc');
    expect(authSvc.currentUser()?.phone).toBe('+919876543210');
  });

  // ── Error matrix ──────────────────────────────────────────────────────────

  it('onSubmit is a no-op when otpValue < 6 chars', () => {
    comp.onOtpCompleted('12345');
    comp.onSubmit();
    httpMock.expectNone('/api/v1/auth/otp/verify');
    expect(authSvc.isAuthenticated()).toBe(false);
  });

  it('400 from verifyOtp → "Invalid or expired code" error message', () => {
    comp.onOtpCompleted('000000');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/verify');
    req.flush(
      { detail: 'OTP invalid', code: 'OTP_INVALID', validation_message_id: 'v1', request_id: 'r1' },
      { status: 400, statusText: 'Bad Request' },
    );

    expect(authSvc.isAuthenticated()).toBe(false);
    expect(comp.errorMessage()).toContain('Invalid or expired');
    expect(comp.loading()).toBe(false);
  });

  it('401 from verifyOtp → "Invalid or expired code" error message', () => {
    comp.onOtpCompleted('111111');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/verify');
    req.flush({}, { status: 401, statusText: 'Unauthorized' });

    expect(comp.errorMessage()).toContain('Invalid or expired');
    expect(comp.loading()).toBe(false);
  });

  it('429 from verifyOtp → rate limit error message', () => {
    comp.onOtpCompleted('222222');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/verify');
    req.flush(
      { detail: 'Rate limited', code: 'RATE_LIMIT', validation_message_id: 'v1', request_id: 'r2' },
      { status: 429, statusText: 'Too Many Requests' },
    );

    expect(comp.errorMessage()).toContain('Too many attempts');
  });

  it('5xx from verifyOtp → generic error message', () => {
    comp.onOtpCompleted('333333');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/verify');
    req.flush({}, { status: 503, statusText: 'Service Unavailable' });

    expect(comp.errorMessage()).toContain('went wrong');
  });

  // ── Resend timer (D18/SP02 setInterval contract — PRESERVED) ─────────────
  // Uses a separate async test to configure fake timers BEFORE component creation
  // so the setInterval registers in the fake clock.

  it('resend-timer: countdown decrements every second via setInterval, clears on destroy', async () => {
    vi.useFakeTimers();

    // Create a fresh isolated module under fake timers
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [OtpVerifyComponent, NoopAnimationsModule],
      providers: [
        provideRouter([
          { path: 'login', children: [] },
          { path: 'dashboard', children: [] },
        ]),
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    const r = TestBed.inject(Router);
    vi.spyOn(r, 'getCurrentNavigation').mockReturnValue({
      extras: { state: { phone: '+919876543210' } },
    } as unknown as ReturnType<Router['getCurrentNavigation']>);

    const timerFixture = TestBed.createComponent(OtpVerifyComponent);
    const timerComp    = timerFixture.componentInstance;
    timerFixture.detectChanges();

    // Countdown starts at 30
    expect(timerComp.countdown()).toBe(30);

    // Advance 5 seconds — setInterval (1 s period) fires 5 times → countdown=25
    vi.advanceTimersByTime(5000);
    expect(timerComp.countdown()).toBe(25);

    // Destroy the component — ngOnDestroy calls clearInterval
    timerFixture.destroy();
    const valueAtDestroy = timerComp.countdown();

    // Advance further — countdown must NOT change (interval is cleared)
    vi.advanceTimersByTime(10000);
    expect(timerComp.countdown()).toBe(valueAtDestroy);

    vi.useRealTimers();
  });
});

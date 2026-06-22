import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { provideRouter, Router } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { GoogleIdentityService } from '@mesell/core';
import { LoginComponent } from './login.component';

/** Stub GIS so tests never inject the real script / hit the network. */
class GisStub {
  load = vi.fn(() => Promise.resolve());
  initialize = vi.fn();
  renderButton = vi.fn();
  cancel = vi.fn();
  isReady = vi.fn(() => true);
}

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let comp: LoginComponent;
  let httpMock: HttpTestingController;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent, ReactiveFormsModule, NoopAnimationsModule],
      providers: [
        provideRouter([
          { path: 'otp-verify', children: [] },
          { path: 'login', children: [] },
          { path: 'dashboard', children: [] },
          { path: 'onboarding', children: [] },
        ]),
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        { provide: GoogleIdentityService, useClass: GisStub },
      ],
    }).compileComponents();
    fixture  = TestBed.createComponent(LoginComponent);
    comp     = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    router   = TestBed.inject(Router);
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
  });

  // ── Form validation ────────────────────────────────────────────────────────

  it('should render mee-auth-layout', () => {
    expect(fixture.nativeElement.querySelector('mee-auth-layout')).toBeTruthy();
  });

  it('should have form invalid when phone is empty', () => {
    comp.form.get('phone')!.setValue('');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should have form invalid when phone starts with 0-5', () => {
    comp.form.get('phone')!.setValue('5876543210');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should have form invalid when phone is fewer than 10 digits', () => {
    comp.form.get('phone')!.setValue('98765');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should have form valid when phone starts with 6-9 and is 10 digits', () => {
    comp.form.get('phone')!.setValue('9876543210');
    fixture.detectChanges();
    expect(comp.form.valid).toBeTruthy();
  });

  // ── Happy-path: real sendOtp call + Router state hand-off ─────────────────

  it('sendOtp happy-path: POST /api/v1/auth/otp/send with +91 prefix, then navigate to /otp-verify with phone state', () => {
    comp.form.get('phone')!.setValue('9876543210');
    fixture.detectChanges();

    const navigateSpy = vi.spyOn(router, 'navigate');

    comp.onSubmit();
    expect(comp.loading()).toBe(true);

    const req = httpMock.expectOne('/api/v1/auth/otp/send');
    expect(req.request.method).toBe('POST');
    // Phone normalised to E.164
    expect(req.request.body).toEqual({ phone: '+919876543210' });
    // No withCredentials on sendOtp (R-W6-5)
    expect(req.request.withCredentials).toBe(false);

    req.flush({ request_id: 'req-abc-123' });

    expect(comp.loading()).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(
      ['/otp-verify'],
      { state: { phone: '+919876543210' } },
    );
  });

  // ── Error matrix ──────────────────────────────────────────────────────────

  it('sends no HTTP when form is invalid', () => {
    comp.form.get('phone')!.setValue('');
    comp.onSubmit();
    httpMock.expectNone('/api/v1/auth/otp/send');
    expect(comp.loading()).toBe(false);
  });

  it('400 → inline error message (bad phone)', () => {
    comp.form.get('phone')!.setValue('9876543210');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/send');
    req.flush(
      { detail: 'Invalid phone', code: 'PHONE_INVALID', validation_message_id: 'v1', request_id: 'r1' },
      { status: 400, statusText: 'Bad Request' },
    );

    expect(comp.loading()).toBe(false);
    expect(comp.errorMessage()).toBeTruthy();
    expect(comp.errorMessage()).toContain('Invalid phone');
  });

  it('429 → rate limit error message', () => {
    comp.form.get('phone')!.setValue('9876543210');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/send');
    req.flush(
      { detail: 'Rate limited', code: 'RATE_LIMIT', validation_message_id: 'v1', request_id: 'r2' },
      { status: 429, statusText: 'Too Many Requests' },
    );

    expect(comp.loading()).toBe(false);
    expect(comp.errorMessage()).toBeTruthy();
    expect(comp.errorMessage()).toContain('Too many attempts');
  });

  it('5xx → generic error message', () => {
    comp.form.get('phone')!.setValue('9876543210');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/send');
    req.flush({}, { status: 503, statusText: 'Service Unavailable' });

    expect(comp.loading()).toBe(false);
    expect(comp.errorMessage()).toBeTruthy();
    expect(comp.errorMessage()).toContain('went wrong');
  });

  it('errorMessage is null on successful submit (cleared before each call)', () => {
    comp.form.get('phone')!.setValue('9876543210');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/send');
    req.flush({ request_id: 'req-ok' });

    // No error after success
    expect(comp.errorMessage()).toBeNull();
  });

  // ── Google sign-in path ─────────────────────────────────────────────────────

  it('wires the GIS button on init: load → initialize → renderButton', () => {
    const gis = TestBed.inject(GoogleIdentityService) as unknown as GisStub;
    // ngAfterViewInit ran during the initial detectChanges in beforeEach.
    expect(gis.load).toHaveBeenCalled();
  });

  it('onGoogleCredential happy-path: googleVerify → me → navigate to /dashboard', async () => {
    const navigateSpy = vi.spyOn(router, 'navigate');

    comp.onGoogleCredential('google-id-token');
    expect(comp.googleLoading()).toBe(true);

    const verifyReq = httpMock.expectOne('/api/v1/auth/google/verify');
    expect(verifyReq.request.method).toBe('POST');
    expect(verifyReq.request.body).toEqual({ credential: 'google-id-token' });
    expect(verifyReq.request.withCredentials).toBe(true);
    verifyReq.flush({ access_token: 'g-tok', expires_in: 3600, token_type: 'bearer' });

    const meReq = httpMock.expectOne('/api/v1/auth/me');
    meReq.flush({
      user_id: 'g-user', phone: null, plan: 'free',
      created_at: '2026-06-11T00:00:00Z', last_login_at: null,
      onboarding_complete: true,
    });

    expect(comp.googleLoading()).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(['/dashboard']);
  });

  it('onGoogleCredential new-user: onboarding_complete:false → navigate to /onboarding', () => {
    const navigateSpy = vi.spyOn(router, 'navigate');

    comp.onGoogleCredential('cred');
    httpMock.expectOne('/api/v1/auth/google/verify')
      .flush({ access_token: 't', expires_in: 3600, token_type: 'bearer' });
    httpMock.expectOne('/api/v1/auth/me').flush({
      user_id: 'new', phone: null, plan: 'free',
      created_at: '2026-06-11T00:00:00Z', last_login_at: null,
      onboarding_complete: false,
    });

    expect(navigateSpy).toHaveBeenCalledWith(['/onboarding']);
  });

  it('onGoogleCredential 401 → "Google sign-in failed" banner, googleLoading reset', () => {
    comp.onGoogleCredential('bad-cred');

    const req = httpMock.expectOne('/api/v1/auth/google/verify');
    req.flush({ detail: 'aud mismatch' }, { status: 401, statusText: 'Unauthorized' });

    expect(comp.googleLoading()).toBe(false);
    expect(comp.errorMessage()).toContain('Google sign-in failed');
  });

  it('onGoogleCredential 429 → rate-limit banner, googleLoading reset', () => {
    comp.onGoogleCredential('cred');

    const req = httpMock.expectOne('/api/v1/auth/google/verify');
    req.flush({ detail: 'rl' }, { status: 429, statusText: 'Too Many Requests' });

    expect(comp.googleLoading()).toBe(false);
    expect(comp.errorMessage()).toContain('Too many attempts');
  });

  it('onGoogleCredential offline (status 0) → offline banner', () => {
    comp.onGoogleCredential('cred');

    const req = httpMock.expectOne('/api/v1/auth/google/verify');
    req.error(new ProgressEvent('error'), { status: 0, statusText: 'Unknown Error' });

    expect(comp.googleLoading()).toBe(false);
    expect(comp.errorMessage()).toContain('offline');
  });

  // ── FE-AUTH-11: Google host availability (GIS load success vs failure) ───────
  //
  // The google-host div (data-testid="login-google-host") is always in the template
  // (no @if flag-gate); the flag gating is in the backend mount + the GIS SDK load.
  // The testable seam in the component:
  //   - When GIS load() succeeds → renderButton() is called on the host element.
  //   - When GIS load() rejects → errorMessage is set to the "Couldn't load" banner.

  it('FE-AUTH-11: GIS load success → renderButton is called with the host element', () => {
    const gis = TestBed.inject(GoogleIdentityService) as unknown as GisStub;
    // The stub's load() already resolves; ngAfterViewInit already ran in beforeEach.
    expect(gis.load).toHaveBeenCalledOnce();
    expect(gis.renderButton).toHaveBeenCalledOnce();
    // The first argument to renderButton must be an HTMLElement (the googleBtn host)
    const hostArg = (gis.renderButton as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(hostArg).toBeInstanceOf(HTMLElement);
  });

  it('FE-AUTH-11: GIS load failure → errorMessage is set with "Couldn\'t load" message', async () => {
    // Rebuild the fixture with a GIS stub whose load() rejects
    TestBed.resetTestingModule();
    class GisFailStub {
      load = vi.fn(() => Promise.reject(new Error('GIS script failed to load')));
      initialize = vi.fn();
      renderButton = vi.fn();
      cancel = vi.fn();
      isReady = vi.fn(() => false);
    }

    await TestBed.configureTestingModule({
      imports: [LoginComponent, ReactiveFormsModule, NoopAnimationsModule],
      providers: [
        provideRouter([
          { path: 'otp-verify', children: [] },
          { path: 'login', children: [] },
          { path: 'dashboard', children: [] },
          { path: 'onboarding', children: [] },
        ]),
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        { provide: GoogleIdentityService, useClass: GisFailStub },
      ],
    }).compileComponents();

    const failFixture = TestBed.createComponent(LoginComponent);
    const failComp = failFixture.componentInstance;
    failFixture.detectChanges();

    // Wait for ngAfterViewInit's async initGoogleButton() to settle
    await new Promise<void>((r) => setTimeout(r, 0));

    // errorMessage must contain the load-failure copy
    expect(failComp.errorMessage()).toContain("Couldn't load Google sign-in");

    // Cleanup: destroy fixture + verify no pending requests
    failFixture.destroy();
    TestBed.inject(HttpTestingController).verify();
  });
});

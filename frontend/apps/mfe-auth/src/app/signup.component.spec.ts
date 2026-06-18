import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { provideRouter, Router } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { GoogleIdentityService } from '@mesell/core';
import { SignupComponent } from './signup.component';

/** Stub GIS so tests never inject the real script / hit the network. */
class GisStub {
  load = vi.fn(() => Promise.resolve());
  initialize = vi.fn();
  renderButton = vi.fn();
  cancel = vi.fn();
  isReady = vi.fn(() => true);
}

describe('SignupComponent', () => {
  let fixture: ComponentFixture<SignupComponent>;
  let comp: SignupComponent;
  let httpMock: HttpTestingController;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SignupComponent, ReactiveFormsModule, NoopAnimationsModule],
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
    fixture  = TestBed.createComponent(SignupComponent);
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

  it('should be invalid when name is empty', () => {
    comp.form.get('name')!.setValue('');
    comp.form.get('phone')!.setValue('9876543210');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should be invalid when phone is invalid', () => {
    comp.form.get('name')!.setValue('Test');
    comp.form.get('phone')!.setValue('12345');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should be valid when name and phone are both valid', () => {
    comp.form.get('name')!.setValue('Test Seller');
    comp.form.get('phone')!.setValue('9876543210');
    fixture.detectChanges();
    expect(comp.form.valid).toBeTruthy();
  });

  // ── Happy-path: real sendOtp call + Router state hand-off ─────────────────

  it('sendOtp happy-path: POST /api/v1/auth/otp/send with +91 prefix, then navigate to /otp-verify with phone state', () => {
    comp.form.get('name')!.setValue('Test Seller');
    comp.form.get('phone')!.setValue('9876543210');
    fixture.detectChanges();

    const navigateSpy = vi.spyOn(router, 'navigate');

    comp.onSubmit();
    expect(comp.loading()).toBe(true);

    const req = httpMock.expectOne('/api/v1/auth/otp/send');
    expect(req.request.method).toBe('POST');
    // Phone normalised to E.164 (+91 prepended)
    expect(req.request.body).toEqual({ phone: '+919876543210' });
    expect(req.request.withCredentials).toBe(false);

    req.flush({ request_id: 'req-xyz-456' });

    expect(comp.loading()).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(
      ['/otp-verify'],
      { state: { phone: '+919876543210' } },
    );
  });

  // ── Error matrix ──────────────────────────────────────────────────────────

  it('sends no HTTP when form is invalid', () => {
    comp.form.get('name')!.setValue('');
    comp.form.get('phone')!.setValue('');
    comp.onSubmit();
    httpMock.expectNone('/api/v1/auth/otp/send');
    expect(comp.loading()).toBe(false);
  });

  it('429 → rate limit error message', () => {
    comp.form.get('name')!.setValue('Test Seller');
    comp.form.get('phone')!.setValue('9876543210');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/send');
    req.flush(
      { detail: 'Rate limited', code: 'RATE_LIMIT', validation_message_id: 'v1', request_id: 'r1' },
      { status: 429, statusText: 'Too Many Requests' },
    );

    expect(comp.loading()).toBe(false);
    expect(comp.errorMessage()).toContain('Too many attempts');
  });

  it('400 → invalid phone error message', () => {
    comp.form.get('name')!.setValue('Test Seller');
    comp.form.get('phone')!.setValue('9876543210');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/send');
    req.flush(
      { detail: 'Bad phone', code: 'PHONE_INVALID', validation_message_id: 'v1', request_id: 'r2' },
      { status: 400, statusText: 'Bad Request' },
    );

    expect(comp.loading()).toBe(false);
    expect(comp.errorMessage()).toContain('Invalid phone');
  });

  it('5xx → generic error message', () => {
    comp.form.get('name')!.setValue('Test Seller');
    comp.form.get('phone')!.setValue('9876543210');
    comp.onSubmit();

    const req = httpMock.expectOne('/api/v1/auth/otp/send');
    req.flush({}, { status: 500, statusText: 'Internal Server Error' });

    expect(comp.loading()).toBe(false);
    expect(comp.errorMessage()).toContain('went wrong');
  });

  // ── Google sign-in path ─────────────────────────────────────────────────────

  it('wires the GIS button on init: load called', () => {
    const gis = TestBed.inject(GoogleIdentityService) as unknown as GisStub;
    expect(gis.load).toHaveBeenCalled();
  });

  it('onGoogleCredential happy-path: googleVerify → me → navigate (onboarding gate)', () => {
    const navigateSpy = vi.spyOn(router, 'navigate');

    comp.onGoogleCredential('google-id-token');
    expect(comp.googleLoading()).toBe(true);

    const verifyReq = httpMock.expectOne('/api/v1/auth/google/verify');
    expect(verifyReq.request.body).toEqual({ credential: 'google-id-token' });
    expect(verifyReq.request.withCredentials).toBe(true);
    verifyReq.flush({ access_token: 'g-tok', expires_in: 3600, token_type: 'bearer' });

    // New Google sign-up → onboarding_complete:false → /onboarding.
    httpMock.expectOne('/api/v1/auth/me').flush({
      user_id: 'g-new', phone: null, plan: 'free',
      created_at: '2026-06-11T00:00:00Z', last_login_at: null,
      onboarding_complete: false,
    });

    expect(comp.googleLoading()).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(['/onboarding']);
  });

  it('onGoogleCredential 400 → "Google sign-in failed" banner, googleLoading reset', () => {
    comp.onGoogleCredential('bad');

    const req = httpMock.expectOne('/api/v1/auth/google/verify');
    req.flush({ detail: 'invalid token' }, { status: 400, statusText: 'Bad Request' });

    expect(comp.googleLoading()).toBe(false);
    expect(comp.errorMessage()).toContain('Google sign-in failed');
  });
});

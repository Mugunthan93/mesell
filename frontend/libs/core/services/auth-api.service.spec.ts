/**
 * auth-api.service.spec.ts — Wave 6 Wave A
 *
 * Tests AuthApiService HTTP methods:
 * - sendOtp: POST /api/v1/auth/otp/send — no withCredentials
 * - verifyOtp: POST /api/v1/auth/otp/verify — withCredentials: true
 * - refresh: POST /api/v1/auth/refresh — withCredentials: true
 * - logout: POST /api/v1/auth/logout — withCredentials: true
 * - me: GET /api/v1/auth/me — no withCredentials (Bearer-auth, R-W6-5)
 */

import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';

import { AuthApiService } from './auth-api.service';
import type { SendOtpResponse, VerifyOtpResponse, RefreshResponse, MeResponse } from './auth-api.service';

// ── Setup ─────────────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [
      AuthApiService,
      provideHttpClient(withFetch()),
      provideHttpClientTesting(),
    ],
  });
  return {
    service:    TestBed.inject(AuthApiService),
    controller: TestBed.inject(HttpTestingController),
  };
}

afterEach(() => {
  TestBed.inject(HttpTestingController).verify();
});

// ── sendOtp ───────────────────────────────────────────────────────────────────

describe('AuthApiService.sendOtp()', () => {
  it('POSTs to /api/v1/auth/otp/send with the phone body', () => {
    const { service, controller } = setup();
    const phone = '+919876543210';
    const result: SendOtpResponse[] = [];

    service.sendOtp(phone).subscribe((r) => result.push(r));

    const req = controller.expectOne('/api/v1/auth/otp/send');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ phone });
    req.flush({ request_id: 'req-xyz' });

    expect(result[0].request_id).toBe('req-xyz');
  });

  it('does NOT use withCredentials (public endpoint)', () => {
    const { service, controller } = setup();

    service.sendOtp('+919876543210').subscribe();

    const req = controller.expectOne('/api/v1/auth/otp/send');
    expect(req.request.withCredentials).toBe(false);
    req.flush({ request_id: 'r' });
  });
});

// ── verifyOtp ─────────────────────────────────────────────────────────────────

describe('AuthApiService.verifyOtp()', () => {
  it('POSTs to /api/v1/auth/otp/verify with phone + otp', () => {
    const { service, controller } = setup();
    const result: VerifyOtpResponse[] = [];

    service.verifyOtp('+919876543210', '123456').subscribe((r) => result.push(r));

    const req = controller.expectOne('/api/v1/auth/otp/verify');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ phone: '+919876543210', otp: '123456' });
    req.flush({ access_token: 'tok', expires_in: 900, token_type: 'bearer' });

    expect(result[0].access_token).toBe('tok');
    expect(result[0].expires_in).toBe(900);
  });

  it('uses withCredentials: true (refresh cookie is set by backend)', () => {
    const { service, controller } = setup();

    service.verifyOtp('+91123', '000000').subscribe();

    const req = controller.expectOne('/api/v1/auth/otp/verify');
    expect(req.request.withCredentials).toBe(true);
    req.flush({ access_token: 't', expires_in: 900, token_type: 'bearer' });
  });
});

// ── refresh ───────────────────────────────────────────────────────────────────

describe('AuthApiService.refresh()', () => {
  it('POSTs to /api/v1/auth/refresh with withCredentials: true', () => {
    const { service, controller } = setup();
    const result: RefreshResponse[] = [];

    service.refresh().subscribe((r) => result.push(r));

    const req = controller.expectOne('/api/v1/auth/refresh');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    req.flush({ access_token: 'new-tok', expires_in: 900, token_type: 'bearer' });

    expect(result[0].access_token).toBe('new-tok');
  });
});

// ── logout ────────────────────────────────────────────────────────────────────

describe('AuthApiService.logout()', () => {
  it('POSTs to /api/v1/auth/logout with withCredentials: true', () => {
    const { service, controller } = setup();
    let completed = false;

    service.logout().subscribe({ complete: () => { completed = true; } });

    const req = controller.expectOne('/api/v1/auth/logout');
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    req.flush(null, { status: 204, statusText: 'No Content' });

    expect(completed).toBe(true);
  });
});

// ── me ────────────────────────────────────────────────────────────────────────

describe('AuthApiService.me()', () => {
  it('GETs /api/v1/auth/me and returns MeResponse', () => {
    const { service, controller } = setup();
    const result: MeResponse[] = [];

    service.me().subscribe((r) => result.push(r));

    const req = controller.expectOne('/api/v1/auth/me');
    expect(req.request.method).toBe('GET');
    req.flush({
      user_id: 'uuid-123',
      phone: '+919876543210',
      plan: 'free',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    });

    expect(result[0].user_id).toBe('uuid-123');
    expect(result[0].phone).toBe('+919876543210');
    expect(result[0].plan).toBe('free');
    expect(result[0].last_login_at).toBeNull();
  });

  it('does NOT use withCredentials (Bearer-auth only — R-W6-5)', () => {
    const { service, controller } = setup();

    service.me().subscribe();

    const req = controller.expectOne('/api/v1/auth/me');
    expect(req.request.withCredentials).toBe(false);
    req.flush({ user_id: 'u', phone: '+91x', plan: 'free', created_at: '', last_login_at: null });
  });
});

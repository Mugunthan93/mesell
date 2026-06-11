/**
 * jwt.interceptor.spec.ts — Wave 6 Wave A
 *
 * Tests jwtInterceptor using Angular HttpTestingController.
 * Verifies:
 *   - Authorization: Bearer header attached when token is present on non-/auth/* requests
 *   - No header added when token is null
 *   - /api/v1/auth/* requests are skipped (no Bearer added — they are cookie-auth or public)
 */

import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';

import { AuthService } from '../services/auth.service';
import { jwtInterceptor } from './jwt.interceptor';

// ── Minimal mock AuthService ───────────────────────────────────────────────────

function makeAuthMock(token: string | null) {
  return { getToken: () => token } as Pick<AuthService, 'getToken'>;
}

// ── Setup ─────────────────────────────────────────────────────────────────────

function setup(token: string | null) {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withFetch(), withInterceptors([jwtInterceptor])),
      provideHttpClientTesting(),
      { provide: AuthService, useValue: makeAuthMock(token) },
    ],
  });
  return {
    http:       TestBed.inject(HttpClient),
    controller: TestBed.inject(HttpTestingController),
  };
}

afterEach(() => {
  TestBed.inject(HttpTestingController).verify();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('jwtInterceptor — token present', () => {
  it('attaches Authorization: Bearer <token> on non-/auth/* GET', () => {
    const { http, controller } = setup('my-jwt-token');

    http.get('/api/v1/categories/suggest').subscribe();

    const req = controller.expectOne('/api/v1/categories/suggest');
    expect(req.request.headers.get('Authorization')).toBe('Bearer my-jwt-token');
    req.flush({});
  });

  it('attaches Authorization header on POST to non-/auth/* path', () => {
    const { http, controller } = setup('post-token');

    http.post('/api/v1/products', { category_id: 'x' }).subscribe();

    const req = controller.expectOne('/api/v1/products');
    expect(req.request.headers.get('Authorization')).toBe('Bearer post-token');
    req.flush({ id: '1' });
  });
});

describe('jwtInterceptor — token null', () => {
  it('does NOT attach Authorization header when token is null', () => {
    const { http, controller } = setup(null);

    http.get('/api/v1/categories/suggest').subscribe();

    const req = controller.expectOne('/api/v1/categories/suggest');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush({});
  });
});

describe('jwtInterceptor — /api/v1/auth/* skip rule', () => {
  it('does NOT attach Bearer on POST /api/v1/auth/otp/send even when token exists', () => {
    const { http, controller } = setup('valid-token');

    http.post('/api/v1/auth/otp/send', { phone: '+919876543210' }).subscribe();

    const req = controller.expectOne('/api/v1/auth/otp/send');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush({ request_id: 'req-1' });
  });

  it('does NOT attach Bearer on POST /api/v1/auth/otp/verify', () => {
    const { http, controller } = setup('valid-token');

    http.post('/api/v1/auth/otp/verify', { phone: '+91123', otp: '123456' }).subscribe();

    const req = controller.expectOne('/api/v1/auth/otp/verify');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush({ access_token: 'tok', expires_in: 900, token_type: 'bearer' });
  });

  it('does NOT attach Bearer on POST /api/v1/auth/refresh', () => {
    const { http, controller } = setup('valid-token');

    http.post('/api/v1/auth/refresh', {}).subscribe();

    const req = controller.expectOne('/api/v1/auth/refresh');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush({ access_token: 'new-tok', expires_in: 900, token_type: 'bearer' });
  });

  it('does NOT attach Bearer on POST /api/v1/auth/logout', () => {
    const { http, controller } = setup('valid-token');

    http.post('/api/v1/auth/logout', {}).subscribe();

    const req = controller.expectOne('/api/v1/auth/logout');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush(null, { status: 204, statusText: 'No Content' });
  });

  it('does NOT attach Bearer on GET /api/v1/auth/me', () => {
    // /auth/me uses Bearer (jwtInterceptor DOES skip it because it contains /api/v1/auth/).
    // The intent: auth endpoints should not have stale tokens from the interceptor.
    // The real /me call (from AuthApiService) would only be made AFTER a valid access_token exists,
    // so Bearer from the interceptor on /me is safe but the skip rule is belt-and-suspenders.
    const { http, controller } = setup('valid-token');

    http.get('/api/v1/auth/me').subscribe();

    const req = controller.expectOne('/api/v1/auth/me');
    // jwtInterceptor skips /api/v1/auth/* — no Bearer added
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush({ user_id: 'uid', phone: '+91123', plan: 'free', created_at: '', last_login_at: null });
  });
});

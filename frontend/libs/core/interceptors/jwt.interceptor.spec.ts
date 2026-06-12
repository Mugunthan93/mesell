/**
 * jwt.interceptor.spec.ts — Wave 6 Wave A (rev 2: /me fix)
 *
 * Tests jwtInterceptor using Angular HttpTestingController.
 * Verifies:
 *   - Authorization: Bearer header attached when token is present on non-/auth/* requests
 *   - No header added when token is null
 *   - /api/v1/auth/otp/send, /otp/verify, /refresh, /logout: skip Bearer (public or cookie-auth)
 *   - /api/v1/auth/me: DOES get Bearer (it is Bearer-protected on backend via Depends(get_current_user))
 *
 * Fix from RESUME session: the original broad /api/v1/auth/* skip incorrectly excluded /auth/me
 * which is a Bearer-protected endpoint. The fix uses explicit path matching (SKIP_BEARER_PATHS).
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

describe('jwtInterceptor — SKIP_BEARER_PATHS (cookie-auth + public endpoints)', () => {
  it('does NOT attach Bearer on POST /api/v1/auth/otp/send (public endpoint)', () => {
    const { http, controller } = setup('valid-token');

    http.post('/api/v1/auth/otp/send', { phone: '+919876543210' }).subscribe();

    const req = controller.expectOne('/api/v1/auth/otp/send');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush({ request_id: 'req-1' });
  });

  it('does NOT attach Bearer on POST /api/v1/auth/otp/verify (OTP exchange, no prior token)', () => {
    const { http, controller } = setup('valid-token');

    http.post('/api/v1/auth/otp/verify', { phone: '+91123', otp: '123456' }).subscribe();

    const req = controller.expectOne('/api/v1/auth/otp/verify');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush({ access_token: 'tok', expires_in: 900, token_type: 'bearer' });
  });

  it('does NOT attach Bearer on POST /api/v1/auth/refresh (cookie-auth path)', () => {
    const { http, controller } = setup('valid-token');

    http.post('/api/v1/auth/refresh', {}).subscribe();

    const req = controller.expectOne('/api/v1/auth/refresh');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush({ access_token: 'new-tok', expires_in: 900, token_type: 'bearer' });
  });

  it('does NOT attach Bearer on POST /api/v1/auth/logout (cookie-auth path)', () => {
    const { http, controller } = setup('valid-token');

    http.post('/api/v1/auth/logout', {}).subscribe();

    const req = controller.expectOne('/api/v1/auth/logout');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush(null, { status: 204, statusText: 'No Content' });
  });
});

describe('jwtInterceptor — /api/v1/auth/me GETS Bearer (Bearer-protected endpoint)', () => {
  it('DOES attach Bearer on GET /api/v1/auth/me when token exists', () => {
    // /auth/me is Bearer-protected on the backend (Depends(get_current_user) in iam/router.py L226).
    // It is NOT in SKIP_BEARER_PATHS — it needs a Bearer token to identify the user.
    // RESUME fix: the original broad /api/v1/auth/* skip incorrectly excluded /me → 401 in production.
    const { http, controller } = setup('valid-token');

    http.get('/api/v1/auth/me').subscribe();

    const req = controller.expectOne('/api/v1/auth/me');
    // /me is NOT in SKIP_BEARER_PATHS → Bearer IS attached
    expect(req.request.headers.get('Authorization')).toBe('Bearer valid-token');
    req.flush({ user_id: 'uid', phone: '+91123', plan: 'free', created_at: '', last_login_at: null });
  });

  it('does NOT attach Bearer on GET /api/v1/auth/me when token is null', () => {
    const { http, controller } = setup(null);

    http.get('/api/v1/auth/me').subscribe();

    const req = controller.expectOne('/api/v1/auth/me');
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush({ user_id: 'uid', phone: '+91123', plan: 'free', created_at: '', last_login_at: null });
  });
});

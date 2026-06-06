// core/auth/auth.service.spec.ts
// Covers: bootstrap(), setAccess(), scheduleRefresh(), logout(), clear()
// FE-D5: verifies no localStorage writes
// Uses Vitest native fake timers instead of Angular fakeAsync (no zone.js/testing required)

import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { describe, expect, it, vi, afterEach, beforeEach } from 'vitest';
import { AuthService } from './auth.service';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';

const BASE = 'https://api.test/api/v1';

// Compact valid JWT payload: sub + exp + plan
function makeJwt(expOffsetSeconds = 3600): string {
  const payload = {
    sub: 'user-123',
    exp: Math.floor(Date.now() / 1000) + expOffsetSeconds,
    plan: 'free',
  };
  const encoded = btoa(JSON.stringify(payload)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  return `header.${encoded}.sig`;
}

describe('AuthService', () => {
  let auth: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: API_BASE_URL, useValue: BASE },
        AuthService,
      ],
    });
    auth = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    vi.restoreAllMocks();
    vi.useRealTimers();
    localStorage.clear();
  });

  // ── Initial state ──

  it('starts with null accessToken', () => {
    expect(auth.accessToken()).toBeNull();
  });

  it('starts unauthenticated', () => {
    expect(auth.isAuthenticated()).toBe(false);
  });

  it('computes null userId when not authenticated', () => {
    expect(auth.userId()).toBeNull();
  });

  // ── setAccess ──

  it('setAccess() sets in-memory accessToken signal', () => {
    const token = makeJwt();
    auth.setAccess({ access_token: token, expires_in: 3600 });
    expect(auth.accessToken()).toBe(token);
    expect(auth.isAuthenticated()).toBe(true);
  });

  it('setAccess() decodes userId from JWT sub claim', () => {
    auth.setAccess({ access_token: makeJwt(), expires_in: 3600 });
    expect(auth.userId()).toBe('user-123');
  });

  it('setAccess() decodes plan from JWT plan claim', () => {
    auth.setAccess({ access_token: makeJwt(), expires_in: 3600 });
    expect(auth.plan()).toBe('free');
  });

  // ── FE-D5: no localStorage writes ──

  it('setAccess() does NOT write to localStorage (FE-D5)', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
    auth.setAccess({ access_token: makeJwt(), expires_in: 3600 });
    expect(setItemSpy).not.toHaveBeenCalled();
  });

  // ── bootstrap — subscribe first, then flush ──

  it('bootstrap() posts to /auth/refresh with withCredentials and returns true on success', () => {
    const token = makeJwt();
    let result: boolean | null = null;

    // Subscribe first to trigger the HTTP request
    auth.bootstrap().subscribe(v => { result = v; });

    // Now flush
    const req = httpMock.expectOne(`${BASE}/auth/refresh`);
    expect(req.request.withCredentials).toBe(true);
    req.flush({ access_token: token, expires_in: 3600 });

    expect(result).toBe(true);
    expect(auth.isAuthenticated()).toBe(true);
  });

  it('bootstrap() returns false on 401', () => {
    let result: boolean | null = null;

    auth.bootstrap().subscribe(v => { result = v; });

    httpMock.expectOne(`${BASE}/auth/refresh`).flush(null, {
      status: 401,
      statusText: 'Unauthorized',
    });

    expect(result).toBe(false);
    expect(auth.isAuthenticated()).toBe(false);
  });

  // ── clear ──

  it('clear() wipes accessToken to null', () => {
    auth.setAccess({ access_token: makeJwt(), expires_in: 3600 });
    auth.clear();
    expect(auth.accessToken()).toBeNull();
    expect(auth.isAuthenticated()).toBe(false);
  });

  // ── logout ──

  it('logout() clears token immediately and posts to /auth/logout', () => {
    auth.setAccess({ access_token: makeJwt(), expires_in: 3600 });

    auth.logout().subscribe();

    // Token should be cleared synchronously before the HTTP call resolves
    expect(auth.isAuthenticated()).toBe(false);

    const req = httpMock.expectOne(`${BASE}/auth/logout`);
    expect(req.request.withCredentials).toBe(true);
    req.flush(null);
  });

  it('logout() does NOT write to localStorage (FE-D5)', () => {
    auth.setAccess({ access_token: makeJwt(), expires_in: 3600 });
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');

    auth.logout().subscribe();
    httpMock.expectOne(`${BASE}/auth/logout`).flush(null);

    expect(setItemSpy).not.toHaveBeenCalled();
  });

  // ── scheduleRefresh (using Vitest fake timers) ──

  it('scheduleRefresh() fires another /auth/refresh at (expiresIn - 30)s', () => {
    vi.useFakeTimers();
    auth.setAccess({ access_token: makeJwt(3600), expires_in: 3600 });

    // No pending refresh yet (the setAccess call above schedules but hasn't fired)
    httpMock.expectNone(`${BASE}/auth/refresh`);

    // Advance timer to just before the trigger
    vi.advanceTimersByTime((3600 - 30) * 1000 - 100);
    httpMock.expectNone(`${BASE}/auth/refresh`);

    // Advance past the trigger point
    vi.advanceTimersByTime(200);

    // The scheduled refresh fires — subscribe needed to trigger HttpClient
    const refreshReq = httpMock.expectOne(`${BASE}/auth/refresh`);
    refreshReq.flush({ access_token: makeJwt(3600), expires_in: 3600 });

    expect(auth.isAuthenticated()).toBe(true);
  });

  it('clear() cancels scheduled refresh', () => {
    vi.useFakeTimers();
    auth.setAccess({ access_token: makeJwt(3600), expires_in: 3600 });
    auth.clear();

    // Advance past scheduled time — no HTTP call should fire
    vi.advanceTimersByTime((3600 - 30) * 1000 + 1000);
    httpMock.expectNone(`${BASE}/auth/refresh`);
  });
});

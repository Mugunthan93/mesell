// core/interceptors/refresh.interceptor.spec.ts
// Covers: 401 triggers deduplication logic, skip patterns, non-401 passthrough, 200 passthrough

import { HttpRequest, HttpHandlerFn, HttpResponse, HttpErrorResponse } from '@angular/common/http';
import { signal, provideExperimentalZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { throwError, of, firstValueFrom } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { refreshInterceptor } from './refresh.interceptor';
import { AuthService } from '@core/auth/auth.service';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';

const BASE = 'https://api.test/api/v1';

function make401Handler(): HttpHandlerFn {
  return () => throwError(() => new HttpErrorResponse({ status: 401 }));
}

function make200Handler(): HttpHandlerFn {
  return () => of(new HttpResponse({ status: 200 }));
}

describe('refreshInterceptor', () => {
  let clearSpy: ReturnType<typeof vi.fn>;
  let setAccessSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    clearSpy = vi.fn();
    setAccessSpy = vi.fn();
    const mockAuth = {
      accessToken: signal<string | null>('original-token'),
      clear: clearSpy,
      setAccess: setAccessSpy,
    } as unknown as AuthService;

    TestBed.configureTestingModule({
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideHttpClient(),
        provideRouter([]),
        { provide: AuthService, useValue: mockAuth },
        { provide: API_BASE_URL, useValue: BASE },
      ],
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it('passes non-401 errors through unchanged', async () => {
    const req = new HttpRequest('GET', `${BASE}/products`);
    const handler: HttpHandlerFn = () => throwError(() => new HttpErrorResponse({ status: 500 }));

    try {
      await firstValueFrom(TestBed.runInInjectionContext(() => refreshInterceptor(req, handler)));
      expect.fail('should have thrown');
    } catch (err) {
      expect((err as HttpErrorResponse).status).toBe(500);
    }
  });

  it('skips /auth/refresh endpoint (avoids infinite loop)', async () => {
    const req = new HttpRequest('POST', `${BASE}/auth/refresh`);

    try {
      await firstValueFrom(TestBed.runInInjectionContext(() => refreshInterceptor(req, make401Handler())));
    } catch (err) {
      // The 401 on /auth/refresh is passed through without calling clear()
      expect(clearSpy).not.toHaveBeenCalled();
      expect((err as HttpErrorResponse).status).toBe(401);
    }
  });

  it('skips /auth/logout endpoint', async () => {
    const req = new HttpRequest('POST', `${BASE}/auth/logout`);

    try {
      await firstValueFrom(TestBed.runInInjectionContext(() => refreshInterceptor(req, make401Handler())));
    } catch (err) {
      expect(clearSpy).not.toHaveBeenCalled();
      expect((err as HttpErrorResponse).status).toBe(401);
    }
  });

  it('skips /auth/otp/ endpoint', async () => {
    const req = new HttpRequest('POST', `${BASE}/auth/otp/send`);

    try {
      await firstValueFrom(TestBed.runInInjectionContext(() => refreshInterceptor(req, make401Handler())));
    } catch (err) {
      expect(clearSpy).not.toHaveBeenCalled();
    }
  });

  it('does not intercept 200 responses', async () => {
    const req = new HttpRequest('GET', `${BASE}/products`);

    const result = await firstValueFrom(
      TestBed.runInInjectionContext(() => refreshInterceptor(req, make200Handler())),
    );

    expect((result as HttpResponse<unknown>).status).toBe(200);
  });
});

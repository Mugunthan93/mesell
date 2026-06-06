// core/interceptors/jwt.interceptor.spec.ts
// Covers: Bearer attachment, skip patterns, no-token passthrough

import { HttpRequest, HttpHandlerFn, HttpResponse } from '@angular/common/http';
import { signal, provideExperimentalZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it, beforeEach } from 'vitest';
import { of, firstValueFrom } from 'rxjs';
import { jwtInterceptor } from './jwt.interceptor';
import { AuthService } from '@core/auth/auth.service';

function makeRequest(url: string): HttpRequest<unknown> {
  return new HttpRequest('GET', url);
}

describe('jwtInterceptor', () => {
  function setupWithToken(token: string | null) {
    const accessToken = signal<string | null>(token);
    const mockAuth = { accessToken } as unknown as AuthService;

    TestBed.configureTestingModule({
      providers: [
        provideExperimentalZonelessChangeDetection(),
        { provide: AuthService, useValue: mockAuth },
      ],
    });
  }

  function makeHandler(spy?: (req: HttpRequest<unknown>) => void): HttpHandlerFn {
    return (req) => {
      spy?.(req);
      return of(new HttpResponse({ status: 200 }));
    };
  }

  beforeEach(() => TestBed.resetTestingModule());

  it('adds Authorization: Bearer when token is present', async () => {
    setupWithToken('test-token-abc');
    let capturedReq: HttpRequest<unknown> | null = null;
    const handler = makeHandler(r => { capturedReq = r; });
    const req = makeRequest('https://api.test/api/v1/products');

    await firstValueFrom(TestBed.runInInjectionContext(() => jwtInterceptor(req, handler)));

    expect(capturedReq!.headers.get('Authorization')).toBe('Bearer test-token-abc');
  });

  it('does NOT add Authorization when token is null', async () => {
    setupWithToken(null);
    let capturedReq: HttpRequest<unknown> | null = null;
    const handler = makeHandler(r => { capturedReq = r; });
    const req = makeRequest('https://api.test/api/v1/products');

    await firstValueFrom(TestBed.runInInjectionContext(() => jwtInterceptor(req, handler)));

    expect(capturedReq!.headers.get('Authorization')).toBeNull();
  });

  it.each([
    '/auth/otp/verify',
    '/auth/otp/send',
    '/auth/refresh',
    '/auth/logout',
  ])('skips Authorization for skip-pattern URL: %s', async (url) => {
    setupWithToken('live-token');
    let capturedReq: HttpRequest<unknown> | null = null;
    const handler = makeHandler(r => { capturedReq = r; });
    const req = makeRequest(`https://api.test/api/v1${url}`);

    await firstValueFrom(TestBed.runInInjectionContext(() => jwtInterceptor(req, handler)));

    expect(capturedReq!.headers.get('Authorization')).toBeNull();
  });

  it('does not mutate the original request object', async () => {
    setupWithToken('my-token');
    const req = makeRequest('https://api.test/api/v1/products');
    const handler = makeHandler();

    await firstValueFrom(TestBed.runInInjectionContext(() => jwtInterceptor(req, handler)));

    // Original request should not be mutated
    expect(req.headers.get('Authorization')).toBeNull();
  });
});

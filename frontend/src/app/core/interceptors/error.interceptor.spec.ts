// core/interceptors/error.interceptor.spec.ts
// Covers: ApiError surfacing, 401 route to /login, network error message, 422 re-throw

import { HttpRequest, HttpHandlerFn, HttpErrorResponse, HttpResponse } from '@angular/common/http';
import { signal, provideExperimentalZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { throwError, of, firstValueFrom } from 'rxjs';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { errorInterceptor } from './error.interceptor';
import { ErrorService } from '@core/services/error.service';
import { NetworkService } from '@core/services/network.service';
import { AuthService } from '@core/auth/auth.service';
import { ApiError } from '@core/api/api-error';

function makeHttpError(status: number, body?: unknown): HttpErrorResponse {
  return new HttpErrorResponse({ status, error: body ?? null });
}

describe('errorInterceptor', () => {
  let showErrorSpy: ReturnType<typeof vi.fn>;
  let showWarningSpy: ReturnType<typeof vi.fn>;
  let clearSpy: ReturnType<typeof vi.fn>;
  let navigateSpy: ReturnType<typeof vi.fn>;

  function setup(online = true) {
    showErrorSpy = vi.fn();
    showWarningSpy = vi.fn();
    clearSpy = vi.fn();
    navigateSpy = vi.fn().mockResolvedValue(true);

    TestBed.configureTestingModule({
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideHttpClient(),
        provideRouter([]),
        { provide: ErrorService, useValue: { showError: showErrorSpy, showWarning: showWarningSpy } },
        { provide: NetworkService, useValue: { online: signal(online) } },
        { provide: AuthService, useValue: { clear: clearSpy } },
      ],
    });

    const router = TestBed.inject(Router);
    router.navigate = navigateSpy;
  }

  beforeEach(() => setup());
  afterEach(() => vi.restoreAllMocks());

  it('passes non-HTTP errors through unchanged', async () => {
    const req = new HttpRequest('GET', '/api/v1/products');
    const rawErr = new Error('parse error');
    const handler: HttpHandlerFn = () => throwError(() => rawErr);

    await expect(
      firstValueFrom(TestBed.runInInjectionContext(() => errorInterceptor(req, handler))),
    ).rejects.toThrow('parse error');
  });

  it('does not intercept 200 responses', async () => {
    const req = new HttpRequest('GET', '/api/v1/products');
    const handler: HttpHandlerFn = () => of(new HttpResponse({ status: 200 }));

    const result = await firstValueFrom(TestBed.runInInjectionContext(() => errorInterceptor(req, handler)));
    expect((result as HttpResponse<unknown>).status).toBe(200);
  });

  it('calls auth.clear() and navigates to /login on 401', async () => {
    const req = new HttpRequest('GET', '/api/v1/products');
    const handler: HttpHandlerFn = () => throwError(() => makeHttpError(401));

    try {
      await firstValueFrom(TestBed.runInInjectionContext(() => errorInterceptor(req, handler)));
    } catch {}

    expect(clearSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });

  it('surfaces 422 via ErrorService.showError() and re-throws as ApiError', async () => {
    const req = new HttpRequest('PATCH', '/api/v1/products/123');
    const handler: HttpHandlerFn = () => throwError(() => makeHttpError(422, { detail: 'Invalid MRP' }));

    try {
      await firstValueFrom(TestBed.runInInjectionContext(() => errorInterceptor(req, handler)));
      expect.fail('should have thrown');
    } catch (err) {
      expect(showErrorSpy).toHaveBeenCalledOnce();
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(422);
    }
  });

  it('surfaces 500 via ErrorService.showError() and re-throws', async () => {
    const req = new HttpRequest('GET', '/api/v1/exports/trigger');
    const handler: HttpHandlerFn = () => throwError(() => makeHttpError(500));

    try {
      await firstValueFrom(TestBed.runInInjectionContext(() => errorInterceptor(req, handler)));
      expect.fail('should have thrown');
    } catch (err) {
      expect(showErrorSpy).toHaveBeenCalledOnce();
      expect(err).toBeInstanceOf(ApiError);
    }
  });

  it('shows offline message when network is down', async () => {
    // Re-setup with online=false
    TestBed.resetTestingModule();
    setup(false);

    const req = new HttpRequest('GET', '/api/v1/products');
    const handler: HttpHandlerFn = () => throwError(() => new HttpErrorResponse({ status: 0, error: new ProgressEvent('error') }));

    try {
      await firstValueFrom(TestBed.runInInjectionContext(() => errorInterceptor(req, handler)));
    } catch {}

    expect(showErrorSpy).toHaveBeenCalledOnce();
    const calledWith = (showErrorSpy.mock.calls[0][0] as ApiError).displayMessage;
    expect(calledWith).toContain('offline');
  });
});

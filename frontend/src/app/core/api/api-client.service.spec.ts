// core/api/api-client.service.spec.ts
// Covers: GET/POST/PATCH/DELETE happy path, 401/422/500 error normalisation,
// withCredentials auto-application, retryOn503, postMultipart

import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { describe, expect, it, afterEach, beforeEach, vi } from 'vitest';
import { ApiClient } from './api-client.service';
import { ApiError } from './api-error';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';

const BASE = 'https://api.test/api/v1';

describe('ApiClient', () => {
  let api: ApiClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: BASE },
        ApiClient,
      ],
    });
    api = TestBed.inject(ApiClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    vi.useRealTimers();
  });

  // ── GET ──

  it('GET — calls correct URL with query params', () => {
    let response: { items: number[] } | null = null;
    api.get<{ items: number[] }>('/products', { params: { page: 1, limit: 20 } })
      .subscribe(v => { response = v; });

    const req = httpMock.expectOne(r => r.url === `${BASE}/products`);
    expect(req.request.params.get('page')).toBe('1');
    expect(req.request.params.get('limit')).toBe('20');
    req.flush({ items: [1, 2, 3] });

    expect(response).toEqual({ items: [1, 2, 3] });
  });

  it('GET — normalises 401 HttpErrorResponse to ApiError', () => {
    let err: unknown = null;
    api.get('/products').subscribe({ error: e => { err = e; } });

    httpMock.expectOne(`${BASE}/products`).flush(null, { status: 401, statusText: 'Unauthorized' });

    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(401);
    expect((err as ApiError).displayMessage).toContain('session');
  });

  it('GET — normalises 422 to ApiError preserving detail', () => {
    let err: unknown = null;
    api.get('/products').subscribe({ error: e => { err = e; } });

    httpMock.expectOne(`${BASE}/products`).flush(
      { detail: 'Invalid filter' },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(422);
    expect((err as ApiError).displayMessage).toBe('Invalid filter');
  });

  it('GET — normalises 500 to generic ApiError', () => {
    let err: unknown = null;
    api.get('/products').subscribe({ error: e => { err = e; } });

    httpMock.expectOne(`${BASE}/products`).flush(null, { status: 500, statusText: 'Server Error' });

    expect((err as ApiError).status).toBe(500);
    expect((err as ApiError).displayMessage).toContain('went wrong');
  });

  // ── POST ──

  it('POST — sends body and returns typed response', () => {
    let response: { id: string } | null = null;
    api.post<{ id: string }>('/products', { category_id: 'cat-1' })
      .subscribe(v => { response = v; });

    const req = httpMock.expectOne(`${BASE}/products`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ category_id: 'cat-1' });
    req.flush({ id: 'prod-abc' });

    expect(response).toEqual({ id: 'prod-abc' });
  });

  // ── PATCH ──

  it('PATCH — sends partial update and returns response', () => {
    let response: { updated: boolean } | null = null;
    api.patch<{ updated: boolean }>('/products/123', { name: 'New Name' })
      .subscribe(v => { response = v; });

    const req = httpMock.expectOne(`${BASE}/products/123`);
    expect(req.request.method).toBe('PATCH');
    req.flush({ updated: true });

    expect(response).toEqual({ updated: true });
  });

  // ── DELETE ──

  it('DELETE — calls DELETE HTTP method and completes', () => {
    let completed = false;
    api.delete('/products/123').subscribe({ complete: () => { completed = true; } });

    const req = httpMock.expectOne(`${BASE}/products/123`);
    expect(req.request.method).toBe('DELETE');
    req.flush(null);

    expect(completed).toBe(true);
  });

  // ── withCredentials auto-detection ──

  it('auto-applies withCredentials for /auth/ paths', () => {
    let result: unknown = null;
    api.post('/auth/refresh', null).subscribe(v => { result = v; });

    const req = httpMock.expectOne(`${BASE}/auth/refresh`);
    expect(req.request.withCredentials).toBe(true);
    req.flush({ access_token: 'tok', expires_in: 3600 });

    expect(result).toBeDefined();
  });

  it('does NOT set withCredentials for non-auth paths by default', () => {
    api.get('/products').subscribe({ error: () => {} });

    const req = httpMock.expectOne(`${BASE}/products`);
    expect(req.request.withCredentials).toBe(false);
    req.flush([]);
  });

  // ── postMultipart ──

  it('postMultipart — does not set Content-Type header (browser sets boundary)', () => {
    const fd = new FormData();
    fd.append('file', new Blob(['img']), 'test.jpg');
    api.postMultipart('/images', fd).subscribe({ error: () => {} });

    const req = httpMock.expectOne(`${BASE}/images`);
    expect(req.request.headers.has('Content-Type')).toBe(false);
    req.flush({ url: 'https://gcs.example.com/img.jpg' });
  });

  // ── retryOn503 ──

  it('retryOn503 — first 503 then 200: succeeds after retry', () => {
    vi.useFakeTimers();
    let result: { ok: boolean } | null = null;

    api.get<{ ok: boolean }>('/categories/browse', { retryOn503: true }).subscribe({
      next: v => { result = v; },
    });

    // First attempt: 503
    httpMock.expectOne(`${BASE}/categories/browse`).flush(null, {
      status: 503,
      statusText: 'Service Unavailable',
    });

    // Advance past first backoff delay (1000ms)
    vi.advanceTimersByTime(1100);

    // Second attempt: 200
    httpMock.expectOne(`${BASE}/categories/browse`).flush({ ok: true });

    expect(result).toEqual({ ok: true });
  });
});

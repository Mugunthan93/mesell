/**
 * google-identity.service.spec.ts — GIS loader + wrapper.
 *
 * No real network: we stub document.createElement to capture the injected
 * <script>, and stub window.google.accounts.id to assert delegation.
 */
import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';

import { GoogleIdentityService } from './google-identity.service';

function setup() {
  TestBed.configureTestingModule({ providers: [GoogleIdentityService] });
  return TestBed.inject(GoogleIdentityService);
}

afterEach(() => {
  vi.restoreAllMocks();
  // Clean up any injected window.google + script tags between tests.
  delete (window as unknown as { google?: unknown }).google;
  document.querySelectorAll('script[src*="gsi/client"]').forEach((s) => s.remove());
  TestBed.resetTestingModule();
});

describe('GoogleIdentityService.load()', () => {
  it('resolves immediately if window.google.accounts.id already exists (no script injected)', async () => {
    (window as unknown as { google: unknown }).google = {
      accounts: { id: {} },
    };
    const createSpy = vi.spyOn(document, 'createElement');

    const service = setup();
    await expect(service.load()).resolves.toBeUndefined();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it('injects the GIS script and resolves on load', async () => {
    const service = setup();

    const realCreate = document.createElement.bind(document);
    let injected: HTMLScriptElement | null = null;
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = realCreate(tag) as HTMLElement;
      if (tag === 'script') injected = el as HTMLScriptElement;
      return el as HTMLScriptElement;
    });
    // Stop the real <script> from hitting the network when appended.
    vi.spyOn(document.head, 'appendChild').mockImplementation(
      (n: Node) => n,
    );

    const p = service.load();
    expect(injected).not.toBeNull();
    expect(injected!.src).toContain('https://accounts.google.com/gsi/client');
    // Simulate the browser firing the load event.
    injected!.dispatchEvent(new Event('load'));

    await expect(p).resolves.toBeUndefined();
  });

  it('is idempotent: a second load() reuses the cached promise (one injection)', async () => {
    const service = setup();

    const realCreate = document.createElement.bind(document);
    let injected: HTMLScriptElement | null = null;
    let scriptCreations = 0;
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = realCreate(tag) as HTMLElement;
      if (tag === 'script') { injected = el as HTMLScriptElement; scriptCreations++; }
      return el as HTMLScriptElement;
    });
    vi.spyOn(document.head, 'appendChild').mockImplementation((n: Node) => n);

    const p1 = service.load();
    const p2 = service.load();
    injected!.dispatchEvent(new Event('load'));

    await Promise.all([p1, p2]);
    expect(scriptCreations).toBe(1);
  });

  it('rejects when the script errors', async () => {
    const service = setup();

    const realCreate = document.createElement.bind(document);
    let injected: HTMLScriptElement | null = null;
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = realCreate(tag) as HTMLElement;
      if (tag === 'script') injected = el as HTMLScriptElement;
      return el as HTMLScriptElement;
    });
    vi.spyOn(document.head, 'appendChild').mockImplementation((n: Node) => n);

    const p = service.load();
    injected!.dispatchEvent(new Event('error'));

    await expect(p).rejects.toThrow(/failed to load/i);
  });
});

describe('GoogleIdentityService.initialize() / renderButton() / cancel()', () => {
  function withMockGis() {
    const id = {
      initialize: vi.fn(),
      renderButton: vi.fn(),
      prompt: vi.fn(),
      cancel: vi.fn(),
      disableAutoSelect: vi.fn(),
    };
    (window as unknown as { google: unknown }).google = { accounts: { id } };
    return id;
  }

  it('initialize() delegates to google.accounts.id.initialize with the env client id + a wrapped callback', () => {
    const id = withMockGis();
    const service = setup();
    const cb = vi.fn();

    service.initialize(cb);

    expect(id.initialize).toHaveBeenCalledOnce();
    const arg = id.initialize.mock.calls[0][0];
    expect(typeof arg.client_id).toBe('string');
    expect(arg.client_id.length).toBeGreaterThan(0);
    expect(arg.auto_select).toBe(false);

    // The wrapped callback forwards the response to the consumer callback.
    arg.callback({ credential: 'jwt-x', select_by: 'btn' });
    expect(cb).toHaveBeenCalledWith({ credential: 'jwt-x', select_by: 'btn' });
  });

  it('renderButton() delegates to google.accounts.id.renderButton with the host + options', () => {
    const id = withMockGis();
    const service = setup();
    const host = document.createElement('div');

    service.renderButton(host, { type: 'standard', width: 320 });

    expect(id.renderButton).toHaveBeenCalledWith(host, { type: 'standard', width: 320 });
  });

  it('initialize() throws if GIS is not loaded', () => {
    const service = setup();
    expect(() => service.initialize(vi.fn())).toThrow(/not loaded/i);
  });

  it('cancel() is a safe no-op when GIS is not loaded', () => {
    const service = setup();
    expect(() => service.cancel()).not.toThrow();
  });

  it('cancel() delegates to google.accounts.id.cancel when loaded', () => {
    const id = withMockGis();
    const service = setup();
    service.cancel();
    expect(id.cancel).toHaveBeenCalledOnce();
  });
});


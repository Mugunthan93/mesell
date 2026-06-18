import { Injectable, NgZone, inject } from '@angular/core';

import { environment } from '@mesell/env';

import type {
  GoogleButtonConfiguration,
  GoogleCredentialResponse,
} from '../types/google-gsi';

/** URL of the Google Identity Services client library (runtime browser asset). */
const GSI_SCRIPT_SRC = 'https://accounts.google.com/gsi/client';

/**
 * GoogleIdentityService — lazy loader + thin wrapper around Google Identity
 * Services (GIS), the ID-token sign-in flow.
 *
 * Lives in @mesell/core so it is a FEDERATION SINGLETON: the GIS <script> is
 * injected at most ONCE for the whole app even if the user bounces between the
 * /login and /signup federated routes. It has no PrimeNG/UI dependency, so it
 * belongs in core (not ui-kit).
 *
 * GIS is NOT an npm dependency and does NOT enter the Native-Federation share
 * graph — it is a runtime browser asset fetched from accounts.google.com.
 *
 * Zoneless-safe: this app runs zoneless, and the GIS credential callback fires
 * OUTSIDE Angular's execution context. Callers marshal back via signals; this
 * service additionally re-enters NgZone.run() defensively so any consumer that
 * still relies on zone-driven CD is correct.
 */
@Injectable({ providedIn: 'root' })
export class GoogleIdentityService {
  private readonly zone = inject(NgZone);

  /** In-flight / settled load promise — guards against double-injection. */
  private loadPromise: Promise<void> | null = null;

  /**
   * load() — idempotent lazy injection of the GIS client script.
   *
   * Resolves immediately if GIS is already present (script reused across mounts).
   * Otherwise injects <script async defer> into <head>, resolving on `load`,
   * rejecting on `error` (blocked by proxy/ad-blocker/offline → callers surface
   * the load-error banner and the phone form still works).
   *
   * The promise is cached so concurrent callers (login + signup) share one load.
   */
  load(): Promise<void> {
    // Defensive SSR guard (this app is CSR-only, cheap insurance).
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return Promise.reject(new Error('GIS unavailable: no browser environment'));
    }

    if (this.isReady()) {
      return Promise.resolve();
    }

    if (this.loadPromise) {
      return this.loadPromise;
    }

    this.loadPromise = new Promise<void>((resolve, reject) => {
      // Reuse an existing tag if one was injected by a prior load that is still pending.
      const existing = document.querySelector<HTMLScriptElement>(
        `script[src="${GSI_SCRIPT_SRC}"]`,
      );
      if (existing) {
        existing.addEventListener('load', () => resolve(), { once: true });
        existing.addEventListener(
          'error',
          () => reject(new Error('GIS script failed to load')),
          { once: true },
        );
        return;
      }

      const script = document.createElement('script');
      script.src = GSI_SCRIPT_SRC;
      script.async = true;
      script.defer = true;
      script.addEventListener('load', () => resolve(), { once: true });
      script.addEventListener(
        'error',
        () => {
          // Allow a future retry by clearing the cached (failed) promise.
          this.loadPromise = null;
          reject(new Error('GIS script failed to load'));
        },
        { once: true },
      );
      document.head.appendChild(script);
    });

    return this.loadPromise;
  }

  /** True once `window.google.accounts.id` is available. */
  isReady(): boolean {
    return (
      typeof window !== 'undefined' && !!window.google?.accounts?.id
    );
  }

  /**
   * initialize() — configure GIS with our client id and the credential callback.
   * Idempotent per page mount (safe to call after every load()).
   *
   * The callback is wrapped in NgZone.run() so any zone-dependent reactivity in
   * the consumer is correct even though GIS fires the callback outside the zone.
   */
  initialize(callback: (response: GoogleCredentialResponse) => void): void {
    if (!this.isReady()) {
      throw new Error('GIS not loaded — call load() before initialize()');
    }
    window.google!.accounts.id.initialize({
      client_id: environment.googleOauthClientId,
      callback: (response: GoogleCredentialResponse) =>
        this.zone.run(() => callback(response)),
      auto_select: false,
      use_fedcm_for_prompt: true,
    });
  }

  /**
   * renderButton() — render the official Google button into `el`.
   * `width` (px) is passed so the button matches the auth-card content width.
   */
  renderButton(el: HTMLElement, options: GoogleButtonConfiguration): void {
    if (!this.isReady()) {
      throw new Error('GIS not loaded — call load() before renderButton()');
    }
    window.google!.accounts.id.renderButton(el, options);
  }

  /**
   * cancel() — dismiss any pending One-Tap prompt. Safe no-op if GIS isn't ready.
   * Called from a consumer's ngOnDestroy for cleanup. We deliberately do NOT
   * call disableAutoSelect() here (it would wipe the user's auto-select
   * preference); that is reserved for explicit logout if One-Tap is enabled.
   */
  cancel(): void {
    if (this.isReady()) {
      window.google!.accounts.id.cancel();
    }
  }
}


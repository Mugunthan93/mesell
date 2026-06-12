import { Injectable, signal, OnDestroy } from '@angular/core';

/**
 * NetworkService — online/offline state.
 *
 * Surfaces window.navigator.onLine as a reactive signal. Components and services
 * gate their network calls behind this signal to surface a meaningful "offline"
 * state instead of a confusing 0-status HTTP error.
 *
 * Event listeners are cleaned up on service destruction (injection context destroy,
 * i.e. app teardown). CSR-only — this is a V1 PWA; no SSR context.
 */
@Injectable({ providedIn: 'root' })
export class NetworkService implements OnDestroy {
  private readonly _online = signal<boolean>(
    typeof navigator !== 'undefined' ? navigator.onLine : true,
  );

  /** Reactive online status. True = connected, False = offline. */
  readonly online = this._online.asReadonly();

  private readonly onlineHandler  = (): void => this._online.set(true);
  private readonly offlineHandler = (): void => this._online.set(false);

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online',  this.onlineHandler);
      window.addEventListener('offline', this.offlineHandler);
    }
  }

  ngOnDestroy(): void {
    if (typeof window !== 'undefined') {
      window.removeEventListener('online',  this.onlineHandler);
      window.removeEventListener('offline', this.offlineHandler);
    }
  }
}

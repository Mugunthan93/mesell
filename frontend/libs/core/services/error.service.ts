import { Injectable, signal } from '@angular/core';
import type { ApiErrorEnvelope } from '../interceptors/error.interceptor';

/**
 * ErrorService — global error state.
 *
 * Written to by errorInterceptor; read by the shell or any component that
 * needs to surface a global error affordance (toast, banner, etc.).
 * Does NOT show UI itself — the UI layer decides the presentation.
 *
 * Uses a signal for reactivity. clear() is idempotent.
 */
@Injectable({ providedIn: 'root' })
export class ErrorService {
  private readonly _lastError = signal<ApiErrorEnvelope | null>(null);

  /** Reactive read: the last error envelope recorded, or null. */
  readonly lastError = this._lastError.asReadonly();

  /** Called by errorInterceptor. Sets the last error (non-blocking). */
  record(envelope: ApiErrorEnvelope): void {
    this._lastError.set(envelope);
  }

  /** Called by the shell/component to dismiss the error surface. */
  clear(): void {
    this._lastError.set(null);
  }
}

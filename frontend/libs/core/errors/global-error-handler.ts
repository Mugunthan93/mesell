import { ErrorHandler, Injectable, isDevMode } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ErrorService } from '../services/error.service';
import type { ApiErrorEnvelope } from '../interceptors/error.interceptor';

/**
 * GlobalErrorHandler — catches uncaught JS errors (zone.js window.onerror path)
 * and normalises them into the typed ApiErrorEnvelope for ErrorService.
 *
 * Wired via: { provide: ErrorHandler, useClass: GlobalErrorHandler }
 *
 * HTTP errors that already went through errorInterceptor will arrive here
 * as HttpErrorResponse — we normalise them the same way so ErrorService always
 * holds a fully typed envelope regardless of error origin.
 *
 * Dev mode: logs to console.error for debugging (stripped in prod builds by
 * isDevMode() tree-shaking at the call site).
 */
@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  constructor(private readonly errorService: ErrorService) {}

  handleError(error: unknown): void {
    if (isDevMode()) console.error('[GlobalErrorHandler]', error);

    let envelope: ApiErrorEnvelope;
    if (error instanceof HttpErrorResponse) {
      const body = error.error as Partial<ApiErrorEnvelope> | null | undefined;
      envelope = {
        detail: body?.detail ?? error.message ?? 'HTTP error',
        code: body?.code ?? 'HTTP_ERROR',
        validation_message_id: body?.validation_message_id ?? '',
        request_id: body?.request_id ?? '',
      };
    } else if (error instanceof Error) {
      envelope = {
        detail: error.message || 'Unknown client error',
        code: 'CLIENT_ERROR',
        validation_message_id: '',
        request_id: '',
      };
    } else {
      envelope = {
        detail: String(error) || 'Unknown error',
        code: 'CLIENT_ERROR',
        validation_message_id: '',
        request_id: '',
      };
    }
    this.errorService.record(envelope);
  }
}

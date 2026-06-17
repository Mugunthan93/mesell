import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ErrorService } from '../services/error.service';

/**
 * errorInterceptor — typed error envelope recorder.
 *
 * Position: LAST in chain (jwt → refresh → error).
 * It only sees errors that refresh interceptor did NOT already resolve.
 * Does NOT handle 401 — that is refresh's responsibility.
 *
 * Behaviour:
 * 1. Extracts the 4-field typed envelope per backend/app/core/errors.py L125-138.
 * 2. Pushes to ErrorService (non-blocking — shell/component reads it for global surface).
 * 3. Re-throws so callers' own catchError matrices still run.
 *
 * 422 adds an errors[] array (errors.py L163) — typed as errors?: unknown[].
 */

/** Typed error envelope — mirrors backend/app/core/errors.py L125-138 */
export interface ApiErrorEnvelope {
  detail: string;
  code: string;
  validation_message_id: string;
  request_id: string;
  /** Present on 422 validation failures (errors.py L163) */
  errors?: unknown[];
}

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const errorService = inject(ErrorService);

  return next(req).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse) {
        const body = err.error as Partial<ApiErrorEnvelope> | null | undefined;
        const envelope: ApiErrorEnvelope = {
          detail: body?.detail ?? err.message ?? 'Unexpected error',
          code: body?.code ?? 'UNKNOWN',
          validation_message_id: body?.validation_message_id ?? '',
          request_id: body?.request_id ?? '',
          ...(body?.errors !== undefined ? { errors: body.errors } : {}),
        };
        errorService.record(envelope);
      }
      return throwError(() => err);
    }),
  );
};

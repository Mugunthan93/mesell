// core/api/api-error.ts
// ApiError class + normaliser per §4.E.4

import { HttpErrorResponse } from '@angular/common/http';

export class ApiError extends Error {
  readonly kind: 'http' | 'network' | 'parse';
  readonly status: number;          // 0 for network, else HTTP status
  readonly code: string | null;     // backend's machine-readable code (e.g., 'rate_limit_exceeded')
  readonly displayMessage: string;  // locale-resolved user-facing message
  readonly traceId: string | null;  // backend's request-id header (for support escalation)
  readonly raw: HttpErrorResponse | null;

  constructor(params: {
    kind: 'http' | 'network' | 'parse';
    status: number;
    code?: string | null;
    displayMessage: string;
    traceId?: string | null;
    raw?: HttpErrorResponse | null;
    message?: string;
  }) {
    super(params.message ?? params.displayMessage);
    this.kind = params.kind;
    this.status = params.status;
    this.code = params.code ?? null;
    this.displayMessage = params.displayMessage;
    this.traceId = params.traceId ?? null;
    this.raw = params.raw ?? null;
    this.name = 'ApiError';
  }
}

/** Normalise an HttpErrorResponse into an ApiError. */
export function normaliseHttpError(err: HttpErrorResponse): ApiError {
  if (err.error instanceof ProgressEvent || err.status === 0) {
    // Network-level error — no response received
    return new ApiError({
      kind: 'network',
      status: 0,
      displayMessage: 'Cannot reach the server. Please check your connection.',
      traceId: null,
      raw: err,
    });
  }

  const body = err.error as Record<string, unknown> | null;
  const detail = typeof body?.['detail'] === 'string' ? body['detail'] : null;
  const code = typeof body?.['code'] === 'string' ? body['code'] : null;
  const traceId = err.headers?.get('x-request-id') ?? null;

  let displayMessage: string;
  switch (err.status) {
    case 400:
      displayMessage = detail ?? 'Invalid request. Please check your input.';
      break;
    case 401:
      displayMessage = 'Your session has expired. Please log in again.';
      break;
    case 403:
      displayMessage = 'You do not have permission to perform this action.';
      break;
    case 404:
      displayMessage = detail ?? 'The requested resource was not found.';
      break;
    case 422:
      displayMessage = detail ?? 'Validation failed. Please check your input.';
      break;
    case 429:
      displayMessage = detail ?? 'Too many requests. Please wait before trying again.';
      break;
    case 503:
      displayMessage = 'Service temporarily unavailable. Please try again shortly.';
      break;
    default:
      if (err.status >= 500) {
        displayMessage = 'Something went wrong on our side. Our team has been notified.';
      } else {
        displayMessage = detail ?? `Unexpected error (${err.status}).`;
      }
  }

  return new ApiError({
    kind: 'http',
    status: err.status,
    code,
    displayMessage,
    traceId,
    raw: err,
  });
}

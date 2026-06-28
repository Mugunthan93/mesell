import { HttpInterceptorFn } from '@angular/common/http';
import { retry, timer } from 'rxjs';

/**
 * retryInterceptor — exponential-backoff retry for transient failures.
 *
 * Position: SECOND in chain (jwt → retry → refresh → error).
 * Wraps the downstream (refresh + error interceptors + backend) so retries
 * re-enter the full inner chain — a 401 on retry still triggers refreshInterceptor.
 *
 * Retry conditions:
 *   - status === 0  (network failure / CORS block) — any HTTP method
 *   - status >= 500 AND method is idempotent (GET, HEAD, OPTIONS, PUT)
 *
 * Non-retriable:
 *   - 4xx (client errors — no retry will fix them)
 *   - 401 (handled by refreshInterceptor)
 *   - POST / PATCH / DELETE 5xx (non-idempotent — retrying may cause duplicate side effects)
 *
 * Backoff schedule: 1 s, 2 s, 4 s (max 3 attempts after the initial failure).
 */

const IDEMPOTENT = new Set(['GET', 'HEAD', 'OPTIONS', 'PUT']);

export const retryInterceptor: HttpInterceptorFn = (req, next) =>
  next(req).pipe(
    retry({
      count: 3,
      delay: (error, retryCount) => {
        const networkFail = error?.status === 0;
        const serverErr = error?.status >= 500 && IDEMPOTENT.has(req.method);
        if (!networkFail && !serverErr) throw error;
        return timer(Math.pow(2, retryCount - 1) * 1000); // 1 s, 2 s, 4 s
      },
      resetOnSuccess: true,
    }),
  );

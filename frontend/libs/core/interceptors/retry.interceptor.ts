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
 * Backoff schedule: 1 s, 2 s, 4 s (max 3 attempts after the initial failure — a HARD cap).
 *
 * IMPORTANT — do NOT add `resetOnSuccess: true` here. HttpClient's request stream emits an
 * `HttpEventType.Sent` `next` value through the interceptor chain on every attempt, BEFORE the
 * eventual response/error. RxJS's `retry({ resetOnSuccess: true })` treats that `next` as a
 * "success" and resets the internal retry counter to 0 on every attempt — including the
 * attempts that go on to error. That reset happens before the counter is ever checked/incremented
 * against `count`, so the cap never trips: every sustained failure (status 0 / 5xx-idempotent)
 * retries forever at a constant ~1 s cadence instead of stopping after 3 retries. A single
 * HttpClient request is a single-shot stream (it errors or completes once) — `resetOnSuccess`
 * has no legitimate use case here and only reintroduces this hazard. Keep it off (the default).
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
    }),
  );

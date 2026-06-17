"""Prometheus metrics registry — svc-pricing SUBSET.

Vendored from the monolith ``app.core.metrics`` (§15.J) but trimmed to the
metrics svc-pricing actually emits:

* ``http_request_duration_seconds`` + ``http_requests_total`` — observed by
  the vendored ``auth_mw`` post-response (the only call site present here).

The Celery / AI / auth-refresh metrics from the monolith are NOT vendored —
pricing runs no worker, emits no AI, issues no tokens.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# ── HTTP request latency ────────────────────────────────────────────────────
# Call site: ``app.core.middleware.auth_mw.AuthContextMiddleware`` post-response.
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["endpoint", "method", "status_code"],
)

# ── HTTP request count ──────────────────────────────────────────────────────
# Call site: ``app.core.middleware.auth_mw.AuthContextMiddleware`` post-response.
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled.",
    ["endpoint", "method", "status_code"],
)


__all__ = [
    "HTTP_REQUEST_DURATION",
    "HTTP_REQUESTS_TOTAL",
]

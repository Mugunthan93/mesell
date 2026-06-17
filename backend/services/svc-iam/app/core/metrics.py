"""Prometheus metrics registry — svc-iam SUBSET.

Vendored from the monolith ``app.core.metrics`` (§15.J) but trimmed to the
metrics svc-iam actually emits:

* ``http_request_duration_seconds`` + ``http_requests_total`` — observed by
  the vendored ``auth_mw`` post-response.
* ``auth_token_refresh_failed_total`` — incremented by ``service.py``
  (auth-builder's file) on each refresh-rotation failure, labelled by cause
  (``cookie_missing`` | ``allowlist_miss`` | ``expired`` | ``replay``).  iam
  is the ONLY service that owns the issuance / rotation half of
  ``core/auth.py`` from a route, so it is the only service that vendors this
  counter (§7.B.3).

The Celery / AI metrics from the monolith are NOT vendored — iam runs no
worker and emits no AI cost.
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

# ── Refresh-token rotation failures ─────────────────────────────────────────
# Call site: ``app.service.rotate_refresh_token`` (auth-builder's file) — each
# ``auth.token.refresh_failed`` audit path increments with the mapped reason.
AUTH_TOKEN_REFRESH_FAILED = Counter(
    "auth_token_refresh_failed_total",
    "Refresh-token rotation failures by cause (§7.B.3).",
    ["reason"],  # "cookie_missing" | "allowlist_miss" | "expired" | "replay"
)


__all__ = [
    "HTTP_REQUEST_DURATION",
    "HTTP_REQUESTS_TOTAL",
    "AUTH_TOKEN_REFRESH_FAILED",
]

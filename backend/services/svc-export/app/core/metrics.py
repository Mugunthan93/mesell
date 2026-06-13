"""Prometheus metrics registry — svc-export SUBSET.

Vendored from the monolith ``app.core.metrics`` (§15.J) but trimmed to the
metrics svc-export actually emits:

* ``http_request_duration_seconds`` + ``http_requests_total`` — observed by
  the vendored ``auth_mw`` post-response (the only call site present here).
* ``celery_queue_depth`` — DEFINED but UNSET in V1 (no in-process monitor);
  kept so the ``/metrics`` scrape exposes the export queue series shape.

The 4 AI / auth-refresh metrics from the monolith are NOT vendored — export
emits none of them (no AI, no token issuance).
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

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

# ── Celery queue depth ──────────────────────────────────────────────────────
# Gauge reflecting the svc-export Celery broker backlog.  DEFINED but UNSET in
# V1 — a separate Celery monitor wires ``.labels(queue="svc-export").set(n)``.
CELERY_QUEUE_DEPTH = Gauge(
    "celery_queue_depth",
    "Celery broker backlog depth per queue (UNSET in V1).",
    ["queue"],
)


__all__ = [
    "CELERY_QUEUE_DEPTH",
    "HTTP_REQUEST_DURATION",
    "HTTP_REQUESTS_TOTAL",
]

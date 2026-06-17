"""Prometheus metrics registry — svc-image SUBSET.

Vendored from the monolith ``app.core.metrics`` (§15.J) but trimmed to the
metrics svc-image actually emits:

* ``http_request_duration_seconds`` + ``http_requests_total`` — observed by
  the vendored ``auth_mw`` post-response (the only HTTP call site present).
* ``celery_queue_depth`` — DEFINED but UNSET in V1 (no in-process monitor);
  kept so the ``/metrics`` scrape exposes the svc-image queue series shape.
* ``ai_ops_budget_alarm_total`` — Counter, emitted by the VENDORED
  ``app.ai_ops.budget_cap.check_and_reserve`` (watermark.v1 step) on the
  80%/100% bands (§6A.F).
* ``ai_ops_cost_inr`` — Gauge, SET by the VENDORED
  ``app.ai_ops.cost_tracker.record`` per watermark call (§6A.D).

The auth-refresh + i18n-missing metrics from the monolith are NOT vendored —
svc-image issues no tokens and its resolver only logs the verbatim-ID miss.
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
# Gauge reflecting the svc-image Celery broker backlog.  DEFINED but UNSET in
# V1 — a separate Celery monitor wires ``.labels(queue="svc-image").set(n)``.
CELERY_QUEUE_DEPTH = Gauge(
    "celery_queue_depth",
    "Celery broker backlog depth per queue (UNSET in V1).",
    ["queue"],
)

# ── AI ops budget alarm ─────────────────────────────────────────────────────
# Call site: VENDORED ``app.ai_ops.budget_cap.check_and_reserve`` —
# ``.labels(level="80")`` on the 80%–100% warning band; ``.labels(level="100")``
# on the hard-stop (100%+).  The budget keyspace is SHARED (un-prefixed, DB 0)
# across all services per §0.5 / D6 — the global ₹500 cap is process-agnostic.
AI_OPS_BUDGET_ALARM = Counter(
    "ai_ops_budget_alarm_total",
    "AI ops daily-budget alarm band crossings (§6A.F).",
    ["level"],  # "80" | "100"
)

# ── AI ops daily cost (INR) ─────────────────────────────────────────────────
# Call site: VENDORED ``app.ai_ops.cost_tracker.record`` — ``.labels(
# workload="watermark", period="daily").set(daily_total_inr)``.  SET (not inc).
AI_OPS_COST_INR = Gauge(
    "ai_ops_cost_inr",
    "Current daily AI cost in INR per workload (§6A.D).",
    ["workload", "period"],  # workload="watermark", period="daily"
)


__all__ = [
    "AI_OPS_BUDGET_ALARM",
    "AI_OPS_COST_INR",
    "CELERY_QUEUE_DEPTH",
    "HTTP_REQUEST_DURATION",
    "HTTP_REQUESTS_TOTAL",
]

"""Prometheus metrics registry — §15.J locked "Key V1 metrics" (F-15-2).

Defines all 7 §15.J metrics as module-level singletons against the
default ``prometheus_client`` registry.  The ``/metrics`` ASGI app is
mounted LAST in :mod:`app.main` (after every router) via
:func:`prometheus_client.make_asgi_app`; that scrape endpoint traverses
the fail-open :class:`app.core.middleware.auth_mw.AuthContextMiddleware`
without a 401 short-circuit (see that module's docstring, which has
anticipated the ``/metrics`` scrape since 2026-06-05).

The 7 metrics (names + labels are LOCKED — do not rename):

1. ``ai_ops_budget_alarm_total{level}``       — Counter (§6A.F bands "80"/"100")
2. ``i18n_resolver_missing_key{message_id}``   — Counter (resolver miss tier)
3. ``http_request_duration_seconds{endpoint,method,status_code}`` — Histogram
4. ``http_requests_total{endpoint,method,status_code}``           — Counter
5. ``celery_queue_depth{queue}``               — Gauge (backlog depth)
6. ``ai_ops_cost_inr{workload,period}``        — Gauge (current daily total)
7. ``auth_token_refresh_failed_total{reason}`` — Counter (refresh-failure cause)

Each metric is incremented / observed / set at exactly one call site
(documented per-metric below).  This module owns ONLY the definitions;
the call sites live in their respective domain modules.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── 1. AI ops budget alarm ──────────────────────────────────────────────────
# Call site: ``app.ai_ops.budget_cap.check_and_reserve`` — ``.labels(level="80")``
# on entering the 80%–100% warning band; ``.labels(level="100")`` when the
# reservation is rejected at the hard-stop (100%+) cap.
AI_OPS_BUDGET_ALARM = Counter(
    "ai_ops_budget_alarm_total",
    "AI ops daily-budget alarm band crossings (§6A.F).",
    ["level"],  # "80" | "100"
)

# ── 2. i18n resolver missing key ────────────────────────────────────────────
# Call site: ``app.i18n.resolver.resolve`` — verbatim-ID (Step 3) miss tier.
#
# NOTE (F-15-2 D-flag): §15.J locks the metric NAME as
# ``i18n_resolver_missing_key`` (NO ``_total`` suffix).  ``prometheus_client``
# FORCES a ``_total`` suffix on any ``Counter`` whose name does not already
# end in ``_total`` — a ``Counter("i18n_resolver_missing_key", ...)`` would
# scrape as ``i18n_resolver_missing_key_total``, breaking the locked name.
# To honour the exact locked series name while preserving monotonic-increment
# semantics, this is implemented as a ``Gauge`` that the call site only ever
# ``.inc()``s.  A Gauge renders WITHOUT the forced ``_total`` suffix, so the
# scrape emits ``i18n_resolver_missing_key{message_id=...}`` verbatim.
I18N_MISSING_KEY = Gauge(
    "i18n_resolver_missing_key",
    "i18n resolver fell through to the verbatim-ID tier (§5A.I).",
    ["message_id"],
)

# ── 3. HTTP request latency ─────────────────────────────────────────────────
# Call site: ``app.core.middleware.auth_mw.AuthContextMiddleware`` post-response.
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["endpoint", "method", "status_code"],
)

# ── 4. HTTP request count ───────────────────────────────────────────────────
# Call site: ``app.core.middleware.auth_mw.AuthContextMiddleware`` post-response.
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled.",
    ["endpoint", "method", "status_code"],
)

# ── 5. Celery queue depth ───────────────────────────────────────────────────
# Gauge reflecting the Celery broker backlog per queue.  Setting this requires
# a Celery ``inspect`` round-trip, which MUST NOT run inside a hot request
# path.  V1 leaves this Gauge DEFINED but UNSET — it reports 0 until a separate
# Celery monitor (a 30s beat task or sidecar) wires ``.labels(queue=q).set(n)``.
# TODO(V1.5): add a periodic Celery monitor that calls
#   ``celery_app.control.inspect().reserved()`` / ``.active()`` every ~30s and
#   sets CELERY_QUEUE_DEPTH per queue.  Acceptable per F-15-2 dispatch to ship
#   the metric at 0 until that monitor lands.
CELERY_QUEUE_DEPTH = Gauge(
    "celery_queue_depth",
    "Celery broker backlog depth per queue (UNSET in V1 — see module TODO).",
    ["queue"],
)

# ── 6. AI ops daily cost (INR) ──────────────────────────────────────────────
# Call site: ``app.ai_ops.cost_tracker.record`` — ``.labels(workload=w,
# period="daily").set(daily_total_inr)``.  SET (not inc) — it is the current
# running daily total for that workload.
AI_OPS_COST_INR = Gauge(
    "ai_ops_cost_inr",
    "Current daily AI cost in INR per workload (§6A.D).",
    ["workload", "period"],  # workload="smart_picker"|"autofill"|"watermark", period="daily"
)

# ── 7. Auth token refresh failures ──────────────────────────────────────────
# Call site: ``app.modules.iam.service.rotate_refresh_token`` — each
# ``auth.token.refresh_failed`` audit path increments with the mapped reason.
AUTH_TOKEN_REFRESH_FAILED = Counter(
    "auth_token_refresh_failed_total",
    "Refresh-token rotation failures by cause (§7.B.3).",
    ["reason"],  # "cookie_missing" | "allowlist_miss" | "expired" | "replay"
)


__all__ = [
    "AI_OPS_BUDGET_ALARM",
    "AI_OPS_COST_INR",
    "AUTH_TOKEN_REFRESH_FAILED",
    "CELERY_QUEUE_DEPTH",
    "HTTP_REQUEST_DURATION",
    "HTTP_REQUESTS_TOTAL",
    "I18N_MISSING_KEY",
]

"""Unit tests for §15.J Prometheus metrics (F-15-2).

Asserts the 7 locked metric names + labels exist, are the correct
``prometheus_client`` types, and render through the default registry
scrape with the exact label values their call sites emit.
"""

from __future__ import annotations

import pytest
from prometheus_client import Counter, Gauge, Histogram, generate_latest

from app.core import metrics


# ── 1. All 7 importable + correct types ─────────────────────────────────────
@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("AI_OPS_BUDGET_ALARM", Counter),
        # §15.J locks the NAME ``i18n_resolver_missing_key`` (no ``_total``);
        # implemented as a Gauge so prometheus_client does not force a
        # ``_total`` suffix that would break the locked series name.
        ("I18N_MISSING_KEY", Gauge),
        ("HTTP_REQUEST_DURATION", Histogram),
        ("HTTP_REQUESTS_TOTAL", Counter),
        ("CELERY_QUEUE_DEPTH", Gauge),
        ("AI_OPS_COST_INR", Gauge),
        ("AUTH_TOKEN_REFRESH_FAILED", Counter),
    ],
)
def test_metric_defined_with_expected_type(name: str, kind: type) -> None:
    metric = getattr(metrics, name)
    assert isinstance(metric, kind)


def test_all_seven_exported() -> None:
    assert set(metrics.__all__) == {
        "AI_OPS_BUDGET_ALARM",
        "AI_OPS_COST_INR",
        "AUTH_TOKEN_REFRESH_FAILED",
        "CELERY_QUEUE_DEPTH",
        "HTTP_REQUEST_DURATION",
        "HTTP_REQUESTS_TOTAL",
        "I18N_MISSING_KEY",
    }


# ── 2. Locked metric NAMES (the scrape-facing contract) ─────────────────────
def test_locked_metric_names_present_in_scrape() -> None:
    # Touch each metric so a sample exists in the registry.
    metrics.AI_OPS_BUDGET_ALARM.labels(level="80").inc()
    metrics.I18N_MISSING_KEY.labels(message_id="x.y.z").inc()
    metrics.HTTP_REQUEST_DURATION.labels(
        endpoint="/t", method="GET", status_code="200"
    ).observe(0.01)
    metrics.HTTP_REQUESTS_TOTAL.labels(
        endpoint="/t", method="GET", status_code="200"
    ).inc()
    metrics.CELERY_QUEUE_DEPTH.labels(queue="image").set(0)
    metrics.AI_OPS_COST_INR.labels(workload="autofill", period="daily").set(0.0)
    metrics.AUTH_TOKEN_REFRESH_FAILED.labels(reason="expired").inc()

    out = generate_latest().decode()
    for family in (
        "ai_ops_budget_alarm_total",
        "i18n_resolver_missing_key",
        "http_request_duration_seconds",
        "http_requests_total",
        "celery_queue_depth",
        "ai_ops_cost_inr",
        "auth_token_refresh_failed_total",
    ):
        assert family in out, f"{family} missing from /metrics scrape"


# ── 3. Locked LABEL values per call-site spec ───────────────────────────────
@pytest.mark.parametrize("level", ["80", "100"])
def test_budget_alarm_levels(level: str) -> None:
    metrics.AI_OPS_BUDGET_ALARM.labels(level=level).inc()
    out = generate_latest().decode()
    assert f'ai_ops_budget_alarm_total{{level="{level}"}}' in out


@pytest.mark.parametrize(
    "reason", ["cookie_missing", "allowlist_miss", "expired", "replay"]
)
def test_refresh_failed_reasons(reason: str) -> None:
    metrics.AUTH_TOKEN_REFRESH_FAILED.labels(reason=reason).inc()
    out = generate_latest().decode()
    assert f'auth_token_refresh_failed_total{{reason="{reason}"}}' in out


@pytest.mark.parametrize("workload", ["smart_picker", "autofill", "watermark"])
def test_ai_cost_workloads_daily(workload: str) -> None:
    metrics.AI_OPS_COST_INR.labels(workload=workload, period="daily").set(1.5)
    out = generate_latest().decode()
    assert f'workload="{workload}"' in out
    assert 'period="daily"' in out


# ── 4. Call-site integration: resolver miss bumps I18N_MISSING_KEY ──────────
def test_resolver_miss_increments_metric() -> None:
    from app.i18n.resolver import resolve

    before = generate_latest().decode()
    miss_id = "totally.unregistered.key"
    assert (
        f'i18n_resolver_missing_key{{message_id="{miss_id}"}}' not in before
    )
    result = resolve(miss_id)
    assert result == miss_id  # verbatim fallback tier
    after = generate_latest().decode()
    # Locked §15.J name has NO ``_total`` suffix (Gauge, not Counter).
    assert f'i18n_resolver_missing_key{{message_id="{miss_id}"}} 1.0' in after
    assert "i18n_resolver_missing_key_total" not in after

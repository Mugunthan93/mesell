"""§18.E — Celery broker URL MUST resolve to Valkey **DB 1**.

Per BACKEND_ARCHITECTURE.md §18.E + CLAUDE.md Valkey DB mapping:

* DB 0 — sessions, OTP, rate limits (NOT used by Celery)
* **DB 1 — Celery broker** (this test)
* DB 2 — Celery result backend
* DB 3 — application read-through cache

The URL is derived from ``settings.VALKEY_URL`` via
``workers.celery_app._build_url_for_db(..., 1)`` — the path component
is rewritten regardless of the inbound URL's DB suffix.
"""

from __future__ import annotations

from urllib.parse import urlparse


def test_broker_url_path_is_db_1():
    """``broker_url`` path MUST equal ``/1`` regardless of input URL."""
    from app.workers.celery_app import celery_app

    parsed = urlparse(celery_app.conf.broker_url)
    assert parsed.path == "/1", (
        f"Celery broker MUST live on Valkey DB 1 per §18.E + CLAUDE.md; "
        f"got URL {celery_app.conf.broker_url} (path={parsed.path})"
    )


def test_broker_url_endswith_slash_1():
    """String-form invariant — broker URL ends with ``/1`` for ops eyeball."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.broker_url.endswith("/1"), (
        f"broker_url MUST end with '/1' for ops readability; "
        f"got {celery_app.conf.broker_url}"
    )


def test_broker_url_is_redis_scheme():
    """Scheme MUST be redis:// (Valkey is wire-protocol-compatible)."""
    from app.workers.celery_app import celery_app

    parsed = urlparse(celery_app.conf.broker_url)
    assert parsed.scheme in ("redis", "rediss"), (
        f"broker_url scheme MUST be redis or rediss; got {parsed.scheme}"
    )


def test_broker_db_matches_shared_valkey_helper():
    """The local ``_build_url_for_db`` MUST behave identically to
    ``shared.valkey._build_url_for_db`` — §18.E enforces a single DB
    allocation discipline across both helpers."""
    from app.shared.valkey import _build_url_for_db as shared_helper
    from app.workers.celery_app import _build_url_for_db as workers_helper

    candidates = [
        "redis://localhost:6379/0",
        "redis://localhost:6380/15",
        "redis://valkey:6379",            # no DB suffix
        "redis://user:pwd@valkey:6379/3", # auth + DB
    ]
    for base in candidates:
        assert workers_helper(base, 1) == shared_helper(base, 1), (
            f"helpers diverge for base={base!r} → workers={workers_helper(base, 1)!r} "
            f"shared={shared_helper(base, 1)!r}"
        )

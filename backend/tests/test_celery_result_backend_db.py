"""§18.E — Celery result backend URL MUST resolve to Valkey **DB 2**.

Per BACKEND_ARCHITECTURE.md §18.E, the result backend lives on a
separate Valkey DB from the broker so a broker queue-purge does NOT
also wipe outstanding task results — and so an operator's `redis-cli`
session against DB 1 can ZRANGE the broker queue without polluting
result-backend keyspace.
"""

from __future__ import annotations

from urllib.parse import urlparse


def test_result_backend_path_is_db_2():
    """``result_backend`` path MUST equal ``/2`` regardless of input URL."""
    from app.workers.celery_app import celery_app

    parsed = urlparse(celery_app.conf.result_backend)
    assert parsed.path == "/2", (
        f"Celery result backend MUST live on Valkey DB 2 per §18.E + CLAUDE.md; "
        f"got URL {celery_app.conf.result_backend} (path={parsed.path})"
    )


def test_result_backend_endswith_slash_2():
    """String-form invariant — result backend URL ends with ``/2``."""
    from app.workers.celery_app import celery_app

    assert celery_app.conf.result_backend.endswith("/2"), (
        f"result_backend MUST end with '/2' for ops readability; "
        f"got {celery_app.conf.result_backend}"
    )


def test_result_backend_is_redis_scheme():
    """Scheme MUST be redis:// (Valkey is wire-protocol-compatible)."""
    from app.workers.celery_app import celery_app

    parsed = urlparse(celery_app.conf.result_backend)
    assert parsed.scheme in ("redis", "rediss"), (
        f"result_backend scheme MUST be redis or rediss; got {parsed.scheme}"
    )


def test_broker_and_result_backend_share_host_diff_db():
    """Broker + result backend MUST share host:port but differ on DB —
    structural assert that the §18.E + §5.C DB-allocation discipline
    is honoured (single Valkey instance, distinct DBs)."""
    from app.workers.celery_app import celery_app

    b = urlparse(celery_app.conf.broker_url)
    r = urlparse(celery_app.conf.result_backend)
    assert (b.hostname, b.port) == (r.hostname, r.port), (
        f"broker host:port ({b.hostname}:{b.port}) MUST equal "
        f"result_backend host:port ({r.hostname}:{r.port}) — single Valkey instance"
    )
    assert b.path != r.path, (
        f"broker DB ({b.path}) MUST differ from result_backend DB ({r.path})"
    )
    assert b.path == "/1" and r.path == "/2", (
        f"broker MUST be /1 and result_backend MUST be /2 per §18.E; "
        f"got broker={b.path} result_backend={r.path}"
    )

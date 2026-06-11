"""Unit tests for ``app.adapters.langfuse`` (§6.F + §6.G).

Verifies the LOCKED CONTRACT (§6.F):
  * ``trace`` and ``score`` NEVER raise — drop-on-failure with WARNING.
  * Missing credentials at startup → no-op with single one-time WARNING.
  * Returns ``None`` unconditionally.
"""

from __future__ import annotations

import inspect
import logging
import uuid

import httpx
import pytest

from app.adapters import LangfuseAdapterError
from app.adapters import langfuse as langfuse_mod
from app.core.errors import MeesellError

pytestmark = pytest.mark.unit


# ── Fixtures ───────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _reset_module():
    langfuse_mod._reset_for_testing()
    yield
    langfuse_mod._reset_for_testing()


def _install_mock_client(handler) -> None:
    transport = httpx.MockTransport(handler)
    # Use the real base_url + auth header — we're not testing those here,
    # so an empty stub is fine.  The MockTransport intercepts all egress.
    langfuse_mod._client = httpx.AsyncClient(
        transport=transport,
        base_url="https://stub.local",
        timeout=2.0,
        headers={"Authorization": "Basic stub", "Content-Type": "application/json"},
    )


# ── Exception hierarchy ────────────────────────────────────────────────────
def test_langfuse_adapter_error_defined_for_v15():
    """Class defined for V1.5 surface; V1 code paths NEVER raise it."""
    assert issubclass(LangfuseAdapterError, MeesellError)
    assert LangfuseAdapterError().status_code == 502


# ── Happy path egress ─────────────────────────────────────────────────────
async def test_trace_emits_to_ingestion_endpoint():
    """trace POSTs to /api/public/ingestion with type=trace-create."""
    seen: list[dict] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            {
                "path": request.url.path,
                "method": request.method,
                "body": request.read(),
            }
        )
        return httpx.Response(207)  # LangFuse uses 207 Multi-Status for batch

    _install_mock_client(_handler)
    result = await langfuse_mod.trace(
        name="smart_picker.suggest",
        input={"prompt": "describe"},
        output={"text": "hello", "tokens": 5},
        metadata={"workload": "smart_picker"},
        trace_id="trace-fixed-id",
    )

    assert result is None  # NEVER returns a value
    assert len(seen) == 1
    assert seen[0]["path"] == "/api/public/ingestion"
    assert seen[0]["method"] == "POST"
    body = seen[0]["body"].decode("utf-8")
    assert "trace-create" in body
    assert "smart_picker.suggest" in body
    assert "trace-fixed-id" in body


async def test_score_emits_score_create_event():
    """score POSTs to /api/public/ingestion with type=score-create."""
    seen: list[bytes] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.read())
        return httpx.Response(207)

    _install_mock_client(_handler)
    result = await langfuse_mod.score(
        trace_id="trace-123",
        name="enum_validation_passed",
        value=1.0,
    )
    assert result is None
    body = seen[0].decode("utf-8")
    assert "score-create" in body
    assert "trace-123" in body
    assert "enum_validation_passed" in body


# ── LOCKED: drop-on-failure with WARNING ──────────────────────────────────
async def test_trace_drops_on_5xx_logs_warning_does_not_raise(caplog):
    """5xx → WARNING logged, returns None, NEVER raises."""
    def _handler(_req):
        return httpx.Response(503, text="upstream down")

    _install_mock_client(_handler)
    with caplog.at_level(logging.WARNING, logger="app.adapters.langfuse"):
        result = await langfuse_mod.trace(
            name="test", input={}, output={}
        )

    assert result is None
    assert any("egress dropped" in r.message for r in caplog.records)


async def test_trace_drops_on_connection_error_does_not_raise(caplog):
    """ConnectError → WARNING logged, returns None, NEVER raises."""
    def _handler(_req):
        raise httpx.ConnectError("connection refused")

    _install_mock_client(_handler)
    with caplog.at_level(logging.WARNING, logger="app.adapters.langfuse"):
        result = await langfuse_mod.trace(
            name="test", input={}, output={}
        )
    assert result is None
    assert any("egress dropped" in r.message for r in caplog.records)


async def test_trace_drops_on_timeout_does_not_raise(caplog):
    """Timeout → WARNING, no raise."""
    def _handler(_req):
        raise httpx.TimeoutException("timed out")

    _install_mock_client(_handler)
    with caplog.at_level(logging.WARNING, logger="app.adapters.langfuse"):
        result = await langfuse_mod.trace(
            name="test", input={}, output={}
        )
    assert result is None


async def test_trace_drops_on_unexpected_exception(caplog):
    """Defensive: any Exception is swallowed with WARNING."""
    def _handler(_req):
        raise RuntimeError("unexpected boom")

    _install_mock_client(_handler)
    with caplog.at_level(logging.WARNING, logger="app.adapters.langfuse"):
        result = await langfuse_mod.trace(
            name="test", input={}, output={}
        )
    assert result is None


async def test_score_drops_on_5xx_does_not_raise(caplog):
    """score follows the same drop-on-failure contract as trace."""
    def _handler(_req):
        return httpx.Response(500)

    _install_mock_client(_handler)
    with caplog.at_level(logging.WARNING, logger="app.adapters.langfuse"):
        result = await langfuse_mod.score(
            trace_id="t", name="n", value=0.5
        )
    assert result is None


# ── Missing credentials → no-op with one-time warning ─────────────────────
async def test_missing_credentials_degrades_to_noop(monkeypatch, caplog):
    """No LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY → silent no-op + 1 warning."""
    # Force creds missing
    monkeypatch.setattr(
        langfuse_mod.settings, "LANGFUSE_PUBLIC_KEY", ""
    )
    monkeypatch.setattr(
        langfuse_mod.settings, "LANGFUSE_SECRET_KEY", ""
    )

    call_count = {"n": 0}

    def _handler(_req):
        call_count["n"] += 1
        return httpx.Response(207)

    _install_mock_client(_handler)
    with caplog.at_level(logging.WARNING, logger="app.adapters.langfuse"):
        # First call: warning logged, no network egress
        result_1 = await langfuse_mod.trace(name="x", input={}, output={})
        # Second call: same — no second warning
        result_2 = await langfuse_mod.score(trace_id="t", name="n", value=1.0)

    assert result_1 is None
    assert result_2 is None
    assert call_count["n"] == 0  # NO network egress

    creds_warnings = [
        r for r in caplog.records if "credentials missing" in r.message
    ]
    assert len(creds_warnings) == 1, "credentials warning must log exactly once"


# ── Event envelope shape ──────────────────────────────────────────────────
async def test_trace_generates_id_when_trace_id_omitted():
    """If trace_id arg is None, adapter generates a fresh UUID."""
    seen_bodies: list[bytes] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(request.read())
        return httpx.Response(207)

    _install_mock_client(_handler)
    await langfuse_mod.trace(name="t", input={}, output={})

    body = seen_bodies[0].decode("utf-8")
    # UUID generated — assert it parses as a valid hex string in the payload
    import json

    payload = json.loads(body)
    inner_id = payload["batch"][0]["body"]["id"]
    uuid.UUID(inner_id)  # raises if not a valid UUID


async def test_trace_user_id_serialised_as_string():
    """user_id UUID is serialised to str in the payload."""
    seen_bodies: list[bytes] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(request.read())
        return httpx.Response(207)

    _install_mock_client(_handler)
    uid = uuid.uuid4()
    await langfuse_mod.trace(name="t", input={}, output={}, user_id=uid)

    import json

    body = json.loads(seen_bodies[0].decode("utf-8"))
    assert body["batch"][0]["body"]["userId"] == str(uid)


# ── Boundary discipline ───────────────────────────────────────────────────
def test_no_os_getenv_in_langfuse():
    """§6.G — credentials via settings only."""
    src = inspect.getsource(langfuse_mod)
    assert "os.getenv" not in src


def test_no_business_logic_in_langfuse():
    src = inspect.getsource(langfuse_mod)
    assert "from app.modules" not in src
    assert "import app.modules" not in src

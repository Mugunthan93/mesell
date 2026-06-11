"""Unit tests for ``app.adapters.gemini`` (§6.B + §6.G).

Mocks ``_call_sdk`` (the single SDK touch point) — never makes real
Gemini calls.  Asserts:

* happy path returns the locked :class:`GeminiResponse` envelope
* retry policy: 3 attempts with exponential backoff (1s, 4s, 16s) on
  transient SDK errors (zeroed out in tests for wall-clock speed)
* non-retryable SDK errors raise :class:`GeminiAdapterError` immediately
* retry exhaustion raises :class:`GeminiAdapterError`
* :func:`generate_vision` passes ``image_bytes`` into the SDK call
* no business logic — adapter is pure transport
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from google.api_core import exceptions as gcore_exc

from app.adapters import AdapterError, GeminiAdapterError
from app.adapters import gemini as gemini_mod
from app.core.errors import MeesellError

pytestmark = pytest.mark.unit


@dataclass
class _FakeUsage:
    prompt_token_count: int
    candidates_token_count: int


@dataclass
class _FakeCandidate:
    finish_reason: Any


@dataclass
class _FakeSDKResponse:
    """Duck-typed Gemini SDK response — matches the shape ``_envelope`` reads."""

    text: str
    usage_metadata: _FakeUsage
    candidates: list[_FakeCandidate]


def _ok_response(text: str = "hello", in_tok: int = 5, out_tok: int = 3) -> _FakeSDKResponse:
    return _FakeSDKResponse(
        text=text,
        usage_metadata=_FakeUsage(prompt_token_count=in_tok, candidates_token_count=out_tok),
        candidates=[_FakeCandidate(finish_reason="STOP")],
    )


@pytest.fixture(autouse=True)
def _reset_module(monkeypatch):
    """Reset module-level singleton state + zero out retry backoff for speed."""
    gemini_mod._reset_for_testing()
    monkeypatch.setattr(gemini_mod, "_RETRY_DELAYS_S", (0.0, 0.0, 0.0))
    yield
    gemini_mod._reset_for_testing()


# ── Exception hierarchy ────────────────────────────────────────────────────
def test_gemini_adapter_error_is_meesell_error():
    """``GeminiAdapterError`` MUST subclass ``MeesellError`` per §6.G."""
    assert issubclass(GeminiAdapterError, AdapterError)
    assert issubclass(GeminiAdapterError, MeesellError)


def test_gemini_adapter_error_default_status_502():
    """§6.G — every AdapterError defaults to HTTP 502 (Bad Gateway)."""
    err = GeminiAdapterError()
    assert err.status_code == 502
    assert err.validation_message_id == "gemini.unavailable"


# ── Happy path ─────────────────────────────────────────────────────────────
async def test_generate_text_happy_path(monkeypatch):
    """generate_text returns a populated GeminiResponse envelope."""
    calls: list[dict] = []

    async def _mock_sdk(**kwargs):
        calls.append(kwargs)
        return _ok_response(text="The mango is ripe.", in_tok=12, out_tok=7)

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    resp = await gemini_mod.generate_text(
        "Describe a mango.", temperature=0.0
    )

    assert isinstance(resp, gemini_mod.GeminiResponse)
    assert resp.text == "The mango is ripe."
    assert resp.input_tokens == 12
    assert resp.output_tokens == 7
    assert resp.finish_reason == "STOP"
    # Envelope MUST carry a debug `raw` dict (NEVER returned to API per §6.B)
    assert isinstance(resp.raw, dict)
    assert resp.raw.get("usage", {}).get("input") == 12

    # SDK is called exactly once on happy path
    assert len(calls) == 1
    assert calls[0]["prompt"] == "Describe a mango."
    assert calls[0]["image_bytes"] is None
    assert calls[0]["generation_config"]["temperature"] == 0.0


async def test_generate_text_respects_max_output_tokens(monkeypatch):
    """max_output_tokens propagates into generation_config."""
    captured: dict[str, Any] = {}

    async def _mock_sdk(**kwargs):
        captured.update(kwargs)
        return _ok_response()

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    await gemini_mod.generate_text("prompt", max_output_tokens=128)
    assert captured["generation_config"]["max_output_tokens"] == 128


async def test_generate_text_respects_response_mime_type(monkeypatch):
    """response_mime_type='application/json' propagates."""
    captured: dict[str, Any] = {}

    async def _mock_sdk(**kwargs):
        captured.update(kwargs)
        return _ok_response()

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    await gemini_mod.generate_text("prompt", response_mime_type="application/json")
    assert captured["generation_config"]["response_mime_type"] == "application/json"


# ── generate_vision ────────────────────────────────────────────────────────
async def test_generate_vision_passes_image_bytes(monkeypatch):
    """generate_vision forwards image_bytes + mime_type into the SDK call."""
    captured: dict[str, Any] = {}

    async def _mock_sdk(**kwargs):
        captured.update(kwargs)
        return _ok_response(text="A bag of chips.")

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    img = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
    resp = await gemini_mod.generate_vision("Describe the image.", img)

    assert captured["image_bytes"] == img
    assert captured["image_mime_type"] == "image/jpeg"
    assert resp.text == "A bag of chips."


# ── Transient retry (3 attempts, 1s/4s/16s) ───────────────────────────────
async def test_transient_503_retries_then_succeeds(monkeypatch):
    """503 ServiceUnavailable on first 2 calls, success on 3rd."""
    attempts = {"n": 0}

    async def _mock_sdk(**kwargs):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise gcore_exc.ServiceUnavailable("transient 503")
        return _ok_response(text="finally")

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    resp = await gemini_mod.generate_text("prompt")
    assert resp.text == "finally"
    assert attempts["n"] == 3


async def test_transient_429_retries(monkeypatch):
    """429 TooManyRequests is retryable per §6.B."""
    attempts = {"n": 0}

    async def _mock_sdk(**kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise gcore_exc.TooManyRequests("rate limited")
        return _ok_response()

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    await gemini_mod.generate_text("prompt")
    assert attempts["n"] == 2


async def test_transient_connection_error_retries(monkeypatch):
    """Builtin ConnectionError is retryable per §6.B."""
    attempts = {"n": 0}

    async def _mock_sdk(**kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ConnectionError("socket reset")
        return _ok_response()

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    await gemini_mod.generate_text("prompt")
    assert attempts["n"] == 2


async def test_retry_exhaustion_raises_gemini_adapter_error(monkeypatch):
    """4 attempts (1 + 3 retries) of 503 → GeminiAdapterError."""
    attempts = {"n": 0}

    async def _mock_sdk(**kwargs):
        attempts["n"] += 1
        raise gcore_exc.ServiceUnavailable("503 forever")

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    with pytest.raises(GeminiAdapterError):
        await gemini_mod.generate_text("prompt")
    # 1 initial + 3 retries = 4 attempts
    assert attempts["n"] == 4


# ── Non-retryable error mapping ────────────────────────────────────────────
async def test_non_retryable_auth_error_raises_immediately(monkeypatch):
    """403 / 401 (Unauthorized / PermissionDenied) is NOT retryable — raises."""
    attempts = {"n": 0}

    async def _mock_sdk(**kwargs):
        attempts["n"] += 1
        raise gcore_exc.Unauthenticated("bad api key")

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    with pytest.raises(GeminiAdapterError):
        await gemini_mod.generate_text("prompt")
    # NO retries on non-retryable error
    assert attempts["n"] == 1


async def test_non_retryable_invalid_argument_raises_immediately(monkeypatch):
    """400 InvalidArgument is NOT retryable — raises immediately."""
    attempts = {"n": 0}

    async def _mock_sdk(**kwargs):
        attempts["n"] += 1
        raise gcore_exc.InvalidArgument("malformed")

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    with pytest.raises(GeminiAdapterError):
        await gemini_mod.generate_text("prompt")
    assert attempts["n"] == 1


async def test_gemini_adapter_error_chains_original(monkeypatch):
    """Raised GeminiAdapterError carries the SDK exception via ``__cause__``."""
    async def _mock_sdk(**kwargs):
        raise gcore_exc.InvalidArgument("bad request")

    monkeypatch.setattr(gemini_mod, "_call_sdk", _mock_sdk)
    with pytest.raises(GeminiAdapterError) as excinfo:
        await gemini_mod.generate_text("prompt")
    assert isinstance(excinfo.value.__cause__, gcore_exc.InvalidArgument)


# ── Defensive envelope ─────────────────────────────────────────────────────
def test_envelope_handles_missing_usage_metadata():
    """Older SDK responses may lack usage_metadata — envelope must not crash."""
    @dataclass
    class _Bare:
        text: str
        usage_metadata: None = None
        candidates: list = None

    raw = _Bare(text="hi")
    env = gemini_mod._envelope(raw)
    assert env.text == "hi"
    assert env.input_tokens == 0
    assert env.output_tokens == 0
    assert env.finish_reason == ""


def test_envelope_handles_missing_text():
    """Defensive — content-blocked responses can omit text."""
    @dataclass
    class _Blocked:
        text: str | None = None
        usage_metadata: None = None
        candidates: list = None

    env = gemini_mod._envelope(_Blocked())
    assert env.text == ""


# ── Boundary discipline ───────────────────────────────────────────────────
def test_no_business_logic_imports_in_gemini():
    """§6.G — adapter MUST NOT import from any domain module (`app.modules.*`)."""
    import inspect

    src = inspect.getsource(gemini_mod)
    assert "from app.modules" not in src
    assert "import app.modules" not in src
    # NO os.getenv per §6.G "credentials via settings" rule
    assert "os.getenv" not in src

"""AI-BE-02 — call_gemini adapter-failure → graceful fallback envelope.

Wave: qa-image-ai (Wave A).  Extends the existing ``test_ai_ops_client.py``
suite (10 tests); fills the single gap: the ``except Exception`` branch at
L228 of ``client.py`` (adapter-level failure after budget reservation).

Scenario (AI-BE-02):
  Given ``generate_text`` raises an unexpected exception;
  When ``call_gemini`` is invoked;
  Then the function NEVER raises — instead it returns an ``AIResponse``
  with ``parsed == _fallback_parsed(workload, reason="adapter_failure")``,
  ``cost_inr == 0.0``, and the budget reservation is released at 0 cost.

This is the §6A.F "domain MUST NOT see a vendor-level exception" invariant.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.ai_ops import client as ai_client
from app.ai_ops.client import AICallContext, AIResponse

pytestmark = pytest.mark.unit


class TestCallGeminiAdapterFailureFallback:
    """AI-BE-02 — adapter-level exception → graceful fallback (never raises)."""

    async def test_generate_text_raises_returns_adapter_failure_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Adapter raises RuntimeError → fallback parsed, cost_inr=0, no re-raise."""
        user_id = uuid.uuid4()
        ctx = AICallContext(workload="autofill", user_id=user_id)

        # Stub: budget_cap.check_and_reserve returns a reservation
        # Stub: budget_cap.release_reservation records calls
        released: list[tuple] = []

        async def _fake_reserve(*a, **kw) -> str:
            return "test-reservation-id"

        async def _fake_release(reservation_id: str, cost: float) -> None:
            released.append((reservation_id, cost))

        # Stub: generate_text raises
        async def _raise_adapter(*a, **kw):
            raise RuntimeError("Simulated transport-level failure")

        monkeypatch.setattr("app.ai_ops.budget_cap.check_and_reserve", _fake_reserve)
        monkeypatch.setattr("app.ai_ops.budget_cap.release_reservation", _fake_release)
        monkeypatch.setattr("app.adapters.gemini.generate_text", _raise_adapter)

        # Must NOT raise
        response = await ai_client.call_gemini(
            ctx,
            prompt_id="autofill.v1",
            prompt_vars={"product_spec": "test spec", "schema": "{}"},
        )

        assert isinstance(response, AIResponse)
        # Parsed must be the adapter_failure fallback shape
        assert isinstance(response.parsed, dict)
        assert response.parsed.get("fallback_offered") is True, (
            f"Expected fallback_offered=True in parsed, got: {response.parsed}"
        )
        # Cost must be 0 (no tokens consumed)
        assert response.cost_inr == 0.0

    async def test_generate_text_raises_releases_reservation_at_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """On adapter failure, reservation is released at 0 cost."""
        user_id = uuid.uuid4()
        ctx = AICallContext(workload="smart_picker", user_id=user_id)

        released: list[tuple] = []

        async def _fake_reserve(*a, **kw) -> str:
            return "reservation-xyz"

        async def _fake_release(reservation_id: str, cost: float) -> None:
            released.append((reservation_id, cost))

        async def _raise_adapter(*a, **kw):
            raise ConnectionError("Simulated connection failure")

        monkeypatch.setattr("app.ai_ops.budget_cap.check_and_reserve", _fake_reserve)
        monkeypatch.setattr("app.ai_ops.budget_cap.release_reservation", _fake_release)
        monkeypatch.setattr("app.adapters.gemini.generate_text", _raise_adapter)

        await ai_client.call_gemini(
            ctx,
            prompt_id="smart_picker.v1",
            prompt_vars={"description": "test"},
        )

        # Reservation must be released at 0 cost (no tokens were consumed)
        assert len(released) == 1, (
            f"Expected 1 release call, got {len(released)}: {released}"
        )
        reservation_id, cost = released[0]
        assert cost == 0.0, (
            f"Reservation must be released at 0 cost on adapter failure, got: {cost}"
        )

    async def test_watermark_generate_vision_raises_returns_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Vision adapter raises → watermark workload returns the watermark fallback."""
        user_id = uuid.uuid4()
        ctx = AICallContext(workload="watermark", user_id=user_id)

        async def _fake_reserve(*a, **kw) -> str:
            return "reservation-wm"

        async def _fake_release(*a, **kw) -> None:
            return None

        async def _raise_vision(*a, **kw):
            raise TimeoutError("Vision adapter timed out")

        monkeypatch.setattr("app.ai_ops.budget_cap.check_and_reserve", _fake_reserve)
        monkeypatch.setattr("app.ai_ops.budget_cap.release_reservation", _fake_release)
        monkeypatch.setattr("app.adapters.gemini.generate_vision", _raise_vision)

        image_bytes = b"\xff\xd8\xff" + b"\x00" * 100  # minimal bytes for type check

        response = await ai_client.call_gemini(
            ctx,
            prompt_id="watermark.v1",
            prompt_vars={},
            image_bytes=image_bytes,
        )

        assert isinstance(response.parsed, dict)
        # Watermark fallback always has watermark_check key
        assert "watermark_check" in response.parsed or response.parsed.get("fallback_offered"), (
            f"Watermark adapter failure should produce watermark fallback. Got: {response.parsed}"
        )

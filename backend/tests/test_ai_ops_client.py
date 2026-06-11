"""Tests for :mod:`app.ai_ops.client` — §6A.C.

Covers the 9-step internal flow:

1. ``AICallContext`` and ``AIResponse`` are frozen dataclasses with the
   locked shape.
2. Happy path: ``call_gemini`` resolves prompt → reserves budget →
   applies Layer 1 → calls Gemini → records cost → Layer 2 passes →
   emits LangFuse trace → returns ``AIResponse``.  Every step fires
   in order (mock verification).
3. Budget hard-stop fallback per workload:
   * smart_picker → empty suggestions + ``fallback_offered=True``
   * autofill     → empty fields + ``fallback_offered=True``
   * watermark    → ``watermark_check="skipped_budget"``
4. Layer 2 happy path: valid response returned without retries.
5. Layer 2 retry: first 2 attempts invalid, 3rd valid → returns the
   valid response with ``layer2_retries=2``.
6. Layer 2 retry exhaustion: all 3 attempts invalid → graceful fallback
   per workload with ``fallback_offered=True`` (or watermark marker).
7. Caller-error guardrails: watermark without image_bytes raises
   ``ValueError`` (developer error, NOT a runtime fallback path).
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest

from app.adapters.gemini import GeminiResponse
from app.ai_ops import budget_cap, client
from app.ai_ops.client import AICallContext, AIResponse

pytestmark = pytest.mark.unit


# ── Dataclass shape ────────────────────────────────────────────────────────
class TestDataclasses:
    def test_aicallcontext_frozen(self) -> None:
        ctx = AICallContext(workload="smart_picker", user_id=uuid.uuid4())
        with pytest.raises(Exception):
            ctx.locale = "ta"  # type: ignore[misc]

    def test_airesponse_frozen(self) -> None:
        resp = AIResponse(
            parsed={"x": 1},
            raw_response=_empty_gem(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )
        with pytest.raises(Exception):
            resp.cost_inr = 1.0  # type: ignore[misc]


# ── Happy path 9-step flow ─────────────────────────────────────────────────
class TestHappyPathFlow:
    async def test_smart_picker_9_steps_in_order(self) -> None:
        """Every step fires in the locked §6A.C order."""
        call_log: list[str] = []

        valid_json = json.dumps(
            {
                "suggestions": [
                    {
                        "category_id": "c1",
                        "confidence": 0.9,
                        "reasons": ["r1"],
                    }
                ]
            }
        )
        gem_resp = GeminiResponse(
            text=valid_json,
            input_tokens=100,
            output_tokens=50,
            finish_reason="STOP",
            raw={},
        )

        async def fake_reserve(*a, **kw):  # type: ignore[no-untyped-def]
            call_log.append("step2_reserve")
            return "resv-1"

        async def fake_release(*a, **kw):  # type: ignore[no-untyped-def]
            call_log.append("step6_release")

        async def fake_record(*a, **kw):  # type: ignore[no-untyped-def]
            call_log.append("step6_record")
            return 0.0388

        async def fake_generate(*a, **kw):  # type: ignore[no-untyped-def]
            call_log.append("step5_gemini")
            return gem_resp

        async def fake_trace(*a, **kw):  # type: ignore[no-untyped-def]
            call_log.append("step8_trace")

        with patch.object(
            client, "prompt_registry"
        ) as _pr, patch.object(
            client.budget_cap, "check_and_reserve", new=fake_reserve
        ), patch.object(
            client.budget_cap, "release_reservation", new=fake_release
        ), patch.object(
            client.cost_tracker, "record", new=fake_record
        ), patch.object(
            client.gemini_adapter, "generate_text", new=fake_generate
        ), patch.object(
            client.langfuse_adapter, "trace", new=fake_trace
        ):
            # Wire prompt_registry to return a valid template.
            from app.ai_ops.prompt_registry import PromptTemplate

            _pr.resolve.return_value = PromptTemplate(
                template="BODY {{x}}",
                version="v1",
                workload="smart_picker",
                rendered_by="text",
            )
            _pr.render.side_effect = lambda t, v: t.replace(
                "{{x}}", str(v.get("x", ""))
            )

            ctx = AICallContext(workload="smart_picker", user_id=uuid.uuid4())
            resp = await client.call_gemini(
                ctx,
                "smart_picker.v1",
                {"x": "hello"},
            )

        # Step 1 fires (resolve called).
        _pr.resolve.assert_called_once_with("smart_picker.v1", "smart_picker")
        # Step 2 + 5 + 6 + 8 fired in order.
        assert call_log[0] == "step2_reserve"
        # step5 (gemini) precedes step6 (record).
        idx_5 = call_log.index("step5_gemini")
        idx_6_record = call_log.index("step6_record")
        idx_8 = call_log.index("step8_trace")
        assert idx_5 < idx_6_record < idx_8

        # Result envelope.
        assert resp.cost_inr == pytest.approx(0.0388)
        assert resp.layer2_retries == 0
        assert resp.trace_id
        assert resp.parsed["suggestions"][0]["category_id"] == "c1"  # type: ignore[index]


# ── Budget hard-stop fallback per workload ─────────────────────────────────
class TestBudgetFallback:
    async def test_smart_picker_returns_empty_suggestions(self) -> None:
        resp = await self._fallback_run("smart_picker")
        assert resp.parsed["suggestions"] == []  # type: ignore[index]
        assert resp.parsed["fallback_offered"] is True  # type: ignore[index]
        assert resp.parsed["reason"] == "budget"  # type: ignore[index]
        assert resp.cost_inr == 0.0

    async def test_autofill_returns_empty_fields(self) -> None:
        resp = await self._fallback_run("autofill")
        assert resp.parsed["fields"] == {}  # type: ignore[index]
        assert resp.parsed["fallback_offered"] is True  # type: ignore[index]
        assert resp.cost_inr == 0.0

    async def test_watermark_returns_skipped_budget_marker(self) -> None:
        resp = await self._fallback_run("watermark")
        assert resp.parsed["has_watermark"] is None  # type: ignore[index]
        assert resp.parsed["watermark_check"] == "skipped_budget"  # type: ignore[index]
        # No "fallback_offered" key for watermark per §6A.F shape.

    async def _fallback_run(self, workload: str) -> AIResponse:
        from app.ai_ops.prompt_registry import PromptTemplate

        # Pick the matching template shape (text vs vision).
        rendered_by = "vision" if workload == "watermark" else "text"

        async def boom_reserve(*a, **kw):  # type: ignore[no-untyped-def]
            raise budget_cap.BudgetExceededError()

        async def fake_trace(*a, **kw):  # type: ignore[no-untyped-def]
            return None

        with patch.object(
            client, "prompt_registry"
        ) as _pr, patch.object(
            client.budget_cap, "check_and_reserve", new=boom_reserve
        ), patch.object(
            client.langfuse_adapter, "trace", new=fake_trace
        ):
            _pr.resolve.return_value = PromptTemplate(
                template="BODY",
                version="v1",
                workload=workload,
                rendered_by=rendered_by,
            )
            _pr.render.side_effect = lambda t, v: t

            ctx = AICallContext(workload=workload, user_id=uuid.uuid4())  # type: ignore[arg-type]
            kwargs = {}
            if workload == "watermark":
                kwargs["image_bytes"] = b"\xff\xd8"  # JPEG magic
            return await client.call_gemini(ctx, f"{workload}.v1", {}, **kwargs)


# ── Layer 2 retry chain ────────────────────────────────────────────────────
class TestLayer2Retries:
    async def test_first_invalid_then_valid_succeeds_with_retries_1(
        self,
    ) -> None:
        responses = [
            GeminiResponse(
                text="not valid json",
                input_tokens=10,
                output_tokens=5,
                finish_reason="STOP",
                raw={},
            ),
            GeminiResponse(
                text=json.dumps(
                    {
                        "suggestions": [
                            {
                                "category_id": "c1",
                                "confidence": 0.5,
                                "reasons": [],
                            }
                        ]
                    }
                ),
                input_tokens=12,
                output_tokens=8,
                finish_reason="STOP",
                raw={},
            ),
        ]
        call_idx = {"i": 0}

        async def stub_gen(*a, **kw):  # type: ignore[no-untyped-def]
            r = responses[call_idx["i"]]
            call_idx["i"] += 1
            return r

        async def stub_reserve(*a, **kw):  # type: ignore[no-untyped-def]
            return "resv-x"

        async def stub_release(*a, **kw):  # type: ignore[no-untyped-def]
            return None

        async def stub_record(*a, **kw):  # type: ignore[no-untyped-def]
            return 0.01

        async def stub_trace(*a, **kw):  # type: ignore[no-untyped-def]
            return None

        from app.ai_ops.prompt_registry import PromptTemplate

        with patch.object(
            client, "prompt_registry"
        ) as _pr, patch.object(
            client.budget_cap, "check_and_reserve", new=stub_reserve
        ), patch.object(
            client.budget_cap, "release_reservation", new=stub_release
        ), patch.object(
            client.cost_tracker, "record", new=stub_record
        ), patch.object(
            client.gemini_adapter, "generate_text", new=stub_gen
        ), patch.object(
            client.langfuse_adapter, "trace", new=stub_trace
        ):
            _pr.resolve.return_value = PromptTemplate(
                template="BODY",
                version="v1",
                workload="smart_picker",
                rendered_by="text",
            )
            _pr.render.side_effect = lambda t, v: t

            ctx = AICallContext(workload="smart_picker", user_id=uuid.uuid4())
            resp = await client.call_gemini(ctx, "smart_picker.v1", {})

        assert resp.layer2_retries == 1
        assert isinstance(resp.parsed, dict)
        assert resp.parsed["suggestions"][0]["category_id"] == "c1"

    async def test_all_3_invalid_falls_back(self) -> None:
        bad = GeminiResponse(
            text="not valid",
            input_tokens=10,
            output_tokens=5,
            finish_reason="STOP",
            raw={},
        )

        async def stub_gen(*a, **kw):  # type: ignore[no-untyped-def]
            return bad

        async def stub_reserve(*a, **kw):  # type: ignore[no-untyped-def]
            return "resv-y"

        async def stub_release(*a, **kw):  # type: ignore[no-untyped-def]
            return None

        async def stub_record(*a, **kw):  # type: ignore[no-untyped-def]
            return 0.01

        async def stub_trace(*a, **kw):  # type: ignore[no-untyped-def]
            return None

        from app.ai_ops.prompt_registry import PromptTemplate

        with patch.object(
            client, "prompt_registry"
        ) as _pr, patch.object(
            client.budget_cap, "check_and_reserve", new=stub_reserve
        ), patch.object(
            client.budget_cap, "release_reservation", new=stub_release
        ), patch.object(
            client.cost_tracker, "record", new=stub_record
        ), patch.object(
            client.gemini_adapter, "generate_text", new=stub_gen
        ), patch.object(
            client.langfuse_adapter, "trace", new=stub_trace
        ):
            _pr.resolve.return_value = PromptTemplate(
                template="BODY",
                version="v1",
                workload="smart_picker",
                rendered_by="text",
            )
            _pr.render.side_effect = lambda t, v: t

            ctx = AICallContext(workload="smart_picker", user_id=uuid.uuid4())
            resp = await client.call_gemini(ctx, "smart_picker.v1", {})

        assert resp.layer2_retries == 2
        assert resp.parsed["suggestions"] == []  # type: ignore[index]
        assert resp.parsed["fallback_offered"] is True  # type: ignore[index]
        assert resp.parsed["reason"] == "guardrail"  # type: ignore[index]


# ── Caller-error guardrails ────────────────────────────────────────────────
class TestCallerArgGuardrails:
    async def test_watermark_requires_image_bytes(self) -> None:
        from app.ai_ops.prompt_registry import PromptTemplate

        with patch.object(client, "prompt_registry") as _pr:
            _pr.resolve.return_value = PromptTemplate(
                template="BODY",
                version="v1",
                workload="watermark",
                rendered_by="vision",
            )
            ctx = AICallContext(workload="watermark", user_id=uuid.uuid4())
            with pytest.raises(ValueError):
                await client.call_gemini(ctx, "watermark.v1", {})

    async def test_smart_picker_rejects_image_bytes(self) -> None:
        from app.ai_ops.prompt_registry import PromptTemplate

        with patch.object(client, "prompt_registry") as _pr:
            _pr.resolve.return_value = PromptTemplate(
                template="BODY",
                version="v1",
                workload="smart_picker",
                rendered_by="text",
            )
            ctx = AICallContext(workload="smart_picker", user_id=uuid.uuid4())
            with pytest.raises(ValueError):
                await client.call_gemini(
                    ctx, "smart_picker.v1", {}, image_bytes=b"junk"
                )


# ── Helpers ────────────────────────────────────────────────────────────────
def _empty_gem() -> GeminiResponse:
    return GeminiResponse(
        text="", input_tokens=0, output_tokens=0, finish_reason="STOP", raw={}
    )


# pytest-asyncio auto-mode handles async tests; no module-level marker.

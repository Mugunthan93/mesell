"""Unified AI call entry point — §6A.C.

This module IS the sole import surface domain modules use for AI work.
Every Smart Picker call, Auto-fill call, and Vision call from
``category``, ``catalog``, ``image`` flows through :func:`call_gemini`.

The 9-step internal flow (locked, in order)
-------------------------------------------
1. :func:`ai_ops.prompt_registry.resolve` — pick up template + version.
2. :func:`ai_ops.budget_cap.check_and_reserve` — race-safe daily-cap
   gate.  Raises :class:`ai_ops.budget_cap.BudgetExceededError` at
   100% — caught here and mapped to a per-workload graceful fallback
   per §6A.F (dispatch acceptance criterion #7).
3. :func:`ai_ops.guardrail.apply_prompt_constraint` — Layer 1 prefix.
4. :func:`ai_ops.prompt_registry.render` — substitute ``{{var}}`` placeholders.
5. :func:`adapters.gemini.generate_text` OR ``generate_vision`` — the SDK call.
6. :func:`ai_ops.cost_tracker.record` — audit_events row + reservation
   release + per-user-per-hour analytics.
7. :func:`ai_ops.guardrail.parse_and_validate` — Layer 2 enum/shape check;
   retries up to 2 times with a stricter prompt on failure; falls
   through to a workload-specific safe fallback on final exhaustion.
8. :func:`adapters.langfuse.trace` — fire-and-forget egress.
9. Return :class:`AIResponse`.

Per-workload graceful fallback shape (§6A.F + dispatch criterion #7)
--------------------------------------------------------------------
* ``smart_picker``: ``parsed = {"suggestions": [], "fallback_offered": True,
  "reason": <budget|guardrail>}``.  Consumer module returns HTTP 200.
* ``autofill``:     ``parsed = {"fields": {}, "fallback_offered": True,
  "reason": <budget|guardrail>}``.  Consumer module returns HTTP 200.
* ``watermark``:    ``parsed = {"has_watermark": None, "confidence": 0.0,
  "watermark_check": "skipped_budget"|"skipped_guardrail"}``.  Consumer
  worker writes ``precheck_jsonb.watermark_check`` accordingly; overall
  precheck status stays ``"ready"``.

Locked rule (per §6A.C + §3.G + §19 import-linter Contract 2)
-------------------------------------------------------------
Domain modules import ONLY :func:`call_gemini` (and the
:class:`AICallContext` / :class:`AIResponse` dataclasses).  Domain
modules NEVER import :mod:`ai_ops.guardrail`, :mod:`ai_ops.cost_tracker`,
:mod:`ai_ops.budget_cap` — those are internal.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.adapters import gemini as gemini_adapter
from app.adapters import langfuse as langfuse_adapter
from app.adapters.gemini import GeminiResponse

# Sub-module imports.  Python's ``from package import submodule`` form
# triggers a sub-module load when the name is not yet a package
# attribute, then attaches it — this is the cleanest pattern for
# loading ``ai_ops`` siblings from inside ``ai_ops/__init__.py``
# mid-execution (the alternative ``from .X import name`` form would
# also work but couples the per-name surface to the call sites below).
from app.ai_ops import budget_cap, cost_tracker, guardrail, prompt_registry
from app.ai_ops.cost_tracker import Workload

logger = logging.getLogger(__name__)


# ── Frozen dataclasses (per §6A.C) ─────────────────────────────────────────
@dataclass(frozen=True)
class AICallContext:
    """Per-call context bundle.  Locked shape per §6A.C."""

    workload: Workload
    user_id: UUID
    locale: str = "en"
    # Caller-provided trace ID for chained traces (e.g. autofill spans
    # multiple call_gemini invocations across a single seller action).
    trace_id: str | None = None


@dataclass(frozen=True)
class AIResponse:
    """Result envelope returned to domain modules.  Locked shape per §6A.C.

    ``parsed`` carries the workload-specific output shape — including the
    graceful-fallback envelope when budget exhaustion or guardrail
    retry-exhaustion occurs (see module docstring).  Consumer modules
    branch on ``parsed.get("fallback_offered")`` or
    ``parsed.get("watermark_check")`` to detect the fallback path.
    """

    parsed: dict[str, Any] | str
    raw_response: GeminiResponse
    cost_inr: float
    layer2_retries: int
    trace_id: str


# ── Internals — sentinel fallback envelope ─────────────────────────────────
def _empty_gemini_response() -> GeminiResponse:
    """Sentinel envelope used for fallback paths where no SDK call fired."""
    return GeminiResponse(
        text="",
        input_tokens=0,
        output_tokens=0,
        finish_reason="FALLBACK",
        raw={"fallback": True},
    )


def _fallback_parsed(workload: Workload, reason: str) -> dict[str, Any]:
    """Build the workload-specific graceful-fallback payload.

    Per §6A.F + dispatch acceptance criterion #7.
    """
    if workload == "smart_picker":
        return {"suggestions": [], "fallback_offered": True, "reason": reason}
    if workload == "autofill":
        return {"fields": {}, "fallback_offered": True, "reason": reason}
    # watermark
    skip_marker = (
        "skipped_budget" if reason == "budget" else "skipped_guardrail"
    )
    return {
        "has_watermark": None,
        "confidence": 0.0,
        "watermark_check": skip_marker,
    }


# ── 9-step flow ────────────────────────────────────────────────────────────
async def call_gemini(
    ctx: AICallContext,
    prompt_id: str,
    prompt_vars: dict[str, Any] | None = None,
    *,
    image_bytes: bytes | None = None,
    allowed_enums: dict[str, list[str]] | None = None,
    response_mime_type: str | None = "application/json",
    max_output_tokens: int | None = None,
) -> AIResponse:
    """Run a single AI call through the 9-step §6A.C flow.

    See module docstring for the step-by-step contract.

    Args:
        ctx: Per-call context (workload + user_id + locale + optional
            inbound trace_id).
        prompt_id: e.g. ``"smart_picker.v1"`` — resolved via
            :mod:`ai_ops.prompt_registry`.
        prompt_vars: ``{{var}}`` substitutions for the template.
        image_bytes: Required iff ``ctx.workload == "watermark"``.
        allowed_enums: Per-field allowlist; required for ``autofill``
            with enum-constrained fields.  Layer 1 prefix appends an
            allowed-enum block when supplied; Layer 2 rejects any value
            not in the allowlist.
        response_mime_type: SDK hint — default ``"application/json"``
            for all 3 workloads; pass ``None`` for free-text responses.
        max_output_tokens: Per-call cap; ``None`` lets the SDK default.

    Returns:
        :class:`AIResponse` with workload-specific ``parsed`` shape.
        Budget hard-stops and Layer 2 retry exhaustion produce a
        graceful-fallback envelope; the call always returns — never
        raises — for the 3 V1 workloads.
    """
    prompt_vars = prompt_vars or {}
    trace_id = ctx.trace_id or uuid.uuid4().hex
    layer2_retries = 0

    # ── Step 1: resolve prompt ──────────────────────────────────────────────
    template = prompt_registry.resolve(prompt_id, ctx.workload)

    # Validate workload-specific argument expectations early.  We catch
    # caller mistakes BEFORE consuming any budget or making any SDK call.
    _validate_workload_args(ctx.workload, template.rendered_by, image_bytes)

    # ── Step 2: budget reservation (race-safe; raises on cap hit) ──────────
    try:
        reservation_id: str | None = await budget_cap.check_and_reserve(
            ctx.workload,
            ctx.user_id,
            estimated_tokens=_estimate_prompt_tokens(template.template, prompt_vars),
        )
    except budget_cap.BudgetExceededError:
        # Per §6A.F: map to workload-specific graceful fallback.
        # Emit a trace tagged budget_fallback for observability.
        await _emit_fallback_trace(
            ctx, prompt_id, reason="budget", trace_id=trace_id
        )
        return AIResponse(
            parsed=_fallback_parsed(ctx.workload, reason="budget"),
            raw_response=_empty_gemini_response(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id=trace_id,
        )

    # ── Step 3 + 4: Layer 1 prefix + template render ──────────────────────
    rendered_prompt = prompt_registry.render(template.template, prompt_vars)
    full_prompt = guardrail.apply_prompt_constraint(
        rendered_prompt, ctx.workload, allowed_enums
    )

    raw_response: GeminiResponse = _empty_gemini_response()
    parsed: dict[str, Any] | None = None
    cost_inr_total = 0.0
    last_response_text = ""

    # Retry loop: up to 2 Layer-2 retries (3 total Gemini calls).
    for attempt in range(3):
        try:
            # ── Step 5: SDK call ─────────────────────────────────────────
            if template.rendered_by == "vision":
                assert image_bytes is not None  # validated above
                raw_response = await gemini_adapter.generate_vision(
                    full_prompt,
                    image_bytes,
                    response_mime_type=None,  # vision SDK ignores
                    max_output_tokens=max_output_tokens,
                )
            else:
                raw_response = await gemini_adapter.generate_text(
                    full_prompt,
                    response_mime_type=response_mime_type,
                    max_output_tokens=max_output_tokens,
                )
        except Exception as exc:
            # Transport-level failure (already retry-exhausted inside the
            # adapter per §6.B).  Release the reservation against zero
            # cost and propagate as a graceful fallback — domain MUST NOT
            # see a vendor-level exception per §6A.F philosophy.
            logger.warning(
                "ai_ops.client: adapter call failed (workload=%s prompt=%s "
                "attempt=%d): %r",
                ctx.workload,
                prompt_id,
                attempt + 1,
                exc,
            )
            await budget_cap.release_reservation(reservation_id, 0.0)
            await _emit_fallback_trace(
                ctx, prompt_id, reason="adapter_failure", trace_id=trace_id
            )
            return AIResponse(
                parsed=_fallback_parsed(ctx.workload, reason="adapter_failure"),
                raw_response=_empty_gemini_response(),
                cost_inr=cost_inr_total,
                layer2_retries=layer2_retries,
                trace_id=trace_id,
            )

        last_response_text = raw_response.text

        # ── Step 6: cost record (only on attempts that consumed tokens) ──
        call_cost = await cost_tracker.record(
            user_id=ctx.user_id,
            workload=ctx.workload,
            input_tokens=raw_response.input_tokens,
            output_tokens=raw_response.output_tokens,
            # Pass reservation only on the FINAL attempt so we don't
            # double-release.  Use sentinel on the path below.
            reservation_id=None if attempt < 2 else reservation_id,
        )
        cost_inr_total += call_cost

        # ── Step 7: Layer 2 validate + retry decision ───────────────────
        parsed = guardrail.parse_and_validate(
            raw_response.text, ctx.workload, allowed_enums
        )
        if parsed is not None:
            # On success BEFORE the final attempt we still need to release
            # the reservation (it wasn't passed to record() above).
            if attempt < 2:
                await budget_cap.release_reservation(reservation_id, cost_inr_total)
            break

        # Layer 2 failed.  If we have retries left, build a stricter
        # prompt and retry.  Otherwise fall through to fallback.
        if attempt < 2:
            layer2_retries += 1
            full_prompt = guardrail.apply_prompt_constraint(
                guardrail.build_retry_prompt(
                    rendered_prompt,
                    ctx.workload,
                    last_response_text,
                    allowed_enums,
                ),
                ctx.workload,
                allowed_enums,
            )

    # ── Step 8: LangFuse trace (fire-and-forget) ──────────────────────────
    await langfuse_adapter.trace(
        name=f"ai_ops.{ctx.workload}",
        input={
            "prompt_id": prompt_id,
            "vars_keys": list(prompt_vars.keys()),
            "allowed_enums_keys": (
                list(allowed_enums.keys()) if allowed_enums else []
            ),
        },
        output={
            "finish_reason": raw_response.finish_reason,
            "input_tokens": raw_response.input_tokens,
            "output_tokens": raw_response.output_tokens,
            "cost_inr": cost_inr_total,
            "layer2_retries": layer2_retries,
            "fallback_offered": parsed is None
            or (isinstance(parsed, dict) and parsed.get("fallback_offered") is True),
        },
        metadata={
            "version": template.version,
            "locale": ctx.locale,
        },
        user_id=ctx.user_id,
        trace_id=trace_id,
    )

    # ── Step 9: return ────────────────────────────────────────────────────
    if parsed is None:
        # Layer 2 retry exhaustion → graceful fallback (per §6A.E final
        # failure + §6A.F shape).
        return AIResponse(
            parsed=_fallback_parsed(ctx.workload, reason="guardrail"),
            raw_response=raw_response,
            cost_inr=cost_inr_total,
            layer2_retries=layer2_retries,
            trace_id=trace_id,
        )
    return AIResponse(
        parsed=parsed,
        raw_response=raw_response,
        cost_inr=cost_inr_total,
        layer2_retries=layer2_retries,
        trace_id=trace_id,
    )


# ── Helpers ────────────────────────────────────────────────────────────────
def _validate_workload_args(
    workload: Workload, rendered_by: str, image_bytes: bytes | None
) -> None:
    """Catch caller errors before consuming budget.

    Raises :class:`ValueError` for shape mismatches; this is a developer
    error path (the consumer module mis-coded the call), NOT a runtime
    Gemini failure that the graceful fallback handles.
    """
    if workload == "watermark" and image_bytes is None:
        raise ValueError(
            "ai_ops.client.call_gemini(workload='watermark') requires image_bytes"
        )
    if workload != "watermark" and image_bytes is not None:
        raise ValueError(
            f"ai_ops.client.call_gemini(workload={workload!r}) must NOT receive "
            f"image_bytes (only watermark is multimodal)"
        )
    if workload == "watermark" and rendered_by != "vision":
        raise ValueError(
            f"prompt for workload='watermark' must declare RENDERED_BY='vision' "
            f"(got {rendered_by!r})"
        )
    if workload != "watermark" and rendered_by != "text":
        raise ValueError(
            f"prompt for workload={workload!r} must declare RENDERED_BY='text' "
            f"(got {rendered_by!r})"
        )


def _estimate_prompt_tokens(template: str, prompt_vars: dict[str, Any]) -> int:
    """Cheap heuristic for pre-call token estimate.

    Uses ~4 chars/token (gemini-2.5-flash typical).  Conservative ceiling
    by treating substituted values as full-length strings.
    """
    estimated_chars = len(template)
    for value in prompt_vars.values():
        estimated_chars += len(str(value))
    # Round up to the nearest 100 tokens.
    return max(100, ((estimated_chars // 4) // 100 + 1) * 100)


async def _emit_fallback_trace(
    ctx: AICallContext,
    prompt_id: str,
    *,
    reason: str,
    trace_id: str,
) -> None:
    """Emit a LangFuse trace tagged with the fallback reason.

    Drop-on-failure: :mod:`adapters.langfuse` already drops on failure
    with a WARNING per §6.F.
    """
    await langfuse_adapter.trace(
        name=f"ai_ops.{ctx.workload}.fallback",
        input={"prompt_id": prompt_id, "fallback_reason": reason},
        output={"fallback_offered": True},
        metadata={"locale": ctx.locale, "fallback_reason": reason},
        user_id=ctx.user_id,
        trace_id=trace_id,
    )


__all__ = [
    "AICallContext",
    "AIResponse",
    "call_gemini",
]


# Defensive: silence unused-import lint for the local helper if a future
# refactor removes the field(default_factory=...) pattern.
_ = field

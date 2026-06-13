"""adapters/gemini.py — raw Gemini 2.5 Flash transport wrapper (§6.B).

Two public methods: :func:`generate_text` (LLM completion) and
:func:`generate_vision` (multimodal image+prompt).  Transport-level retry
only — 3 retries with exponential backoff (1s / 4s / 16s) on connection
errors, idempotent 5xx, and 429.

This adapter intentionally has NO knowledge of:
  * cost tracking (§6A.B owns this)
  * LangFuse trace egress (§6A wraps this; ``adapters/langfuse`` does the transport)
  * the 3-layer guardrail (§6A.D owns Layer 1; §6A.E owns Layer 2 hook)
  * prompt-registry lookup or versioning (§6A.G owns this)
  * which workload is calling (Smart Picker / Auto-fill / Watermark)
  * domain knowledge of any kind

Consumed ONLY by ``app.ai_ops.client`` per the §3.G locked boundary rule.
Domain modules call ``ai_ops.client.call_gemini(...)`` — never the adapter
directly.  §19 import-linter enforces this.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as gcore_exc

from app.adapters import GeminiAdapterError
from app.shared.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeminiResponse:
    """Locked envelope per §6.B.

    Attributes:
        text: Generated text content.
        input_tokens: Prompt token count from ``usage_metadata``.
        output_tokens: Candidate (response) token count.
        finish_reason: SDK-native finish reason string (e.g. ``"STOP"``).
        raw: SDK-native debug payload — NEVER serialised to API responses.
    """

    text: str
    input_tokens: int
    output_tokens: int
    finish_reason: str
    raw: dict


# ── Lazy singleton state ───────────────────────────────────────────────────
# ``genai.configure(api_key=...)`` is a process-wide side effect; we call it
# once on first model construction.  Models themselves are cached per-name
# so the same ``GenerativeModel`` instance is reused for every call.
_models: dict[str, "genai.GenerativeModel"] = {}
_configured: bool = False
_init_lock: asyncio.Lock | None = None


def _get_init_lock() -> asyncio.Lock:
    """Lazy lock construction — bound to whichever loop first hits the path."""
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


async def _get_model(model_name: str) -> "genai.GenerativeModel":
    """Lazy model factory; thread-safe via :func:`_get_init_lock`."""
    global _configured
    cached = _models.get(model_name)
    if cached is not None:
        return cached
    async with _get_init_lock():
        if not _configured:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            _configured = True
        if model_name not in _models:
            _models[model_name] = genai.GenerativeModel(model_name)
    return _models[model_name]


# ── Retry policy (§6.B locked triple) ──────────────────────────────────────
_RETRY_DELAYS_S: tuple[float, ...] = (1.0, 4.0, 16.0)
"""Locked at 3 retries with backoff (1s, 4s, 16s) per §6.B."""

_RETRYABLE_SDK_EXC: tuple[type[BaseException], ...] = (
    gcore_exc.ServiceUnavailable,    # 503
    gcore_exc.InternalServerError,   # 500
    gcore_exc.GatewayTimeout,        # 504
    gcore_exc.TooManyRequests,       # 429
    gcore_exc.DeadlineExceeded,
    ConnectionError,
    asyncio.TimeoutError,
)


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, _RETRYABLE_SDK_EXC)


# ── Public API ─────────────────────────────────────────────────────────────
async def generate_text(
    prompt: str,
    *,
    model: str | None = None,
    response_mime_type: str | None = None,
    max_output_tokens: int | None = None,
    temperature: float = 0.0,
) -> GeminiResponse:
    """LLM text completion.  See §6.B locked signature.

    ``temperature`` defaults to 0.0 per the F3 prompt-level guardrail
    locked in §6A — deterministic output is the AI-track baseline; any
    workload that wants stochastic output overrides via ``ai_ops/``, not
    here.
    """
    return await _generate(
        prompt,
        image_bytes=None,
        image_mime_type=None,
        model=model or settings.GEMINI_MODEL,
        response_mime_type=response_mime_type,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )


async def generate_vision(
    prompt: str,
    image_bytes: bytes,
    image_mime_type: str = "image/jpeg",
    *,
    model: str | None = None,
    max_output_tokens: int | None = None,
    temperature: float = 0.0,
) -> GeminiResponse:
    """Multimodal image+prompt completion.  See §6.B locked signature."""
    return await _generate(
        prompt,
        image_bytes=image_bytes,
        image_mime_type=image_mime_type,
        model=model or settings.GEMINI_MODEL,
        response_mime_type=None,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )


# ── Core retry loop ────────────────────────────────────────────────────────
async def _generate(
    prompt: str,
    *,
    image_bytes: bytes | None,
    image_mime_type: str | None,
    model: str,
    response_mime_type: str | None,
    max_output_tokens: int | None,
    temperature: float,
) -> GeminiResponse:
    """Retry loop wrapping :func:`_call_sdk`.  Internal — tests mock ``_call_sdk``.

    Retries: 3 attempts with backoff (1s, 4s, 16s) on transient SDK errors.
    Non-retryable errors (auth, malformed request, content-blocked safety
    filter) raise :class:`GeminiAdapterError` immediately.  Retry exhaustion
    also raises :class:`GeminiAdapterError`.  Never returns an empty / partial
    :class:`GeminiResponse` on error.
    """
    gen_config: dict[str, Any] = {"temperature": temperature}
    if max_output_tokens is not None:
        gen_config["max_output_tokens"] = max_output_tokens
    if response_mime_type is not None:
        gen_config["response_mime_type"] = response_mime_type

    last_exc: BaseException | None = None
    for attempt in range(len(_RETRY_DELAYS_S) + 1):
        try:
            raw = await _call_sdk(
                model_name=model,
                prompt=prompt,
                image_bytes=image_bytes,
                image_mime_type=image_mime_type,
                generation_config=gen_config,
            )
            return _envelope(raw)
        except Exception as exc:
            last_exc = exc
            retryable = _is_retryable(exc)
            if not retryable or attempt == len(_RETRY_DELAYS_S):
                logger.warning(
                    "gemini.generate failed (attempt=%d retryable=%s exc=%r)",
                    attempt + 1,
                    retryable,
                    exc,
                )
                raise GeminiAdapterError(
                    detail=f"Gemini call failed: {type(exc).__name__}"
                ) from exc
            delay = _RETRY_DELAYS_S[attempt]
            logger.info(
                "gemini.generate transient (attempt=%d, retry in %.1fs, exc=%r)",
                attempt + 1,
                delay,
                exc,
            )
            await asyncio.sleep(delay)

    # Defensive — the loop above always returns or raises; this is unreachable.
    raise GeminiAdapterError(detail="Gemini retry exhaustion") from last_exc


async def _call_sdk(
    *,
    model_name: str,
    prompt: str,
    image_bytes: bytes | None,
    image_mime_type: str | None,
    generation_config: dict[str, Any],
) -> Any:
    """Single SDK invocation.  Test mock target.

    The SDK call returns a ``GenerateContentResponse`` object whose
    attributes are read by :func:`_envelope`.  Tests substitute this
    function with a mock that yields a duck-typed response.
    """
    model = await _get_model(model_name)
    if image_bytes is None:
        contents: list[Any] = [prompt]
    else:
        contents = [
            prompt,
            {"mime_type": image_mime_type or "image/jpeg", "data": image_bytes},
        ]
    return await model.generate_content_async(
        contents, generation_config=generation_config
    )


def _envelope(raw: Any) -> GeminiResponse:
    """Defensive parser from SDK response → :class:`GeminiResponse`.

    Missing attributes (older SDK versions, partial responses) degrade
    to empty strings and zero token counts rather than raising.
    """
    text = getattr(raw, "text", "") or ""
    usage = getattr(raw, "usage_metadata", None)
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)

    candidates = getattr(raw, "candidates", None) or []
    finish_reason = ""
    if candidates:
        fr = getattr(candidates[0], "finish_reason", None)
        if fr is not None:
            finish_reason = str(getattr(fr, "name", fr))

    raw_dict: dict[str, Any] = {
        "text": text,
        "finish_reason": finish_reason,
        "usage": {"input": input_tokens, "output": output_tokens},
    }
    return GeminiResponse(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        finish_reason=finish_reason,
        raw=raw_dict,
    )


# ── Test helpers ───────────────────────────────────────────────────────────
def _reset_for_testing() -> None:
    """Reset module-level singleton state.  Called from test fixtures only.

    Required because ``asyncio.Lock`` is bound to the loop that first
    awaits it.  Test functions running in fresh loops (or after a session
    loop dies) must drop the lock before re-using the adapter.
    """
    global _configured, _init_lock
    _models.clear()
    _configured = False
    _init_lock = None

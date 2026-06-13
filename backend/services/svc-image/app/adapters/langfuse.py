"""adapters/langfuse.py — observability trace egress (§6.F).

Async fire-and-forget trace egress to LangFuse.

LOCKED CONTRACT (§6.F + §1.E)
-----------------------------
Observability MUST NOT block the business path.  Both public methods —
:func:`trace` and :func:`score` — adhere strictly to:

  * NEVER raise.  Every exception is caught and logged via
    ``logger.warning(...)``.  This is the second locked exception to the
    §6.G typed-exception pattern; :class:`LangfuseAdapterError` is
    defined in ``adapters/__init__.py`` for V1.5 surface compatibility
    but V1 code paths do not raise it.
  * Drop-on-failure with a single WARNING log per dropped event.
  * Degrade to a complete no-op (no network egress, no error) when
    LangFuse credentials are missing at startup.  A single one-time
    WARNING is logged when this happens: ``"langfuse credentials missing
    — trace egress disabled"``.

Decision flag D1 — httpx direct, no SDK
---------------------------------------
V1 uses ``httpx`` direct POST to ``{LANGFUSE_HOST}/api/public/ingestion``
rather than the official ``langfuse`` Python SDK.  Rationale:

  * No new dependency in ``requirements.txt`` — ``httpx`` is already pinned.
  * Fire-and-forget semantics make the SDK's batching value moot for V1
    AI volume; per-call POST overhead is acceptable (LangFuse free-tier
    quotas accommodate the V1 envelope per ``MVP_ARCH §8``).
  * SDK reintroduction is a single-file change in V1.5 if batching becomes
    operationally necessary; the adapter surface is stable.

FLAGGED for master review — escalate if the SDK is preferred.

Cross-section integration
-------------------------
Consumed ONLY by ``app.ai_ops.client``.  Domain modules NEVER import
``adapters.langfuse`` directly — every AI call site flows through
``ai_ops/client.py``, which fires the trace as the final step after the
Gemini call returns (success or failure).
"""

from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx

from app.shared.config import settings

logger = logging.getLogger(__name__)


_INGESTION_PATH = "/api/public/ingestion"
"""LangFuse public ingestion endpoint — accepts batched events."""

_REQUEST_TIMEOUT_S = 5.0
"""Short timeout — fire-and-forget MUST NEVER block the business path."""


# ── Lazy singleton client ──────────────────────────────────────────────────
_client: httpx.AsyncClient | None = None
_init_lock: asyncio.Lock | None = None
_creds_warned: bool = False


def _get_init_lock() -> asyncio.Lock:
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


def _has_creds() -> bool:
    """Return True iff both public + secret keys are configured.

    On the first call that finds credentials missing, log a single
    WARNING ("langfuse credentials missing — trace egress disabled").
    Subsequent calls return False silently.
    """
    global _creds_warned
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        if not _creds_warned:
            logger.warning("langfuse credentials missing — trace egress disabled")
            _creds_warned = True
        return False
    return True


async def _get_client() -> httpx.AsyncClient:
    """Lazy ``httpx.AsyncClient`` — single instance per process.

    Basic-auth header is baked in at construction time (LangFuse uses
    ``public_key:secret_key`` base64-encoded as the basic-auth user/pass).
    """
    global _client
    if _client is not None:
        return _client
    async with _get_init_lock():
        if _client is None:
            credentials = (
                f"{settings.LANGFUSE_PUBLIC_KEY}:{settings.LANGFUSE_SECRET_KEY}"
            ).encode("utf-8")
            auth_token = base64.b64encode(credentials).decode("ascii")
            _client = httpx.AsyncClient(
                base_url=settings.LANGFUSE_HOST,
                timeout=_REQUEST_TIMEOUT_S,
                headers={
                    "Authorization": f"Basic {auth_token}",
                    "Content-Type": "application/json",
                },
            )
    return _client


# ── Public API ─────────────────────────────────────────────────────────────
async def trace(
    name: str,
    input: dict,
    output: dict,
    *,
    metadata: dict | None = None,
    user_id: UUID | None = None,
    trace_id: str | None = None,
) -> None:
    """Fire a trace event.  See §6.F locked signature.

    NEVER raises — drop-on-failure with WARNING log.  Returns None
    unconditionally (success or failure).

    Args:
        name: Trace name, e.g. ``"smart_picker.suggest"``.
        input: Request envelope (prompt + parameters).  Free-form dict.
        output: Response envelope (text + token counts).  Free-form dict.
        metadata: Free-form metadata dict.
        user_id: Optional seller UUID for filtering in the LangFuse UI.
        trace_id: Caller-provided ID for chaining multi-step traces.
            If ``None``, the adapter generates a fresh UUID.
    """
    if not _has_creds():
        return
    event_body = {
        "id": trace_id or str(uuid.uuid4()),
        "name": name,
        "input": input,
        "output": output,
        "metadata": metadata or {},
        "userId": str(user_id) if user_id is not None else None,
    }
    batch_envelope = {
        "batch": [
            {
                "id": str(uuid.uuid4()),
                "timestamp": _now_iso(),
                "type": "trace-create",
                "body": event_body,
            }
        ]
    }
    await _emit(batch_envelope, event_kind="trace")


async def score(
    trace_id: str,
    name: str,
    value: float,
) -> None:
    """Fire a score event.  See §6.F locked signature.

    NEVER raises — drop-on-failure with WARNING log.  Returns None
    unconditionally.

    Args:
        trace_id: ID of the trace this score attaches to.
        name: Score name, e.g. ``"enum_validation_passed"``.
        value: 0.0 / 1.0 for boolean scores; eval rubric uses [0.0, 1.0].
    """
    if not _has_creds():
        return
    event_body = {
        "id": str(uuid.uuid4()),
        "traceId": trace_id,
        "name": name,
        "value": float(value),
    }
    batch_envelope = {
        "batch": [
            {
                "id": str(uuid.uuid4()),
                "timestamp": _now_iso(),
                "type": "score-create",
                "body": event_body,
            }
        ]
    }
    await _emit(batch_envelope, event_kind="score")


# ── Internal egress + helpers ──────────────────────────────────────────────
async def _emit(body: dict[str, Any], *, event_kind: str) -> None:
    """Drop-on-failure POST.  NEVER raises.

    Catches every Exception (including ``httpx.HTTPError`` subclasses,
    ``TypeError`` from a misbuilt body, and unexpected RuntimeError).
    Logs a single WARNING per dropped event and returns.
    """
    try:
        client = await _get_client()
        resp = await client.post(_INGESTION_PATH, json=body)
        if resp.status_code >= 300:
            logger.warning(
                "langfuse %s egress dropped: http %d body=%s",
                event_kind,
                resp.status_code,
                resp.text[:200],
            )
    except Exception as exc:
        logger.warning("langfuse %s egress dropped: %r", event_kind, exc)


def _now_iso() -> str:
    """RFC 3339 / ISO 8601 UTC timestamp for LangFuse batch events."""
    return datetime.now(timezone.utc).isoformat()


# ── Test helpers ───────────────────────────────────────────────────────────
def _reset_for_testing() -> None:
    """Reset module singletons + creds-warned latch.  Called from fixtures only."""
    global _client, _init_lock, _creds_warned
    _client = None
    _init_lock = None
    _creds_warned = False

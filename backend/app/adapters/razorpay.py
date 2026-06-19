"""adapters/razorpay.py — Razorpay transport wrapper (§6.E + §6.G).

Two surfaces live in this file:

* The **V1 LOCKED** synchronous HMAC helper :func:`verify_webhook_signature`
  (signature verification; see the two LOCKED-EXCEPTION paragraphs below).
  It stays sync, ``bool``-returning, and never raises.
* The **V1.5** async subscription / order / customer surface
  (:func:`create_subscription`, :func:`create_order`, :func:`fetch_subscription`,
  :func:`cancel_subscription`, :func:`update_subscription`, :func:`get_customer`),
  added per ``RAZORPAY_INTEGRATION_SPEC §5`` + founder ruling F9 (official
  Razorpay Python SDK).  The official SDK is **synchronous** (``requests``-based),
  so each async method wraps the sync SDK call in :func:`asyncio.to_thread`,
  EXACTLY mirroring the ``adapters/gcs.py`` pattern (which wraps the sync
  ``google-cloud-storage`` SDK).  Vendor shapes NEVER leak past this file — the
  methods return the frozen dataclasses defined below, never raw SDK dicts
  (Philosophy M10 / §6).  Transport / non-2xx failures are re-raised as
  :class:`RazorpayAdapterError`; raw ``razorpay.errors.*`` / ``requests``
  exceptions never escape this boundary (§6.G).

LOCKED EXCEPTION #1 (§6.G "all adapters async")
-----------------------------------------------
:func:`verify_webhook_signature` is **synchronous** because HMAC-SHA256
verification is CPU-bound and microsecond-scale; an ``async def`` wrapper
would add event-loop overhead with no I/O benefit.  See §6.E rationale.
It stays sync even though the V1.5 surface below is async.

LOCKED EXCEPTION #2 (§6.G "raise typed errors")
-----------------------------------------------
:func:`verify_webhook_signature` returns ``bool``.  Invalid signature
returns ``False``; malformed input returns ``False``.  It NEVER raises.
The caller (the webhook router → ``iam.service.capture_razorpay_webhook``)
raises :class:`WebhookSignatureInvalidError` (401) on a ``False`` return.
The V1.5 async methods below DO follow the §6.G typed-exception pattern —
they raise :class:`RazorpayAdapterError` on failure.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from dataclasses import dataclass, field

import razorpay
from razorpay.errors import (
    BadRequestError,
    GatewayError,
    ServerError,
    SignatureVerificationError,
)

from app.adapters import RazorpayAdapterError
from app.shared.config import settings

logger = logging.getLogger(__name__)


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    *,
    secret: str | None = None,
) -> bool:
    """Verify Razorpay webhook signature.

    HMAC-SHA256 of ``payload`` with ``secret`` is compared constant-time
    against ``signature`` (the value of the ``X-Razorpay-Signature``
    request header).

    Args:
        payload: Raw request body — bytes, NOT json-parsed.  Parsing
            mutates whitespace and breaks the HMAC.
        signature: Hex-encoded signature from the request header.
        secret: Override the configured ``RAZORPAY_WEBHOOK_SECRET``.

    Returns:
        True if the signature matches; False otherwise.

    NEVER raises (locked exception #2).  Returns ``False`` on:
      * non-bytes payload (defensive)
      * empty / non-string signature (defensive)
      * actual signature mismatch
      * any HMAC compare exception (defensive)
    """
    if not isinstance(payload, (bytes, bytearray)):
        logger.warning(
            "razorpay.verify_webhook_signature: non-bytes payload type=%s",
            type(payload).__name__,
        )
        return False
    if not isinstance(signature, str) or not signature:
        return False

    key = (secret or settings.RAZORPAY_WEBHOOK_SECRET).encode("utf-8")
    expected = hmac.new(key, bytes(payload), hashlib.sha256).hexdigest()

    try:
        return hmac.compare_digest(expected, signature)
    except Exception as exc:
        # Defensive — ``hmac.compare_digest`` accepts str-vs-str or bytes-vs-bytes
        # only; any TypeError here is signal we have malformed input upstream.
        logger.warning(
            "razorpay.verify_webhook_signature compare error: %r", exc
        )
        return False


# ═══════════════════════════════════════════════════════════════════════════
# V1.5 async surface — Subscriptions / Orders / Customers (RAZORPAY_SPEC §5).
#
# Everything below this line is the V1.5 addition.  It does NOT touch the
# LOCKED ``verify_webhook_signature`` above.  Each method wraps the sync
# official Razorpay SDK via ``asyncio.to_thread`` (GCS pattern) and raises
# :class:`RazorpayAdapterError` on failure (§6.G typed-exception pattern).
# ═══════════════════════════════════════════════════════════════════════════


# ── Frozen return dataclasses (vendor shapes never leak — §6 / M10) ─────────
@dataclass(frozen=True)
class RazorpaySubscription:
    """Stable subscription shape returned to the service layer.

    Attributes:
        id: Razorpay subscription id (``sub_...``).
        status: Razorpay lifecycle status (``created``/``authenticated``/
            ``active``/``pending``/``halted``/``cancelled``/``completed``).
        plan_id: The Razorpay plan id the subscription is bound to.
        current_end: Period end as Razorpay epoch SECONDS, or ``None`` when
            absent.  The service layer converts to a UTC ``datetime`` when
            writing ``subscriptions.current_period_end``.
        short_url: Hosted-checkout URL the FE widget opens; ``None`` if absent.
        notes: Free-form ``notes`` dict echoed back by Razorpay (carries
            ``{user_id, tier}`` we set at create time).
    """

    id: str
    status: str
    plan_id: str
    current_end: int | None = None
    short_url: str | None = None
    notes: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RazorpayOrder:
    """Stable one-time Order shape (LTD path).

    Attributes:
        id: Razorpay order id (``order_...``).
        amount: Amount in PAISE (Razorpay-native; F9).
        currency: ISO-4217 code (always ``INR`` for V1.5).
        status: Razorpay order status (``created``/``attempted``/``paid``).
        receipt: The receipt string we passed at create time; ``None`` if absent.
    """

    id: str
    amount: int
    currency: str
    status: str
    receipt: str | None = None


@dataclass(frozen=True)
class RazorpayCustomer:
    """Stable customer shape (KYC / reconciliation lookup).

    PII (``email``/``contact``) is carried only because ``get_customer`` needs
    it; the service MUST NOT log these fields (§9).
    """

    id: str
    email: str | None = None
    contact: str | None = None


# ── Lazy singleton SDK client (mirrors gcs.py) ──────────────────────────────
_client: razorpay.Client | None = None
_init_lock: asyncio.Lock | None = None

#: Razorpay SDK errors that map to our 502 envelope.  ``BadRequestError`` =
#: Razorpay rejected our request (bad plan_id etc.); the rest = transport /
#: gateway / server failure.  ``SignatureVerificationError`` is included for
#: completeness (the async surface does not verify signatures, but the SDK base
#: error tree includes it).
_SDK_ERRORS: tuple[type[BaseException], ...] = (
    BadRequestError,
    GatewayError,
    ServerError,
    SignatureVerificationError,
)


def _get_init_lock() -> asyncio.Lock:
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


async def _get_client() -> razorpay.Client:
    """Lazy Razorpay SDK client — single instance per process.

    Auth sourced from ``settings`` only (never the process environment
    directly) per §6.G / the §19 import-linter adapter rule.
    """
    global _client
    if _client is not None:
        return _client
    async with _get_init_lock():
        if _client is None:
            client = await asyncio.to_thread(
                razorpay.Client,
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            )
            # Request attribution (best-effort; never fatal).
            try:
                client.set_app_details({"title": "MeeSell", "version": "1.5"})
            except Exception as exc:  # noqa: BLE001 — attribution is optional
                logger.debug("razorpay.set_app_details skipped: %r", exc)
            _client = client
    return _client


def _to_int_or_none(value: object) -> int | None:
    """Coerce a Razorpay epoch-seconds field to ``int | None`` defensively."""
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _map_subscription(raw: dict) -> RazorpaySubscription:
    """Map a raw SDK subscription dict → :class:`RazorpaySubscription`."""
    return RazorpaySubscription(
        id=str(raw.get("id", "")),
        status=str(raw.get("status", "")),
        plan_id=str(raw.get("plan_id", "")),
        current_end=_to_int_or_none(raw.get("current_end")),
        short_url=raw.get("short_url"),
        notes=dict(raw.get("notes") or {}),
    )


def _map_order(raw: dict) -> RazorpayOrder:
    """Map a raw SDK order dict → :class:`RazorpayOrder`."""
    return RazorpayOrder(
        id=str(raw.get("id", "")),
        amount=int(raw.get("amount", 0)),
        currency=str(raw.get("currency", "INR")),
        status=str(raw.get("status", "")),
        receipt=raw.get("receipt"),
    )


def _map_customer(raw: dict) -> RazorpayCustomer:
    """Map a raw SDK customer dict → :class:`RazorpayCustomer`."""
    return RazorpayCustomer(
        id=str(raw.get("id", "")),
        email=raw.get("email"),
        contact=raw.get("contact"),
    )


# ── Public V1.5 async methods (§5.2) ────────────────────────────────────────
async def create_subscription(
    *,
    plan_id: str,
    customer_notify: bool = True,
    total_count: int | None = None,
    notes: dict | None = None,
) -> RazorpaySubscription:
    """Create a recurring subscription (Razorpay Subscriptions API).

    The adapter is plan-agnostic (D-B): the caller passes an opaque
    ``plan_id``; the plan→price→tier map lives in Wave-3 / pricing config.

    Args:
        plan_id: Razorpay plan id (``plan_...``) for the target tier×interval.
        customer_notify: Whether Razorpay sends its own checkout email.
        total_count: Billing-cycle count; ``None`` → omit (open-ended).
        notes: Free-form metadata echoed back on webhooks — carries
            ``{user_id, tier}`` so the webhook router can resolve the user.

    Returns:
        :class:`RazorpaySubscription` with ``id`` + ``short_url`` for checkout.

    Raises:
        RazorpayAdapterError: On any SDK / transport failure (502 envelope).
    """
    body: dict = {
        "plan_id": plan_id,
        "customer_notify": 1 if customer_notify else 0,
    }
    if total_count is not None:
        body["total_count"] = total_count
    if notes:
        body["notes"] = notes

    client = await _get_client()
    try:
        raw = await asyncio.to_thread(client.subscription.create, body)
    except _SDK_ERRORS as exc:
        logger.warning("razorpay.create_subscription failed: %r", exc)
        raise RazorpayAdapterError(
            detail=f"Razorpay create_subscription failed: {type(exc).__name__}"
        ) from exc
    return _map_subscription(raw)


async def create_order(
    *,
    amount: int,
    currency: str = "INR",
    receipt: str,
    notes: dict | None = None,
) -> RazorpayOrder:
    """Create a one-time Order (LTD purchase path; Razorpay Orders API).

    Args:
        amount: Amount in PAISE (F9 — never rupees, never float).
        currency: ISO-4217 code; ``INR`` for V1.5.
        receipt: Idempotency-friendly receipt string the caller controls.
        notes: Free-form metadata (e.g. ``{user_id, tier: 'ltd'}``).

    Raises:
        RazorpayAdapterError: On any SDK / transport failure.
    """
    body: dict = {"amount": amount, "currency": currency, "receipt": receipt}
    if notes:
        body["notes"] = notes

    client = await _get_client()
    try:
        raw = await asyncio.to_thread(client.order.create, body)
    except _SDK_ERRORS as exc:
        logger.warning("razorpay.create_order failed receipt=%s: %r", receipt, exc)
        raise RazorpayAdapterError(
            detail=f"Razorpay create_order failed: {type(exc).__name__}"
        ) from exc
    return _map_order(raw)


async def fetch_subscription(sub_id: str) -> RazorpaySubscription:
    """Pull authoritative subscription state (reconciliation — Wave 4).

    Raises:
        RazorpayAdapterError: On any SDK / transport failure.
    """
    client = await _get_client()
    try:
        raw = await asyncio.to_thread(client.subscription.fetch, sub_id)
    except _SDK_ERRORS as exc:
        logger.warning("razorpay.fetch_subscription failed sub=%s: %r", sub_id, exc)
        raise RazorpayAdapterError(
            detail=f"Razorpay fetch_subscription failed: {type(exc).__name__}"
        ) from exc
    return _map_subscription(raw)


async def cancel_subscription(
    sub_id: str,
    *,
    cancel_at_cycle_end: bool = True,
) -> RazorpaySubscription:
    """Cancel a subscription.  Default cancel-at-cycle-end (§3.6).

    Args:
        sub_id: Razorpay subscription id.
        cancel_at_cycle_end: ``True`` (default) keeps entitlement until period
            end; ``False`` cancels immediately.

    Raises:
        RazorpayAdapterError: On any SDK / transport failure.
    """
    client = await _get_client()
    try:
        raw = await asyncio.to_thread(
            client.subscription.cancel,
            sub_id,
            {"cancel_at_cycle_end": 1 if cancel_at_cycle_end else 0},
        )
    except _SDK_ERRORS as exc:
        logger.warning("razorpay.cancel_subscription failed sub=%s: %r", sub_id, exc)
        raise RazorpayAdapterError(
            detail=f"Razorpay cancel_subscription failed: {type(exc).__name__}"
        ) from exc
    return _map_subscription(raw)


async def update_subscription(
    sub_id: str,
    *,
    plan_id: str,
    schedule_change_at: str = "cycle_end",
) -> RazorpaySubscription:
    """Change the plan on a subscription (upgrade / downgrade — §3.3/§3.4).

    F4: upgrade lands immediately; downgrade is scheduled at cycle end
    (``schedule_change_at="cycle_end"``, the default).

    Raises:
        RazorpayAdapterError: On any SDK / transport failure.
    """
    client = await _get_client()
    try:
        # SDK exposes the plan-change PATCH as ``subscription.edit`` (the
        # Razorpay REST "update subscription" endpoint).  There is no
        # ``subscription.update`` method in the v1.4.x SDK.
        raw = await asyncio.to_thread(
            client.subscription.edit,
            sub_id,
            {"plan_id": plan_id, "schedule_change_at": schedule_change_at},
        )
    except _SDK_ERRORS as exc:
        logger.warning("razorpay.update_subscription failed sub=%s: %r", sub_id, exc)
        raise RazorpayAdapterError(
            detail=f"Razorpay update_subscription failed: {type(exc).__name__}"
        ) from exc
    return _map_subscription(raw)


async def get_customer(customer_id: str) -> RazorpayCustomer:
    """Fetch a customer (KYC / reconciliation lookup).

    Raises:
        RazorpayAdapterError: On any SDK / transport failure.
    """
    client = await _get_client()
    try:
        raw = await asyncio.to_thread(client.customer.fetch, customer_id)
    except _SDK_ERRORS as exc:
        logger.warning("razorpay.get_customer failed: %r", exc)
        raise RazorpayAdapterError(
            detail=f"Razorpay get_customer failed: {type(exc).__name__}"
        ) from exc
    return _map_customer(raw)


# ── Test helper ─────────────────────────────────────────────────────────────
def _reset_for_testing() -> None:
    """Reset module singletons.  Called from test fixtures only."""
    global _client, _init_lock
    _client = None
    _init_lock = None

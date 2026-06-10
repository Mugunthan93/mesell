"""``category`` service layer — 8 PUBLIC async methods per §9.C (LOCKED 2026-06-05).

Public surface (8 methods)::

    # 5 endpoint-mirror — return JSON-serialisable dicts (router validates)
    suggest_categories(user_id, q, db) -> dict     # SuggestResponse shape
    browse_categories(q, super_id, limit, offset, db) -> dict  # BrowseResponse
    get_category_tree(db) -> dict                  # CategoryTreeResponse shape
    fetch_schema(category_id, db) -> dict          # §5A.B envelope verbatim
    get_field_enum(category_id, field_name, db) -> dict  # FieldEnumResponse

    # 3 cross-module
    get_commission(category_id, db) -> Decimal           # called by pricing
    list_super_categories(db) -> list[SuperCategoryInfo] # called by customer
    assert_category_exists(category_id, db) -> None      # called by catalog

Note: the 5 endpoint-mirror methods return plain ``dict`` payloads —
the router (owned by api-routes-builder) wraps each in
``XxxResponse.model_validate(payload)`` when constructing the HTTP
response.  This decouples the service from the Pydantic schema cycle.

Cache keys (per §9.I)::

    smart_picker:{sha256(q).hexdigest()}     TTL  900 s
    browse:{sha256(q|super_id|limit|offset)} TTL  300 s
    category_tree                            TTL 3600 s + ETag
    schema:{category_id}                     TTL 3600 s + ETag
    field_enum:{category_id}:{field_name}    TTL 3600 s  single_flight=True (§6.8)
    super_category_list                      TTL 3600 s

All keys are version-prefixed ``meesell:v{cache_version}:`` by
:func:`app.core.cache.get_or_set` per §4.D + §6.4 — quarterly Meesho
refresh bumps CACHE_VERSION env var to invalidate every cached entry
atomically.

Tenancy (§4.C)
--------------
This module owns READ access to the GLOBAL ``categories`` /
``templates`` / ``field_enum_values`` tables.  No ``user_id`` scoping
is applied; the repository carries no tenancy column.  Plan-guard
hourly counters DO use ``user_id`` (per §9.B.1 + §4.E) — but that is a
separate gate that fires BEFORE the read.

AI seam (§9.A)
--------------
The Smart Picker path consumes :mod:`app.modules.category.picker` (AI
track) and :func:`app.ai_ops.client.call_gemini` (per §6A.C).  This
module NEVER imports ``app.adapters.gemini`` directly per §3.G + §16
import-linter Contract 2.

Graceful fallback contract (per §9.B.1 + §6A.F)
-----------------------------------------------
:func:`suggest_categories` MUST return ``SuggestResponse(suggestions=[],
fallback_offered=True)`` with HTTP 200 — never raise — when any of:

* :class:`BudgetExceededError` is raised inside ``call_gemini`` (V1.5
  surface; V1's ``call_gemini`` catches it internally and returns
  ``AIResponse(parsed.fallback_offered=True)`` instead).
* ``AIResponse.parsed.get("fallback_offered") is True`` (Layer 2 retry
  exhaustion path inside ``call_gemini``).
* Every returned ``category_id`` fails the existence guardrail
  (defensive: ``call_gemini`` already retries up to 2 times for invalid
  IDs; this is the final 200-with-fallback safety net).
"""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_ops import client as ai_client
from app.ai_ops.budget_cap import BudgetExceededError
from app.ai_ops.client import AICallContext
from app.core.cache import get_or_set
from app.core.plan_guard import enforce_plan_limit
from app.modules.category import picker, repository as category_repo
from app.modules.category.domain import SuperCategoryInfo
from app.modules.category.exceptions import (
    BrowseQueryInvalidError,
    CategoryNotFoundError,
    SuggestQueryInvalidError,
)
# NOTE: schemas.py is owned by api-routes-builder (parallel dispatch).  The
# service surface returns plain ``dict`` payloads + the §9.F domain
# dataclasses; the router calls ``SuggestResponse.model_validate(payload)``
# (etc.) when constructing the HTTP response.  This decouples service
# tests from the Pydantic schema generation cycle.

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Cache TTL constants
# ─────────────────────────────────────────────────────────────────────────────
_SUGGEST_TTL_SECONDS = 900       # 15 min  per §9.B.1
_BROWSE_TTL_SECONDS = 300        # 5  min  per §9.B.2
_TREE_TTL_SECONDS = 3600         # 1  h    per §9.B.3
_SCHEMA_TTL_SECONDS = 3600       # 1  h    per §9.B.4
_FIELD_ENUM_TTL_SECONDS = 3600   # 1  h    per §9.B.5
_SUPER_LIST_TTL_SECONDS = 3600   # 1  h    per §9.C

# Plan guard
_PLAN_RESOURCE_SMART_PICKER = "smart_picker_hourly"
_PLAN_FREE = "free"

# Smart Picker top-K
_SUGGEST_TOP_K = 5


# ─────────────────────────────────────────────────────────────────────────────
# Cache-key helpers
# ─────────────────────────────────────────────────────────────────────────────
def _suggest_cache_key(q: str) -> str:
    """``smart_picker:{sha256(q)}`` per §9.B.1.

    SHA-256 bounds the key length to 64 hex chars + 13-char prefix; the
    raw description could contain arbitrary characters that Valkey
    tolerates poorly.
    """
    digest = hashlib.sha256(q.encode("utf-8")).hexdigest()
    return f"smart_picker:{digest}"


def _browse_cache_key(
    q: str | None, super_id: str | None, limit: int, offset: int
) -> str:
    """``browse:{sha256(q|super_id|limit|offset)}`` per §9.B.2."""
    raw = f"{q or ''}|{super_id or ''}|{limit}|{offset}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"browse:{digest}"


def _schema_cache_key(category_id: UUID) -> str:
    """``schema:{category_id}`` per §9.B.4."""
    return f"schema:{category_id}"


def _field_enum_cache_key(category_id: UUID, field_name: str) -> str:
    """``field_enum:{category_id}:{field_name}`` per §9.B.5."""
    return f"field_enum:{category_id}:{field_name}"


# ─────────────────────────────────────────────────────────────────────────────
# Internal — fetch the tree (cached) as list[CategoryRow] dicts
# ─────────────────────────────────────────────────────────────────────────────
async def _fetch_tree_dicts(db: AsyncSession) -> list[dict[str, Any]]:
    """Cached read of the full category tree as JSON-serialisable dicts.

    The repository returns ``list[CategoryRow]`` (frozen dataclasses with
    UUID / Decimal fields); JSON-serialise via stringification so the
    Valkey cache layer's ``json.dumps`` path is happy.

    This is the SHARED read consumed by:
    * :func:`get_category_tree` (the §9.B.3 endpoint)
    * :func:`suggest_categories` (the §9.B.1 picker compression source)
    """

    async def _fetch() -> list[dict[str, Any]]:
        rows = await category_repo.fetch_category_tree(db)
        return [
            {
                "id": str(r.id),
                "meesho_leaf_id": r.meesho_leaf_id,
                "super_id": r.super_id,
                "super_name": r.super_name,
                "path": r.path,
                "leaf_name": r.leaf_name,
                "template_id": str(r.template_id),
                "commission_pct": (
                    str(r.commission_pct) if r.commission_pct is not None else None
                ),
            }
            for r in rows
        ]

    return await get_or_set(
        "category_tree",
        _fetch,
        ttl=_TREE_TTL_SECONDS,
        single_flight=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# §9.B.1 Smart Category Picker
# ─────────────────────────────────────────────────────────────────────────────
async def suggest_categories(
    user_id: UUID,
    q: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Smart Category Picker per §9.B.1.

    Pipeline:

    1. Validate ``q`` length (1..500 trimmed).  Raises
       :class:`SuggestQueryInvalidError` on violation.
    2. Plan-guard: ``smart_picker_hourly`` cap (100/h/user) per §4.E.
    3. Cache lookup (TTL 900 s, key
       ``smart_picker:{sha256(q).hexdigest()}``).
    4. On miss: load tree → ``picker.compress_tree`` → ``call_gemini(
       "smart_picker.v1", ...)``.
    5. Handle BOTH graceful-fallback paths (per dispatch criterion 7):
       a. ``BudgetExceededError`` raised → empty suggestions + flag.
       b. ``AIResponse.parsed.fallback_offered is True`` → same.
    6. Validate each AI-emitted ``category_id`` against the categories
       table (defensive final pass; ``call_gemini`` already retried).
    7. Enrich each surviving suggestion with super_id/super_name/path/
       leaf_name from the in-process tree.
    8. Apply ``picker.calibrate_confidence`` then ``picker.select_top_k(5)``.

    Returns the :class:`SuggestResponse` envelope.  HTTP 200 always —
    never raises a 5xx for AI failures.
    """
    # Step 1 — validate.
    trimmed = q.strip() if q is not None else ""
    if not (1 <= len(trimmed) <= 500):
        raise SuggestQueryInvalidError()

    # Step 2 — plan guard.  Raises PlanLimitExceededError (402) per §4.E.
    await enforce_plan_limit(
        user_id, _PLAN_FREE, _PLAN_RESOURCE_SMART_PICKER, requested=1
    )

    # Step 3+ — cache the FINAL response shape (deterministic per query
    # because §6A locks smart_picker temperature=0).
    async def _build() -> dict[str, Any]:
        return await _build_suggest_payload(user_id, trimmed, db)

    payload = await get_or_set(
        _suggest_cache_key(trimmed),
        _build,
        ttl=_SUGGEST_TTL_SECONDS,
        single_flight=False,
    )
    return payload


async def _build_suggest_payload(
    user_id: UUID,
    q: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Cache miss path for :func:`suggest_categories`.

    Returns a JSON-serialisable dict matching :class:`SuggestResponse`.
    """
    # Load + index the tree once.
    tree_dicts = await _fetch_tree_dicts(db)
    by_id: dict[str, dict[str, Any]] = {row["id"]: row for row in tree_dicts}

    # Compress + call AI.
    compressed = picker.compress_tree(tree_dicts, description=q)
    ctx = AICallContext(workload="smart_picker", user_id=user_id)

    try:
        ai_response = await ai_client.call_gemini(
            ctx,
            "smart_picker.v1",
            prompt_vars={"description": q, "compressed_tree": compressed},
        )
    except BudgetExceededError:
        # V1.5 surface: call_gemini might one day re-raise this.  Today it
        # catches internally and returns AIResponse with parsed
        # fallback_offered=True — but the dispatch criterion #7 asks us
        # to handle BOTH paths.
        logger.info(
            "category.suggest: BudgetExceededError raised through ai_ops — "
            "returning graceful fallback"
        )
        return {"suggestions": [], "fallback_offered": True}

    parsed = ai_response.parsed if isinstance(ai_response.parsed, dict) else {}
    if parsed.get("fallback_offered") is True:
        return {"suggestions": [], "fallback_offered": True}

    raw_suggestions = parsed.get("suggestions") or []
    if not isinstance(raw_suggestions, list) or not raw_suggestions:
        return {"suggestions": [], "fallback_offered": True}

    # Step 6 — defensive final validation against the categories table.
    # ai_ops already retried up to 2 times for invalid IDs — this is the
    # final 200-with-fallback safety net per §9.B.1 step 3.
    scored: list[dict[str, Any]] = []
    for raw in raw_suggestions:
        if not isinstance(raw, dict):
            continue
        category_id_raw = raw.get("category_id")
        if not category_id_raw:
            continue
        try:
            cid = UUID(str(category_id_raw))
        except (ValueError, TypeError):
            continue
        # Validate existence via the in-process tree (cheap) — if absent,
        # fall through to the DB roundtrip for a deterministic answer.
        tree_entry = by_id.get(str(cid))
        if tree_entry is None:
            exists = await category_repo.assert_category_exists_uncached(db, cid)
            if not exists:
                continue
            # Tree might be stale (1-hour TTL) — load directly from DB by
            # forcing a tree miss.  For V1 we just skip — the cache will
            # refresh on the next bump.
            continue

        confidence_raw = raw.get("confidence", 0.0)
        try:
            confidence_f = float(confidence_raw)
        except (TypeError, ValueError):
            confidence_f = 0.0

        calibrated = picker.calibrate_confidence(
            confidence_f, ai_response.layer2_retries
        )

        reasons_raw = raw.get("reasons") or []
        if isinstance(reasons_raw, list):
            reasons = [str(r) for r in reasons_raw]
        else:
            reasons = []

        scored.append(
            {
                "category_id": str(cid),
                "super_id": tree_entry["super_id"],
                "super_name": tree_entry["super_name"],
                "path": tree_entry["path"],
                "leaf_name": tree_entry["leaf_name"],
                "confidence": calibrated,
                "reasons": reasons,
            }
        )

    if not scored:
        # Every AI suggestion failed validation → graceful fallback.
        return {"suggestions": [], "fallback_offered": True}

    # Step 8 — top-K.  Picker enforces deterministic ordering.
    top_k = picker.select_top_k(scored, _SUGGEST_TOP_K)
    return {"suggestions": top_k, "fallback_offered": False}


# ─────────────────────────────────────────────────────────────────────────────
# §9.B.2 Manual Browse
# ─────────────────────────────────────────────────────────────────────────────
async def browse_categories(
    q: str | None,
    super_id: str | None,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Manual Browse per §9.B.2 — pg_trgm against the 3 GIN indexes.

    Cache per ``(q, super_id, limit, offset)`` tuple, TTL 5 min.
    """
    if not (1 <= limit <= 100) or offset < 0:
        raise BrowseQueryInvalidError()

    async def _fetch() -> dict[str, Any]:
        rows, total = await category_repo.search_via_trigram(
            db, q, super_id, limit, offset
        )
        results: list[dict[str, Any]] = []
        for row in rows:
            # Similarity is computed at the SQL layer but not propagated
            # back through `_orm_to_row`.  For V1 we report 0.0 — the
            # similarity ordering is preserved in the ORDER BY, which is
            # what consumers actually need.  Lifting `sim` end-to-end is
            # a §V1.5 refinement (would require widening the repository
            # return shape).
            results.append(
                {
                    "category_id": str(row.id),
                    "super_id": row.super_id,
                    "super_name": row.super_name,
                    "path": row.path,
                    "leaf_name": row.leaf_name,
                    "similarity": 0.0,
                }
            )
        return {
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    payload = await get_or_set(
        _browse_cache_key(q, super_id, limit, offset),
        _fetch,
        ttl=_BROWSE_TTL_SECONDS,
        single_flight=False,
    )
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# §9.B.3 Category Tree
# ─────────────────────────────────────────────────────────────────────────────
async def get_category_tree(db: AsyncSession) -> dict[str, Any]:
    """Full hierarchical category tree per §9.B.3.

    Cached GLOBAL TTL 1 h.  The router consumes the returned dict + reads
    :func:`app.core.cache.etag_for` on the JSON-serialised payload to set
    the response's ETag header.

    Return shape (mirrors §9.E ``CategoryTreeResponse``)::

        {
            "super_categories": [
                {
                    "super_id": str,
                    "super_name": str,
                    "leaves": [
                        {"category_id": str,
                         "super_id": str,
                         "super_name": str,
                         "path": str,
                         "leaf_name": str,
                         "similarity": float},
                        ...
                    ],
                },
                ...
            ],
        }
    """
    tree_dicts = await _fetch_tree_dicts(db)

    # In-Python group-by super_id assembly.
    groups: dict[str, dict[str, Any]] = {}
    for row in tree_dicts:
        super_id = row["super_id"]
        bucket = groups.setdefault(
            super_id,
            {
                "super_id": super_id,
                "super_name": row["super_name"],
                "leaves": [],
            },
        )
        bucket["leaves"].append(
            {
                "category_id": row["id"],
                "super_id": row["super_id"],
                "super_name": row["super_name"],
                "path": row["path"],
                "leaf_name": row["leaf_name"],
                "similarity": 0.0,
            }
        )
    # Sort outer dict deterministically.
    super_categories = [groups[k] for k in sorted(groups.keys())]
    return {"super_categories": super_categories}


# ─────────────────────────────────────────────────────────────────────────────
# §9.B.4 Compiled wizard schema
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_schema(category_id: UUID, db: AsyncSession) -> dict:
    """Compiled wizard schema per §9.B.4 + cross-module callers (§2.4 + §16).

    Returns the §5A.B envelope as a plain ``dict``.  Cached per
    ``category_id`` TTL 1 h.

    Raises:
        CategoryNotFoundError: when ``category_id`` not in ``categories``.
    """

    async def _fetch() -> dict:
        return await category_repo.fetch_schema_uncached(db, category_id)

    return await get_or_set(
        _schema_cache_key(category_id),
        _fetch,
        ttl=_SCHEMA_TTL_SECONDS,
        single_flight=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# §9.B.5 Field-Enum lookup
# ─────────────────────────────────────────────────────────────────────────────
async def get_field_enum(
    category_id: UUID,
    field_name: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Field-Enum lookup per §9.B.5.

    Cached per ``(category_id, field_name)`` TTL 1 h with
    ``single_flight=True`` per ``MVP_ARCH §6.8`` — the 291 Brand-pattern
    enum payloads can be 50-200 KB each and concurrent cold-cache hits
    would each rebuild the same blob.

    Raises:
        CategoryNotFoundError: when ``category_id`` not in ``categories``.
        FieldEnumNotFoundError: when ``(category_id, field_name)`` has no
            row in ``field_enum_values``.
    """

    async def _fetch() -> dict[str, Any]:
        entries, truncated = await category_repo.fetch_field_enum_uncached(
            db, category_id, field_name
        )
        # Coerce each entry to the §5.6.4 shape {canonical, meesho, labels}.
        out_entries: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            canonical = str(entry.get("canonical", ""))
            meesho = str(entry.get("meesho", canonical))
            labels = entry.get("labels") or {"en": canonical}
            if not isinstance(labels, dict):
                labels = {"en": canonical}
            out_entries.append(
                {
                    "canonical": canonical,
                    "meesho": meesho,
                    "labels": {str(k): str(v) for k, v in labels.items()},
                }
            )
        return {
            "enum_entries": out_entries,
            "total": len(out_entries),
            "truncated": truncated,
        }

    payload = await get_or_set(
        _field_enum_cache_key(category_id, field_name),
        _fetch,
        ttl=_FIELD_ENUM_TTL_SECONDS,
        single_flight=True,
    )
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# §9.C Cross-module surfaces
# ─────────────────────────────────────────────────────────────────────────────
async def get_commission(category_id: UUID, db: AsyncSession) -> Decimal:
    """Cross-module call from ``pricing.service.calculate_price`` (§2.6).

    Raises :class:`CategoryNotFoundError` if no row exists.  Returns the
    ``commission_pct`` Decimal as-stored (NEVER None — categories without
    a seeded commission have no pricing surface in V1; the pricing service
    fails over to a default).
    """
    # First check existence (so we can distinguish "no row" from "row but
    # commission_pct IS NULL").
    exists = await category_repo.assert_category_exists_uncached(db, category_id)
    if not exists:
        raise CategoryNotFoundError()
    commission = await category_repo.get_commission_uncached(db, category_id)
    if commission is None:
        # Per the docstring above — pricing service handles None at the
        # call site (defaults to 0).  We surface a Decimal so callers
        # don't have to None-check.
        return Decimal("0.00")
    return commission


async def list_super_categories(db: AsyncSession) -> list[SuperCategoryInfo]:
    """Cross-module call from ``customer.service.set_active_categories`` (§8.C).

    Distinct super_id / super_name list with diagnostic leaf_count.
    Cached GLOBAL TTL 1 h.
    """

    async def _fetch() -> list[dict[str, Any]]:
        infos = await category_repo.list_super_id_distinct(db)
        return [
            {
                "super_id": info.super_id,
                "super_name": info.super_name,
                "leaf_count": info.leaf_count,
            }
            for info in infos
        ]

    payload = await get_or_set(
        "super_category_list",
        _fetch,
        ttl=_SUPER_LIST_TTL_SECONDS,
        single_flight=True,
    )
    return [
        SuperCategoryInfo(
            super_id=str(p["super_id"]),
            super_name=str(p["super_name"]),
            leaf_count=int(p["leaf_count"]),
        )
        for p in payload
    ]


async def assert_category_exists(category_id: UUID, db: AsyncSession) -> None:
    """Cross-module validation gate (called by ``catalog`` per §2.D / §16).

    Raises:
        CategoryNotFoundError: when ``category_id`` not in ``categories``.
    """
    exists = await category_repo.assert_category_exists_uncached(db, category_id)
    if not exists:
        raise CategoryNotFoundError()


__all__ = [
    "assert_category_exists",
    "browse_categories",
    "fetch_schema",
    "get_category_tree",
    "get_commission",
    "get_field_enum",
    "list_super_categories",
    "suggest_categories",
]

"""Smart Category Picker — pure-Python helpers (AI track).

PUBLIC SURFACE (locked contract — see module-private NOTES below):

* :func:`compress_tree` — collapse the 3,772-leaf flat ``CategoryRow``
  list into a JSON-serialisable, deterministic dict that
  :func:`app.ai_ops.client.call_gemini` accepts as a ``prompt_vars`` value
  for the ``smart_picker.v1`` prompt template (``{{compressed_tree}}``
  variable per :mod:`app.ai_ops.prompts.smart_picker_v1`).
* :func:`calibrate_confidence` — penalise a raw AI-emitted confidence by
  the number of Layer 2 guardrail retries (``ai_ops.client``'s
  ``layer2_retries`` field per §6A.E), clamped to ``[0.0, 1.0]``.  Used
  by ``category.service.suggest_categories`` to clamp
  ``CategorySuggestion.confidence`` (``Field(ge=0.0, le=1.0)`` per
  §9.E).
* :func:`select_top_k` — sort scored suggestions by confidence
  DESCENDING and return the top-K with deterministic tie-breaks (on
  ``category_id`` string) so that the §9.B.1 cache key (which hashes the
  query, not the response) yields identical responses across workers.

PIPELINE FIT (per BACKEND_ARCHITECTURE.md §9.B.1 flow steps 3-5):

  step 3a (service)              category.repository.fetch_category_tree
                                  ↓ list[CategoryRow]
  step 3b (here)                  compress_tree(rows, description)
                                  ↓ dict (JSON-serialisable)
  step 3c (ai_ops.client)         call_gemini("smart_picker.v1",
                                              {compressed_tree: <dict>,
                                               description: <q>})
                                  ↓ AIResponse.parsed.suggestions
                                  ↓ AIResponse.layer2_retries
  step 4 (service)                for each raw suggestion:
                                    confidence = calibrate_confidence(
                                        raw_conf, layer2_retries)
                                  ↓
  step 5 (here)                   select_top_k(scored, k=5)
                                  ↓ list[dict] capped at 5

HARD RULES (enforced by code review + §19 linter):

* NO I/O — no DB, no Valkey, no HTTP, no filesystem reads inside any
  helper.  All three functions are pure functions of their inputs.
* NO new third-party dependencies — stdlib only.
* DETERMINISTIC — for identical input, the output bytes
  (``json.dumps(...)`` for :func:`compress_tree`; ``id`` ordering for
  :func:`select_top_k`) are bit-identical so that the §9.B.1 cache key
  (``smart_picker:{sha256(q)}:v{cache_version}``) actually deduplicates
  cross-worker traffic.
* NO ADAPTERS — this module MUST NOT import from
  :mod:`app.adapters.gemini` per §3.G + §16 boundary.

NOTES (non-load-bearing, for future iteration):

* The compression strategy is intentionally simple for V1: group by
  ``super_id``, sample up to N leaves per group, prioritise by trigram
  overlap with the seller's description.  The ranker (Gemini) sees the
  super-category context plus a representative leaf sample — enough to
  pick the right leaf when one exists in the sample, and enough signal
  to graceful-fallback when the description is incoherent.  V1.5 may
  introduce embedding pre-filter; the function signature stays stable.
* The confidence penalty (``0.1 * retries``) was chosen so that one
  retry shaves a "0.85 confident" answer down to 0.75 — still above the
  typical UX cut-off — while two retries (the §6A.E cap) shave it to
  0.65, signalling the frontend to surface the manual browse fallback.

Owner: ``meesell-category-picker-builder``.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Iterable

# ─────────────────────────────────────────────────────────────────────────────
# Tunables — kept module-private so callers stay stable across V1.5 tweaks.
# ─────────────────────────────────────────────────────────────────────────────

# Maximum leaves emitted per super-category in the compressed tree.  Sized
# against the §6A.D token budget for ``smart_picker``: ~50 leaves × ~12 tokens
# each × ~17 super-categories ≈ 10K input tokens, well under the workload's
# 32K input cap.
_MAX_LEAVES_PER_SUPER: int = 50

# Trigram length used for description-aware ranking inside compress_tree.
# 3 is the pg_trgm default and matches the database-side ranking signal so
# the AI sees a similar relevance order to what /browse would return.
_TRIGRAM_N: int = 3

# Penalty per Layer 2 retry applied in calibrate_confidence.  Locked at 0.1
# per the §6A.E retry contract (max 2 retries → max 0.2 penalty).
_RETRY_PENALTY: float = 0.1


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (module-private)
# ─────────────────────────────────────────────────────────────────────────────


def _row_field(row: Any, name: str) -> Any:
    """Read ``name`` from a ``CategoryRow``-like object.

    Accepts the §9.F frozen dataclass, a plain dict, or any object with the
    attribute set.  Returns ``None`` if missing (callers handle the
    fallback).  Kept private — the public API consumes the dataclass shape
    but this gives test fixtures wiggle room.
    """
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)


def _trigrams(text: str) -> set[str]:
    """Return the set of lowercase n-grams in ``text`` (n = _TRIGRAM_N).

    Mirrors pg_trgm's tokenisation (padded with spaces) loosely enough that
    the AI sees roughly the same relevance ordering /browse would produce
    on the same query.  Deterministic and dependency-free.
    """
    if not text:
        return set()
    padded = f"  {text.lower()}  "
    return {padded[i : i + _TRIGRAM_N] for i in range(len(padded) - _TRIGRAM_N + 1)}


def _overlap(leaf_trigrams: set[str], q_trigrams: set[str]) -> int:
    """Trigram overlap count — used as the description-aware sort key.

    Integer (not Jaccard) keeps the ordering total and avoids float
    instability across workers — bit-identical output is the contract.
    """
    if not q_trigrams or not leaf_trigrams:
        return 0
    return len(leaf_trigrams & q_trigrams)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────


def compress_tree(
    category_rows: Iterable[Any],
    description: str | None = None,
) -> dict[str, Any]:
    """Compress 3,772 ``CategoryRow``s into a Gemini-prompt-sized dict.

    Strategy:

    1. Group rows by ``super_id``.
    2. For each super-category, rank its leaves by trigram overlap with
       ``description`` (if provided); ties break on ``leaf_name`` then on
       ``category_id`` (lexicographic) so the output is deterministic.
    3. Emit up to ``_MAX_LEAVES_PER_SUPER`` leaves per super-category as
       ``{"category_id": str, "leaf_name": str, "path": str}`` tuples.
    4. Sort super-categories by ``super_id`` (lexicographic) so the
       outer dict iteration order is deterministic for cache stability.

    Args:
        category_rows: Iterable of §9.F ``CategoryRow`` instances (or
            plain dicts with the same keys).  The §9.D
            ``fetch_category_tree`` repository method returns the canonical
            list.
        description: Optional seller free-text product description.  When
            provided, biases the per-super leaf sample toward leaves
            whose ``leaf_name``/``path`` share trigrams with the
            description.

    Returns:
        JSON-serialisable dict::

            {
                "super_categories": [
                    {
                        "super_id": "<str>",
                        "super_name": "<str>",
                        "leaves": [
                            {
                                "category_id": "<uuid-as-str>",
                                "leaf_name": "<str>",
                                "path": "<str>",
                            },
                            ...
                        ],
                    },
                    ...
                ],
            }

        ``category_id`` is always emitted as a string so the dict is
        ``json.dumps``-safe (UUIDs would otherwise raise).  The
        ``smart_picker.v1`` prompt template consumes this via the
        ``{{compressed_tree}}`` variable; the template's ``json.dumps`` call
        site sees deterministic key ordering by relying on Python 3.7+
        insertion order + the explicit sorts here.

    Determinism:
        ``json.dumps(compress_tree(rows), sort_keys=True)`` is
        bit-identical across calls with identical (rows, description).
        Tested at :file:`backend/tests/modules/category/test_picker_helpers.py`.
    """
    q_trigrams: set[str] = _trigrams(description) if description else set()

    # Bucket by super_id; sort within each bucket once we know the bucket
    # is closed (single-pass grouping is wrong with arbitrary input order).
    buckets: dict[str, dict[str, Any]] = {}
    for row in category_rows:
        super_id_raw = _row_field(row, "super_id")
        if super_id_raw is None:
            # Defensive — repository contract guarantees non-null but we
            # don't want to crash a 3,772-row compression on one bad row.
            continue
        super_id = str(super_id_raw)
        super_name = str(_row_field(row, "super_name") or "")
        leaf_name = str(_row_field(row, "leaf_name") or "")
        path = str(_row_field(row, "path") or "")
        # UUIDs are stringified eagerly so json.dumps doesn't choke and so
        # the deterministic-ordering contract holds across worker boots
        # (the UUID's __str__ is stable; its bytes representation is not
        # what callers see).
        category_id = str(_row_field(row, "id") or "")

        bucket = buckets.setdefault(
            super_id,
            {"super_id": super_id, "super_name": super_name, "_leaves": []},
        )
        # Pre-compute the leaf's trigram overlap once per row.
        leaf_trigrams = _trigrams(f"{leaf_name} {path}") if q_trigrams else set()
        bucket["_leaves"].append(
            {
                "category_id": category_id,
                "leaf_name": leaf_name,
                "path": path,
                "_overlap": _overlap(leaf_trigrams, q_trigrams),
            }
        )

    # Close out each bucket: sort leaves, trim to cap, drop internal sort key.
    super_categories: list[dict[str, Any]] = []
    for super_id in sorted(buckets):
        bucket = buckets[super_id]
        leaves: list[dict[str, Any]] = bucket["_leaves"]
        # Sort: overlap DESC, leaf_name ASC, category_id ASC.  All three
        # tie-breakers are deterministic and total.
        leaves.sort(
            key=lambda leaf: (
                -leaf["_overlap"],
                leaf["leaf_name"],
                leaf["category_id"],
            )
        )
        trimmed = [
            {
                "category_id": leaf["category_id"],
                "leaf_name": leaf["leaf_name"],
                "path": leaf["path"],
            }
            for leaf in leaves[:_MAX_LEAVES_PER_SUPER]
        ]
        super_categories.append(
            {
                "super_id": bucket["super_id"],
                "super_name": bucket["super_name"],
                "leaves": trimmed,
            }
        )

    return {"super_categories": super_categories}


def calibrate_confidence(
    raw_ai_confidence: float,
    layer2_retries: int = 0,
) -> float:
    """Penalise raw AI confidence by Layer 2 guardrail retry count.

    Penalty: ``_RETRY_PENALTY * max(0, layer2_retries)``.  Final value is
    clamped to ``[0.0, 1.0]`` so it passes §9.E
    ``CategorySuggestion.confidence = Field(ge=0.0, le=1.0)``.

    Negative ``layer2_retries`` are treated as zero (defensive — the
    ``AIResponse.layer2_retries`` field is constrained ``int >= 0`` per
    §6A.C but the helper stays robust against future caller mistakes).

    Args:
        raw_ai_confidence: The ``confidence`` value the AI emitted for one
            suggestion before clamping.  Any float; will be clamped.
        layer2_retries: The §6A.E retry count from the AI envelope
            (``AIResponse.layer2_retries``).  0 on a first-attempt pass;
            up to 2 if the AI returned invalid category_ids twice before
            converging.

    Returns:
        ``float`` in ``[0.0, 1.0]`` — safe to assign directly to the
        Pydantic ``CategorySuggestion.confidence`` field.
    """
    retries = max(0, int(layer2_retries))
    penalised = float(raw_ai_confidence) - (_RETRY_PENALTY * retries)
    if penalised < 0.0:
        return 0.0
    if penalised > 1.0:
        return 1.0
    return penalised


def select_top_k(
    scored_suggestions: list[dict[str, Any]],
    k: int = 5,
) -> list[dict[str, Any]]:
    """Return the top-K suggestions by confidence DESCENDING.

    Tie-break is lexicographic on ``category_id`` (stringified) — the
    same field the §9.B.1 cache key derives stability from.  Suggestions
    missing ``confidence`` are treated as 0.0; suggestions missing
    ``category_id`` sort last (empty string tie-breaker).

    Args:
        scored_suggestions: List of dicts.  At minimum each carries
            ``confidence`` and ``category_id``; other fields
            (``super_id``, ``path``, ``leaf_name``, ``reasons``) are
            preserved verbatim — the service layer maps them to the §9.E
            ``CategorySuggestion`` Pydantic shape.
        k: Cap on returned suggestions.  §9.E
            ``SuggestResponse.suggestions = Field(max_length=5)`` is the
            contract for V1; pass ``5`` from the service.

    Returns:
        New list (input is not mutated) of up to ``k`` dicts, sorted by
        confidence DESC then by ``category_id`` ASC.  ``k <= 0`` yields
        an empty list.
    """
    if k <= 0 or not scored_suggestions:
        return []

    # Sort a shallow copy — input list is not mutated (the service may
    # reuse it for diagnostic logging).
    ranked = sorted(
        scored_suggestions,
        key=lambda s: (
            -float(s.get("confidence", 0.0) or 0.0),
            str(s.get("category_id", "") or ""),
        ),
    )
    return ranked[:k]


# ─────────────────────────────────────────────────────────────────────────────
# Marker re-exports — keep __all__ tight so star-imports don't leak the
# private helpers above into the service layer.
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "compress_tree",
    "calibrate_confidence",
    "select_top_k",
]


# ─────────────────────────────────────────────────────────────────────────────
# Defensive guard: if a caller passes a frozen dataclass to compress_tree's
# row iterator that's neither dict-like nor attr-accessible, _row_field
# falls back to ``None`` and the row is skipped — but log nothing here
# (this module is pure-Python and has no logger).  The service layer is
# the right place to surface row-skipping telemetry.
#
# We keep ``asdict`` and ``is_dataclass`` imported to make the dataclass
# duck-typing intent visible to readers — even though _row_field uses
# getattr directly for performance (no asdict allocation per row).
# ─────────────────────────────────────────────────────────────────────────────
_ = (asdict, is_dataclass)  # re-export-free no-op; keeps imports honest

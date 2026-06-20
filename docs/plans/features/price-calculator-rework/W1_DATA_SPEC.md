# W1 — DATA LAYER BUILD SPEC (Price Calculator Rework)

| Field | Value |
|---|---|
| Wave | **W1** (ROOT — hard barrier; W2 + W6 bind to this file's path + schema) |
| Section | section-7 (`price-calculator`) — V1 Feature 7 |
| Author | `meesell-data-engineer` (Data Lead) — HYBRID step-1 SPEC |
| Builder (step-2) | `meesell-database-builder` (executes; does NOT design) |
| Merge-gate (step-3) | `meesell-data-engineer` (data-file review) + `meesell-backend-coordinator` (loader-code review) |
| Branch | `feature/section-7/backend` (off `feature/section-7/integration`) |
| Type | code + data |
| Session | `mesell-price-calculator-data-session-15` |
| Authoritative model | `.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md` (confirmed 2026-06-19) |
| Source data | `logs/scraper/transfer_price_census_summary.json` → key `lookup` (3,772 entries, `error_rows=0`, all `formula_ok=true`) |

> **DO NOT follow** `handoff_pricing_transfer_price.md` (round-4 `fetch-supplier-products` / "₹9 flat fee"). It predates the census and is WRONG. The getTransferPrice census is the only source.

---

## 0. Confirmed facts this wave bakes in (verified by the Data Lead 2026-06-19)

- Census `lookup` = **exactly 3,772** entries, keyed by **string `sscat_id`** (e.g. `"10949"`). Each value: `{leaf_name, path_str, commission_percentage, shipping_charges, transfer_price_at_100, formula_ok}`.
- `commission_percentage == 0.0` for **all 3,772** rows (`commission_analysis.non_zero_count = 0`).
- `shipping_charges` is an **integer**, per-category constant, range **[48, 8435]**, 365 distinct values.
- **Q2 RESOLVED — no separate category-mapping unit needed.** `categories.meesho_leaf_id` (`backend/app/shared/models/category.py:47`, `String(16)`, `unique=True`, indexed `idx_categories_meesho_leaf`) **IS** the Meesho `sscat_id`. 100% overlap verified (3,772/3,772). The pricing engine (W2) maps product → category → `meesho_leaf_id` → lookup key directly. The lookup file is keyed by `meesho_leaf_id` (= `sscat_id` as string).
- Census meta: `generated_at = 2026-06-19T03:32:46`, `census_price = 100`, `total_leaves = 3772`, `rows_with_data = 3772`, `error_rows = 0`.
- Sanity anchor: `"10949"` (Extension Chords) → `shipping_charges=82`, `commission_percentage=0.0`, `transfer_price_at_100=85.06`.

---

## 1. The productionized data file

**Path (NEW, committed — NOT gitignored, it is shipped production data):**
`backend/app/data/meesho_pricing_lookup.json`

**Exact schema:**
```json
{
  "_meta": {
    "source": "getTransferPrice census (logs/scraper/transfer_price_census_summary.json)",
    "generated_at": "2026-06-19T03:32:46.427203",
    "census_price": 100,
    "total": 3772,
    "model": "confirmed-2026-06-19",
    "refresh": "monthly-via-scraper (W6 — folded into the existing monthly category scrape)",
    "version": "1"
  },
  "lookup": {
    "10949": { "shipping_charges": 82, "commission_percentage": 0 },
    "...": { "shipping_charges": 0, "commission_percentage": 0 }
  }
}
```

**Schema rules (the build/transform step MUST enforce):**
- Top-level keys: exactly `_meta` and `lookup`.
- `lookup` is keyed by `meesho_leaf_id` (= census `sscat_id`) as a **string**.
- Each `lookup` value is exactly `{ "shipping_charges": <int>, "commission_percentage": <number, always 0> }`. **No other keys** — `leaf_name`, `path_str`, `transfer_price_at_100`, `formula_ok` are dropped (they are derivation/QA fields, not runtime inputs; the runtime engine only needs shipping + commission default). `transfer_price_at_100` is retained ONLY in the census summary for the W1 validation test (spot-check), not in the shipped file.
- `shipping_charges` is emitted as an **integer** (cast from the census value; census values are already int).
- `commission_percentage` is emitted as a **number `0`** (the census `0.0` floats collapse to `0`).
- `_meta.generated_at` and `_meta.census_price` are copied verbatim from the census summary's top-level `generated_at` / `census_price`. `_meta.total` MUST equal `len(lookup)` and MUST be 3772.

**How it is generated (the build/transform step `meesell-database-builder` writes):**

A small, idempotent, re-runnable transform script:
`backend/scripts/build_pricing_lookup.py`

Behavior:
1. Read `logs/scraper/transfer_price_census_summary.json`.
2. Assert `error_rows == 0` and `len(d["lookup"]) == 3772` — hard-fail otherwise (do not emit a partial file).
3. For each `sscat_id, v` in `d["lookup"]`: emit `lookup[str(sscat_id)] = {"shipping_charges": int(v["shipping_charges"]), "commission_percentage": 0}`. Assert `v["commission_percentage"] == 0.0` and `v["formula_ok"] is True` for every row (hard-fail on any violation).
4. Build `_meta` from the census summary's `generated_at` + `census_price`, plus the static fields above; set `_meta.total = len(lookup)`.
5. Write `backend/app/data/meesho_pricing_lookup.json` with `json.dumps(..., indent=2, sort_keys=True, ensure_ascii=False)` for a stable, diff-friendly commit (W6 monthly refresh overwrites the SAME file — stable ordering keeps diffs minimal).

The script is the SINGLE producer for both W1 (run once now) and W6 (folded into the monthly scrape). W6 will call this same transform from the monthly orchestrator. Keep it dependency-free (stdlib only).

---

## 2. Loader contract (what the W2 pricing engine calls)

**Module (NEW):** `backend/app/modules/pricing/pricing_lookup.py`

> A dedicated loader module — NOT folded into `service.py` (keeps the engine clean; matches the wave-plan §3 preference). Do NOT add loaders to `backend/app/data/__init__.py` (that module is the legacy stub helper set being trimmed — see §3).

**Public API:**
```python
class UnknownCategoryError(KeyError):
    """Raised when a meesho_leaf_id (sscat_id) is not present in the pricing lookup."""

def get_shipping(meesho_leaf_id: str) -> int:
    """Per-category constant shipping charge for the given Meesho leaf id (sscat_id).
    Raises UnknownCategoryError on miss."""

def get_commission_default(meesho_leaf_id: str) -> Decimal:
    """Default commission percentage for the category (always Decimal('0') for V1).
    Raises UnknownCategoryError on miss."""

def lookup_size() -> int:
    """Number of entries in the loaded lookup (for the health/validation test)."""
```

**Contract details:**
- **Caching: load-once.** Use `@lru_cache(maxsize=1)` on a private `_load() -> dict` that reads `backend/app/data/meesho_pricing_lookup.json` once at first call and returns the `lookup` sub-dict. File is read at process start / first call; a refreshed file (W6) is picked up on next deploy/restart (document this reload semantic in the module docstring).
- **Key normalization:** accept `meesho_leaf_id` as `str`; the engine passes `category.meesho_leaf_id` directly (already a string). Internally `str(...)`-coerce defensively before lookup.
- **Lookup-miss behavior: RAISE `UnknownCategoryError`** — never silently fall back to a default shipping. A miss is a data-integrity bug (a seeded category with no pricing row), and W2's router translates it to a clear 4xx/handled error. NO numeric fallback (a wrong shipping number would silently produce a wrong settlement — worse than a clear error).
- `get_commission_default` returns `Decimal('0')` for V1 (commission is an optional override the engine accepts as a parameter; the lookup's stored `commission_percentage` is 0 everywhere but is read through this accessor so W6 refreshes are honored if Meesho ever charges commission).
- Pure-stdlib + `decimal`; no DB, no network, no SQLAlchemy import.

---

## 3. Retire the wrong-model stubs

**Recommendation: TOMBSTONE (not hard-delete) the two stub data files + REMOVE all code refs.**

| File | Action |
|---|---|
| `backend/app/data/meesho_shipping_slabs.json` | Tombstone: replace contents with a single `{ "_CLOSED": "...note..." }` object (see note below). |
| `backend/app/data/category_commissions.json` | Tombstone: same `_CLOSED` note object. |

**Tombstone note content (both files):**
```json
{
  "_CLOSED": "RETIRED 2026-06-19 (W1, price-calculator rework). Superseded by backend/app/data/meesho_pricing_lookup.json (getTransferPrice census model). The old slab/commission model was WRONG (deducted full shipping from seller + 4% commission). Do NOT reference. See docs/plans/features/price-calculator-rework/W1_DATA_SPEC.md.",
  "lookup": {}
}
```
(The trailing `"lookup": {}` keeps any accidental legacy consumer from KeyError-crashing on shape; but all real refs are removed — see below.)

**Code refs the builder MUST grep for and remove (verified by the Data Lead):**
- `backend/app/data/__init__.py:28-29` — delete the `load_shipping_slabs()` function. **VERIFIED: zero callers in `backend/app/`** (only the definition itself) — safe to remove.
- `backend/app/data/__init__.py` — leave `load_categories` / `load_attributes` / `load_banned_words` UNTOUCHED (out of scope; those are quality-engine stubs, not pricing). Only remove `load_shipping_slabs`.
- `category_commissions.json` — **VERIFIED: zero refs in `backend/app/`**; the only refs are in `backend/scripts/meesho_commission_*.py` (retired scrape scripts, out of scope for this wave — leave the scripts but their output file is tombstoned). The builder must `grep -rn "category_commissions\|meesho_shipping_slabs" backend/app/` and confirm zero remaining `app/` refs after the edit.

**Why tombstone, not delete:** keeps a discoverable CLOSED breadcrumb at the path any old doc/spec points to, and preserves git history clarity. The empty `lookup` shape prevents a hard crash if a missed consumer survives. Hard-delete is acceptable ONLY if the merge-gate grep proves zero refs anywhere in the repo (`backend/`, `docs/` code samples) — default to tombstone.

---

## 4. Validation / tests

**Test file (NEW):** `backend/tests/modules/pricing/test_pricing_lookup.py`

| Test | Assertion |
|---|---|
| `test_lookup_has_3772_entries` | `len(json.load(...)["lookup"]) == 3772`; `_meta["total"] == 3772`. |
| `test_all_commission_zero` | every entry's `commission_percentage == 0`. |
| `test_shipping_in_range` | every entry's `shipping_charges` is an `int` and `48 <= v <= 8435`. |
| `test_known_anchor` | `lookup["10949"]["shipping_charges"] == 82` (Extension Chords). |
| `test_loader_get_shipping` | `pricing_lookup.get_shipping("10949") == 82`. |
| `test_loader_unknown_raises` | `get_shipping("99999999")` raises `UnknownCategoryError`. |
| `test_loader_commission_default` | `get_commission_default("10949") == Decimal("0")`. |
| `test_no_orphan_categories` | **DB-join test:** for every `categories.meesho_leaf_id` in the seeded DB, the id resolves in the lookup (zero orphans). Marked `@pytest.mark.integration` (needs the seeded test DB); if the seeded DB is unavailable in the unit CI lane, fall back to asserting the lookup is a SUPERSET of the seed's `meesho_leaf_id` set read from `data/parsed/`/seed fixtures. The builder picks whichever seed source is available in the test env and documents it in the PR. |
| `test_meta_block` | `_meta` carries `source`, `generated_at`, `census_price == 100`, `model == "confirmed-2026-06-19"`, `refresh`, `version`. |

Gate-1 (unit) MUST be green. No XLSX surface is touched → **gate-5 golden_roundtrip is N/A** (justify with a one-liner in the PR body).

---

## 5. File ownership (exact — no overlap with W2/W3/W4/W6)

`meesell-database-builder` CREATES:
- `backend/app/data/meesho_pricing_lookup.json` (data — generated, committed)
- `backend/scripts/build_pricing_lookup.py` (transform script)
- `backend/app/modules/pricing/pricing_lookup.py` (loader module)
- `backend/tests/modules/pricing/test_pricing_lookup.py` (tests)

`meesell-database-builder` MODIFIES:
- `backend/app/data/__init__.py` (remove `load_shipping_slabs` only)
- `backend/app/data/meesho_shipping_slabs.json` (tombstone)
- `backend/app/data/category_commissions.json` (tombstone)

**No overlap:** W2 owns `service.py` / `domain.py` / `schemas.py` / `router.py` / `repository.py` / `pricing_calc.py` / migration / `test_settlement_formula.py` — NONE touched here. W3 = frontend. W4 = export. W6 is the ONLY other writer of `meesho_pricing_lookup.json` (monthly refresh, never concurrent) and reuses `build_pricing_lookup.py`. The loader module `pricing_lookup.py` is created here and only READ by W2.

---

## 6. Merge-gate checklist (Data Lead, step-3)

1. `.github/PULL_REQUEST_TEMPLATE/data.md` filled: source-change declared (NEW pricing lookup from census), run command + stats (`python backend/scripts/build_pricing_lookup.py` → 3772 rows, 0 errors, shipping range, diff vs none), schema-impact = "No DB schema change — pure data file + loader" (NO Alembic — the W2 wave owns the `pricing_calcs` migration).
2. Gate-1 green (the 9 tests above). Gate-5 N/A justified.
3. `feature_board_data.md` row shows `IN REVIEW`.
4. Data-file spot-check: 3 entries match the census summary verbatim; `_meta.total == 3772`; tombstones in place; zero `app/` refs to the retired stubs (grep).
5. Coverage report (3772/3772, 0 errors) recorded in PR body + `STATUS_DATA.md`. Squash-merge to `feature/section-7/backend`.

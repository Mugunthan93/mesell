# §21 Extraction Path Audit Report
**Date:** 2026-06-09
**Auditor sub-session:** meesell-backend-verification-21-extraction-1
**Audit target:** `docs/BACKEND_ARCHITECTURE.md` §21 (Extraction Path — V1.5/V2) + §16.G/§16.H extraction contract + per-module §X.K/§X.L extraction notes
**Overall verdict:** PARTIAL

> No V1 blockers. Checks 2, 3, 5 PASS. Checks 1, 4 PARTIAL — all findings are
> V1.5-readiness nuances (serializer wiring) and documentation-consistency drift
> (extraction-order contradictions inside two LOCKED per-module notes). The V1.5
> landing zone (`core/extracted_clients/`) is correctly empty. Nothing requires a
> code change for V1; the actionable items are V1.5-prep + doc-amendment requests.

---

## Audit checklist results

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Cross-module `domain.py` return types JSON-serializable | **PARTIAL** | Pure-primitive returns JSON-native today; UUID/datetime/Decimal/bytes returns need serializer wiring at extraction (anticipated by checklist). See per-type table below. |
| 2 | `service.py` signatures stable (no `**kwargs`, no positional-only) | **PASS** | `grep` across all 8 `service.py`: zero `**kwargs`, zero positional-only (`/`). Several keyword-only (`*,`) — stability-positive. |
| 3 | `core/extracted_clients/` absent (V1.5 landing zone) | **PASS** | `ls backend/app/core/extracted_clients/` → "No such file or directory"; `find … -name "*extracted_client*"` → 0 matches. Matches §21.F.1 "V1 has zero such entries." |
| 4 | Per-module §X.K extraction notes present | **PARTIAL** | All 8 present (§7.K/§8.K/§9.K/§10.K/§11.L/§12.K/§13.K/§14.L). Each documents owned tables + cross-module sigs→HTTP. BUT §7.K + §10.K embed extraction orderings that contradict the locked §21.B/§16.H order (Finding F-21-1). |
| 5 | §21.B 8-step order consistent with §16.H | **PASS** | §21.B (L7666-7673) == §16.H.1 (L6727-6734) == expected order, exactly: `export → dashboard → image → pricing → customer → category → iam → catalog`. §21.B states "The order is the same as §16.H." |

---

## Check 1 — Cross-module `domain.py` return-type JSON-serializability (detail)

The §16.G.1 contract states the `domain.py` dataclass IS the V1.5 wire contract and
"MUST be JSON-serializable… frozen dataclass with primitive / dict / list fields."
The §21.C readiness checklist marks "✓ JSON-serializable returns" for every module.
Per-type verification against the actual code:

| Cross-module method | Return type | Field types | stdlib-`json`-native? | Pydantic wire-mirror | Verdict |
|---|---|---|---|---|---|
| `customer.get_compliance_block` (`service.py:648`) | `ComplianceBlock` | 10× `str`/`str\|None` | **YES** | `customer/schemas.py:174 ComplianceBlockResponse` | PASS |
| `customer.get_onboarding_completeness` (`service.py:682`) † | `ProfileCompleteness` | 4× `int`, 1× `bool` | **YES** | `dashboard/schemas.py:61 ProfileCompletenessSummary` | PASS |
| `customer.assert_eligible_for_super_id` (`service.py:735`) | `None` / raises | — | N/A | — | PASS |
| `category.fetch_schema` (`service.py:467`) | `dict` (§5A.B envelope) | JSON-native by construction — round-trips through `core/cache.get_or_set` `json.dumps`/`json.loads` (`cache.py:92,97,107,123,133`) | **YES** (cache-proven) | `category/schemas.py:153 SchemaResponse` | PASS |
| `category.get_commission` (`service.py:548`) | **`Decimal`** (bare; never `None` — returns `Decimal("0.00")`) | `Decimal` | **NO** | **none** | **V1.5 CONCERN** |
| `catalog.assert_product_ownership` (`service.py:919`) | `None` / raises | — | N/A | — | PASS |
| `catalog.list_products` (`service.py:997`) | `PaginatedProductsInternal` → `tuple[Product]` | `Product`: 4× `UUID`, 3× `datetime` | **NO** | `catalog/schemas.py:230 PaginatedProductsResponse` ✓ | V1.5 CONCERN (mirror exists) |
| `catalog.get_product_for_export` (`service.py:943`) | `ExportSnapshotInternal` | 2× `UUID`, `tuple[str]`, nested `ValidationSummaryInternal(UUID,…)` | **NO** | `catalog/schemas.py:266 ExportSnapshot` ✓ | V1.5 CONCERN (mirror exists) |
| `image.get_image_urls` (`service.py:280`) | `list[ImageUrl]` | `ImageUrl`: `UUID image_id`, `int`, `str`, `bool` | **NO** | **none** (`image/schemas.py` has only Upload/Summary/List) | **V1.5 CONCERN** |
| `image.get_image_bytes` (`service.py:319`) | **`bytes`** | binary | **NO** (cannot be a JSON field) | N/A | **V1.5 ESCALATION** |

† The §21.C.5 / audit checklist name `get_profile_completeness`; the live method is
`get_onboarding_completeness` (returns `ProfileCompleteness`). Method-name drift — see OBS-21-3.

**Reconciliation.** Every cross-module `domain.py` docstring states "These types never
cross the HTTP boundary directly — the Pydantic schemas in `.schemas` are the wire
shapes." Pydantic v2 serializes `UUID`→str, `datetime`→ISO-8601, `Decimal`→str/float
natively, so where a mirror exists the V1.5 wire contract is JSON-ready. In V1 **all
ten calls are in-process Python** — zero serialization occurs — so there is **no V1
runtime defect**. The findings are extraction-readiness gaps, which is precisely what
§21 exists to land.

**Finding F-21-2 (LOW, V1.5).** Two cross-module returns lack a Pydantic wire-mirror
**and** are not stdlib-`json`-native:
- `category.get_commission → Decimal` (bare). The §16.G.2 shim pattern would need an
  explicit `Decimal↔str` encoder. The pricing consumer reads it in-process for
  arithmetic (`pricing/service.py:165-168`, `== Decimal("0.00")` guard per §12-PRICING-D1).
- `image.get_image_urls → list[ImageUrl]` (carries `UUID image_id`); also
  `image.summary → ImageStatusSummary` (`UUID product_id`). No mirror in `image/schemas.py`.

Recommend: before the `image` (order 3) and `category` (order 6) extractions, add the
serializer wiring (Pydantic mirror or shim-level encoder).

**Finding F-21-3 (LOW, V1.5 — correctly anticipated).** `image.get_image_bytes → bytes`
cannot cross an HTTP/JSON boundary as a field. The method's own docstring confirms it is
in-process-only in V1 (streams bytes into the export ZIP, "does NOT generate a signed
URL"). The V1.5 candidate is to swap to a signed-URL-returning method for HTTP transport.
**Gap:** §11.L line 4440 says `get_image_bytes` "become[s] an HTTP call — the contracts
are already locked" **without** noting the required shape change (bytes ≠ JSON field).
Recommend a §11.L forward-note.

**Observation OBS-21-1 (INFO).** §16.G.1's blanket claim that "every cross-module-exported
`domain.py` type already satisfies [JSON-serializable]… primitive / dict / list fields" is
imprecise: `Product`, `ExportSnapshotInternal`, `ImageUrl`, `ImageStatusSummary`,
`CategoryRow`/`get_commission` carry `UUID`/`datetime`/`Decimal`, and `get_image_bytes`
returns `bytes`. The claim holds only under the "Pydantic mirror is the wire shape"
reading (which the domain docstrings and the §16.G.2 shim — note its manual
`str(category_id)` — actually use). Suggest tightening §16.G.1 wording.

---

## Check 2 — `service.py` signature stability (detail)

- **Zero `**kwargs`** in any of the 8 `service.py` files.
- **Zero positional-only parameters** (`/` marker absent everywhere).
- Cross-module surfaces use explicit named params; `image` uses keyword-only (`*, db`)
  which is *more* stable, not less.
- §12.K independently calls the pricing cross-module reads "2 stable contracts," and
  §8.K notes `assert_eligible_for_super_id`'s signature "is already designed for this
  transition." Corroborates stability.

**Observation OBS-21-2 (INFO, hybrid-mode mechanics).** Every cross-module method carries
a `db: AsyncSession` parameter that **cannot survive extraction** — the extracted pod owns
its own session. The §16.G.2 illustrative shim sidesteps this by omitting `db` from even
the V1 signature (`fetch_schema(category_id)`), whereas the real call site is
`fetch_schema(category_id, db=db)`. At extraction the shim must drop `db`. This is inherent
to the modular-monolith→pod transition (not a defect), but §16.G/§21.F do not explicitly
state that `db` is the one signature element the shim strips. Suggest a one-line §21.F note.
Not a Check-2 failure (no `**kwargs`/positional-only involved).

---

## Check 3 — `core/extracted_clients/` absence (detail)

```
$ ls backend/app/core/extracted_clients/
ls: backend/app/core/extracted_clients/: No such file or directory   (exit 1)
$ find backend -name "*extracted_client*"
(no matches)
```
`core/` contains only V1 layers: `auth.py cache.py errors.py middleware/ plan_guard.py
tenancy.py`. The V1.5 landing zone is correctly absent. Consistent with §16.G.2
("`core/extracted_clients/category_client.py` — NEW in V1.5") and §21.F.1 ("§5.D registry
will accumulate these env vars one at a time as modules extract — V1 has zero such
entries"). **No premature V1.5 work. PASS.**

---

## Check 4 — Per-module extraction notes (detail)

| Module | Section | Owned table(s) | Cross-module sigs → HTTP | Rank claim | Consistent w/ §21.B? |
|---|---|---|---|---|---|
| iam | §7.K (L2743) | `users` ✓ | `get_current_user`→`POST /internal/auth/validate` ✓ | **"2nd-easiest after export"** | ✗ §21.B ranks iam **7th** |
| customer | §8.K (L3089) | `seller_profile` ✓ | `assert_eligible_for_super_id`→HTTP ✓ | "extracts cleanly" (no #) | OK |
| category | §9.K (L3487) | global tables / "owns no writes" ✓ | `ai_ops.client.call_gemini`→HTTP; cache moves ✓ | "strong candidate" (no #) | OK |
| catalog | §10.K (L3928) | `catalogs`/`products`/`product_drafts` ✓ | 4 surfaces → 4 RPCs ✓ | "hardest / last" ✓ … **but embeds full contradictory order at L3936** | ✗ (embedded order) |
| image | §11.L (L4433) | `product_images` (FK→products) ✓ | `assert_product_ownership` + `get_image_urls`/`get_image_bytes` → HTTP ✓ | "one of the easier" ✓ | OK |
| pricing | §12.K (L4794) | `pricing_calcs` ✓ | `get_commission` + `assert_product_ownership` ✓ | "extracts trivially" ✓ | OK |
| dashboard | §13.K (L5129) | **zero tables** ✓ | `httpx` → catalog/customer ✓ | "easiest, alongside export" ✓ | OK |
| export | §14.L (L5940) | `exports` ✓ | 4 imports → `httpx.AsyncClient` ✓ | **"the EASIEST"** ✓ | OK |

Presence: **8/8 PASS.** Content (tables + cross-module signatures): **8/8 PASS.**
Note the §21.B locking column correctly cites **§11.L** (image) and **§14.L** (export) —
§11.K and §14.K are *Test plans*; the extraction notes live in `.L`. The audit-prompt's
"§11.K/§14.K" was the imprecise pointer; the document is internally correct.

**Finding F-21-1 (MEDIUM, doc-drift — amendment requested).** Two LOCKED per-module notes
carry extraction orderings that contradict the locked, consolidated §21.B/§16.H order:
1. **§7.K (L2745):** "Per §21 extraction order, `iam` is the **2nd-easiest** module to
   extract after `export`." — §21.B ranks iam **7th** (penultimate; "extraction last
   because every other module must have its `get_current_user` shim already wired").
2. **§10.K (L3936):** "Per §21, the recommended V1.5 extraction order is
   `iam → customer → category → image → pricing → dashboard → export → catalog (last)`."
   — §21.B is `export → dashboard → image → pricing → customer → category → iam → catalog`.
   These agree only on `catalog` last; the first seven are differently ordered.

§7.K and §10.K also contradict **each other** (§7.K: export 1st/iam 2nd; §10.K: iam 1st/
export 7th) — both pre-date the §16.H/§21.B consolidation lock. Authoritative order is
§21.B (§21.B itself: "consolidated from §16.H… the order is the same as §16.H").
Recommend an 8-digit-dated amendment to §7.K + §10.K repointing both to the §21.B order,
following the OBS-16-1 precedent. **No code impact** (V1 has no extraction).

---

## Check 5 — §21.B vs §16.H order consistency (detail)

| Order | §21.B (L7666-7673) | §16.H.1 (L6727-6734) | Expected | Match |
|---|---|---|---|---|
| 1 | export | export | export | ✓ |
| 2 | dashboard | dashboard | dashboard | ✓ |
| 3 | image | image | image | ✓ |
| 4 | pricing | pricing | pricing | ✓ |
| 5 | customer | customer | customer | ✓ |
| 6 | category | category | category | ✓ |
| 7 | iam | iam | iam | ✓ |
| 8 | catalog | catalog | catalog | ✓ |

Exact three-way agreement. **PASS.**

---

## Non-compliance findings (summary)

| ID | Sev | Type | Summary | Action |
|----|-----|------|---------|--------|
| F-21-1 | MEDIUM | Doc-drift (LOCKED §7.K + §10.K) | Embedded extraction orders contradict locked §21.B/§16.H (and each other) | Founder/master amendment repointing §7.K + §10.K to §21.B order |
| F-21-2 | LOW | V1.5-readiness | `get_commission`(Decimal) + `get_image_urls`/`summary`(ImageUrl/ImageStatusSummary, UUID) lack Pydantic wire-mirror & serializer wiring | Add mirror/encoder before `image`(ord 3) + `category`(ord 6) extraction |
| F-21-3 | LOW | V1.5-readiness | `get_image_bytes → bytes` not JSON-transportable; §11.L claims "becomes an HTTP call" without noting shape change | §11.L forward-note: signed-URL swap at image extraction |
| OBS-21-1 | INFO | Doc-precision | §16.G.1 "already JSON-serializable / primitive-dict-list" wording imprecise vs UUID/datetime/Decimal/bytes-bearing dataclasses | Tighten §16.G.1 wording (Pydantic-mirror is the wire shape) |
| OBS-21-2 | INFO | Doc-precision | `db: AsyncSession` param cannot survive extraction; §16.G/§21.F don't state the shim strips it | One-line §21.F note |
| OBS-21-3 | INFO | Spec/code naming | Checklist/§21.C.5 say `get_profile_completeness`; live method is `get_onboarding_completeness` | Cosmetic — align §21.C.5 wording or accept as-is |

**Escalation-trigger assessment.** All three configured triggers were evaluated:
- *"Cross-module method returns a non-JSON-serializable type"* — technically hit by
  `get_commission`(Decimal), `get_image_bytes`(bytes), and the UUID/datetime-bearing
  dataclasses. **Escalated as DOCUMENTED V1.5-readiness items (F-21-2/F-21-3), not as
  surprise V1 blockers** — the checklist itself pre-states the Decimal-encoder and
  bytes-signed-URL cases, and §21 is by definition the V1.5 landing zone. Zero V1 runtime
  impact (all in-process).
- *"`service.py` uses `**kwargs`"* — **none found.** No escalation.
- *"`core/extracted_clients/` exists in V1"* — **absent.** No escalation.

---

## Verdict rationale

§21 is **structurally sound and V1-correct**. The extraction order is internally
self-consistent (§21.B == §16.H, exact), the V1.5 landing zone is correctly empty,
service signatures are stable (no `**kwargs`/positional-only), and all 8 per-module
extraction notes exist with owned-tables + cross-module-signature content. The verdict is
**PARTIAL** rather than PASS because of two non-blocking gaps:

1. **Doc-consistency (F-21-1, MEDIUM):** §7.K and §10.K — both LOCKED — carry stale
   extraction orderings that contradict the consolidated §21.B/§16.H order and each
   other. This undermines §21's "the order is traceable" guarantee even though the
   authoritative table (§21.B) is correct. Requires a dated amendment to the two LOCKED
   notes (REPORTED, not edited, per audit hard-rules).
2. **V1.5 serializer-readiness (F-21-2/F-21-3, LOW):** the `Decimal`, `bytes`, and
   `UUID`/`datetime`-bearing cross-module returns are not stdlib-`json`-native and lack
   serializer wiring (Pydantic mirror present for catalog/customer types, **absent** for
   image `ImageUrl`/`ImageStatusSummary` and category `commission`). These are exactly the
   pre-flagged extraction concerns; they bite only at the relevant module's V1.5
   extraction, never in V1.

No production code was modified. No LOCKED section was amended. No V1 acceptance blocker
arises from §21.

---

## Hand-back to master

- §21 verdict: **PARTIAL** — Checks 2/3/5 PASS, Checks 1/4 PARTIAL. **No V1 blocker.**
- 1 MEDIUM doc-drift finding requiring a founder/master amendment to LOCKED §7.K + §10.K
  (extraction-order contradiction). 2 LOW V1.5-readiness findings (serializer wiring +
  signed-URL swap) — defer to image/category extraction dispatch. 3 INFO observations.
- Carry-forward to §22: F-21-1 amendment decision; F-21-2/F-21-3 belong on the V1.5
  extraction-prep ticket list (not V1 acceptance).
- Recommend chaining with the §15 F-15-* and §17 F6 audit-trail items already in the
  master ledger — none overlap with §21 findings.

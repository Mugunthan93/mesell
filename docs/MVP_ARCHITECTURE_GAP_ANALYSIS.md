# MVP_ARCHITECTURE — Gap Analysis & Reconciliation Plan

**Author:** meesell-data-engineer (coordinator)
**Date:** 2026-06-05
**Status:** DRAFT — pending founder review
**Scope:** Audit `docs/MVP_ARCHITECTURE.md` (2,797 lines, 15 sections) against the as-built database (Alembic head `935e55b4852c`, 13 tables live), the SSoT (`docs/MEESHO_CATEGORY_INTELLIGENCE.md`), and `docs/CORE_PHILOSOPHY.md`.
**Output discipline:** Analysis only. No edits to `MVP_ARCHITECTURE.md`, `MEESHO_CATEGORY_INTELLIGENCE.md`, or any other locked doc. No migrations, no model changes.

---

## Section 1 — Executive Summary

**Total gaps found:** 18 (11 validated from database coordinator's starting list + 7 newly surfaced during this audit).

**Tier-1 BLOCKER-V1 count:** 4 (G1, G2, G8, G16). All are doc-or-artifact gaps that will mislead downstream builders or leave acceptance gates hollow. None require schema migration — schema is already correct.

**Doc-health verdict:** The architecture is **structurally sound and decision-locked**, but it is **stratigraphically inconsistent** — §2 (the data model) is the oldest layer and was never backported when later sections (§5.5, §5.6, §12) amended it. The database team built against the newer, correct layers, which is why the implementation works but the doc reads as drifted. Three classes of drift dominate:

1. **Schema stratigraphy** — 4 deltas live in the DB are absent from §2's DDL (G1, G6, G17).
2. **Section-numbering collisions** — "Section 8" uses §9.x, "Section 9" uses §10.x, "Section 10" + "Section 11" both use §11.x (G3). Every cross-reference is friction.
3. **Prose-only rules** that were realised in code without being locked in code-named files (G6, G7) — quarterly refresh runs will silently diverge.

In addition, **every V1 acceptance gate that depends on an artifact (golden fixtures, eval sets) is currently hollow** — the doc names 15 round-trip fixtures and 3 AI eval sets but none have been authored. CI configured against those paths will pass vacuously.

**Recommendation:** authorise Phases R1 (schema-drift reconciliation) and R3 (doc structure) before any API/services/AI track work proceeds. R2 (code-lock for prose rules) is required before the next quarterly Meesho refresh. R4 (missing artifacts) can run in parallel with API/AI tracks but must finish before V1 launch gate. R5 (functional gaps) is V1.5-deferrable except G15 (product_drafts TTL) which is V1.

---

## Section 2 — Gap Inventory

### G1 — §2 DDL is stale relative to §5.5, §5.6, §12 (4 deltas)

**Tier:** 1
**Severity:** BLOCKER-V1
**Type:** schema-drift
**Source sections in doc:** §2.2, §2.3 (stale); §5.5.13, §5.6.4, §12.2, §12.6 (correct)
**Blast radius:** Any agent reading only §2 produces wrong schema. The database coordinator already had to make 4 deltas live during Phase 1 because §2 was outdated. The next agent reading §2 in isolation (e.g. a future api-routes-builder reviewing the data model) will be confused or, worse, "fix" the as-built schema back to §2.
**Validated:** YES — confirmed against `backend/app/models/seller_profile.py`, `template.py`, `field_alias.py`, `field_enum_value.py` and Alembic `935e55b4852c`.

The 4 specific drifts:

| # | What §2 says | What's live (correct per §5.5/§5.6/§12) | Source of correct value |
|---|---|---|---|
| 1.a | `field_aliases` has 3 columns | `field_aliases.for_xlsx_export BOOLEAN NOT NULL DEFAULT FALSE` (4 columns) | §12.2 + SSoT §6 |
| 1.b | `templates` has 5 columns | `templates.compliance_shape VARCHAR(10) NOT NULL DEFAULT 'standard'` + CHECK IN ('standard','collapsed') | §5.5.13 + §12.6 |
| 1.c | `field_enum_values.enum_values JSONB` (string array) | `field_enum_values.enum_entries JSONB` (richer entries per §5.6.4) | §5.6.4 |
| 1.d | `seller_profile` has 9 standard + 3 collapsed compliance fields (`manufacturer_details`, `packer_details`, `importer_details`) | `seller_profile` has ONLY the 9 standard fields. Combined fields are derived at export time by `CollapsedComplianceStrategy`. | §12.6 (revised) |

**Proposed fix:** Rewrite §2.2 (drop the 3 collapsed-compliance columns; rename `profile_complete` → `onboarding_complete` per G11) and §2.3 (add `for_xlsx_export` to field_aliases; add `compliance_shape` + CHECK to templates; replace `enum_values` with `enum_entries`). Cite §5.5.13 / §5.6.4 / §12 as the rationale headers above each delta. Add a one-line callout at the top of §2: "§2 is normative. Where §5.5/§5.6/§12 modify a table, the modification is backported here."
**Owner:** meesell-data-engineer (doc-only rewrite of §2.2 + §2.3)
**Estimated effort:** S (1–2 hr)
**Dependencies:** none

---

### G2 — `pricing_calcs` + `exports` DDL points to legacy V1_FEATURE_SPEC §4

**Tier:** 1
**Severity:** BLOCKER-V1
**Type:** schema-drift / doc-structure
**Source sections in doc:** §2.5 (says `CREATE TABLE pricing_calcs (...); -- per V1_FEATURE_SPEC §4` and same for `exports`)
**Blast radius:** MVP_ARCHITECTURE.md is the SSoT for V1 build. Pointing back to V1_FEATURE_SPEC (which §0 of MVP_ARCHITECTURE supersedes) creates a circular-truth problem: any agent following the breadcrumb finds an older DDL that does NOT include `exports.error_message TEXT`, which the as-built schema added per §5.5.8. V1_FEATURE_SPEC §4 also does not include `exports.user_id` (the V1_FEATURE_SPEC version has `user_id` but as a denormalisation, which the live schema does correctly with FK to users — but the legacy doc gives no rationale).
**Validated:** YES — V1_FEATURE_SPEC §4 lines 472–496 read; matches §2.5 placeholder.

Specific issues:
- The live `pricing_calcs` matches V1_FEATURE_SPEC §4 column-for-column.
- The live `exports` adds `error_message TEXT` (per §5.5.8 Celery requirement) — NOT in V1_FEATURE_SPEC §4.
- Live `exports.user_id` has FK + RESTRICT ondelete (per §10/§9 multi-tenancy). Legacy doc shows just `UUID FK`.

**Proposed fix:** Inline both `pricing_calcs` and `exports` DDL into §2.5 verbatim from the as-built models (`backend/app/models/pricing_calc.py`, `export.py`). Add `error_message TEXT NULL` with a `-- per §5.5.8` comment. Delete the V1_FEATURE_SPEC reference line.
**Owner:** meesell-data-engineer
**Estimated effort:** S (30 min)
**Dependencies:** none

---

### G3 — Section numbering collision (Sections 8/9/10/11 sub-headers)

**Tier:** 2
**Severity:** NON-BLOCKER-V1 (cosmetic but high-friction)
**Type:** doc-structure
**Source sections in doc:** §8 (line 1832, uses §9.x), §9 (line 2148, uses §10.x), §10 (line 2361, uses §11.x), §11 (line 2575, uses §11.x — **direct collision**)
**Blast radius:** Every cross-reference like "§11.6 product_drafts lifecycle" is ambiguous: does it mean Section 11 (Hand-off Contracts) or §11.6 within Section 10 (Audit Log)? `STATUS_DATABASE.md` Phase 0 table cites §10/§11.2 and §10/§11.6 — those were correct interpretations only because the database coordinator read sequentially. New agents grepping the doc will mis-route.
**Validated:** YES — grep confirms §8 → §9.x, §9 → §10.x, §10 → §11.x, §11 → §11.x.

Root cause: each section was authored as a draft (still visible in `docs/draft_architecture_section_*_*.md` files) keeping its draft-internal numbering, and the integration step that should have renumbered them when inserted into MVP_ARCHITECTURE never ran.

**Proposed fix:** Renumber all sub-headers in §8 (§9.x → §8.x), §9 (§10.x → §9.x), §10 (§11.x → §10.x), §11 (§11.x → §11.x — keep, but rename top section to "§11 — Hand-off Contracts" and force its sub-headers to §11.1, §11.2, etc.). Update every cross-reference in the same pass (~30 mentions). Also delete the orphan `docs/draft_architecture_section_*.md` files since they are superseded.
**Owner:** meesell-data-engineer (or any agent — pure text edit)
**Estimated effort:** M (2–3 hr including cross-reference sweep)
**Dependencies:** none

---

### G4 — `audit_events.id BIGSERIAL` rationale missing from §2

**Tier:** 2
**Severity:** NON-BLOCKER-V1
**Type:** doc-structure
**Source sections in doc:** §2 lists "audit_events" in §2.5 implicitly (via §2.6 migration order); actual DDL is in §11.2 (which is sub-header §11.2 within Section 10 "Audit Log")
**Blast radius:** Every other PK in the 13-table schema is UUID. `audit_events.id BIGSERIAL` is a deliberate exception (high-volume append-only table, monotonic ordering aids time-range scans). The rationale exists in the as-built model file (`audit_event.py` lines 6–12) but does not appear in §2.5 — only the deeper Audit Log section §11.2 (within Section 10) implies it.
**Validated:** YES — §2.5 mentions "audit_events" only by name; the rationale comment lives only in the ORM model file and Section 10's §11.2 prose.
**Proposed fix:** Add one bullet to §2.5 (the §2 DDL section): "`audit_events.id` is `BIGSERIAL` (not UUID) — monotonic ordering for time-range scans + zero UUID-gen overhead on the highest-volume append-only table. Full DDL in §10 (Audit Log)." Cross-reference fixed automatically when §10/§11.x renumber per G3.
**Owner:** meesell-data-engineer
**Estimated effort:** S (15 min)
**Dependencies:** G3 (so the cross-reference lands on the correct numbering)

---

### G5 — 10 vs 11 primitives — `address_group` classification ambiguous

**Tier:** 2
**Severity:** NON-BLOCKER-V1 (clarification needed)
**Type:** doc-structure
**Source sections in doc:** SSoT §4 (10 primitives, explicitly calls `address_group` a "Special composite — NOT a catalog primitive"); MVP §4.1 ("10 + 1 composite ... Total: 11 primitive components")
**Blast radius:** Frontend agent reading MVP §4.1 builds 11 primitives. Frontend agent reading SSoT §4 builds 10 primitives + an onboarding-only address-group component. Database coordinator's Phase 3 transformer (build_template_schemas.py) emits `primitive` strings drawn from a 10-element vocabulary — there is no `address_group` primitive value anywhere in `templates.schema_jsonb`. Implementation already chose 10; doc still says 11.
**Validated:** YES — `scripts/build_template_schemas.py:classify_primitive()` lines 203–259 only emit 10 primitives. SSoT §4 line 236 explicitly says address_group is "used only by the seller profile onboarding wizard, not the per-product catalog wizard".

**Proposed fix:** In MVP §4.1, change the closing sentence "Total: 11 primitive components, covering 1,831 corpus-wide field names" to "**10 primitives** cover the entire catalog-wizard field universe (1,831 names). A separate `address_group` composite is used only by the onboarding wizard — it never appears in `templates.schema_jsonb.primitive`."
**Owner:** meesell-data-engineer
**Estimated effort:** S (5 min)
**Dependencies:** none

---

### G6 — Step ID assignment rules described in prose only

**Tier:** 3
**Severity:** NON-BLOCKER-V1 (becomes BLOCKER for the first quarterly refresh)
**Type:** prose-vs-code
**Source sections in doc:** §5.6.3 (step composition algorithm in prose, with a table of `step_id` → title); §5.6.5 (parser inference rules in prose)
**Blast radius:** The step-assignment ruleset is currently embedded in `scripts/build_template_schemas.py:STEP_ASSIGNMENT` (lines 88–115, 14 ordered regex patterns) and `STEP_ORDER` (lines 118–132). At the next quarterly Meesho refresh, this script re-runs against new XLSXs — if anyone has edited the ruleset informally OR if the regex order has been shuffled, step assignment for existing leaves will drift, breaking wizard layouts seller-by-seller. Frontend renderer reads `step_id` from `schema_jsonb`; any drift mid-cycle silently re-orders wizard steps for active sellers.
**Validated:** YES — `scripts/build_template_schemas.py` lines 86–132 contain the full ruleset. §5.6.3 of the doc describes the desired outcome but contains no canonical rule list.
**Proposed fix:** Promote `STEP_ASSIGNMENT` and `STEP_ORDER` from `scripts/build_template_schemas.py` into a versioned, named module: `backend/app/i18n/step_assignment.py`. Have `build_template_schemas.py` import from there. Update §5.6.3 in the doc to say: "Step-assignment rules are locked in code at `backend/app/i18n/step_assignment.py:STEP_ASSIGNMENT` (versioned). Do not edit this list without also bumping `parser_version` and re-running the round-trip golden tests."
**Owner:** meesell-data-engineer (doc) + meesell-services-builder (code refactor, ~50 LOC move)
**Estimated effort:** S (1–2 hr including code-move + import wiring + smoke test that templates still seed identically)
**Dependencies:** none

---

### G7 — Primitive inference rules described in prose only

**Tier:** 3
**Severity:** NON-BLOCKER-V1 (becomes BLOCKER for the first quarterly refresh)
**Type:** prose-vs-code
**Source sections in doc:** §4.1 table (rules), §5.6.5 ("primitive = inferred from data_type + enum_count")
**Blast radius:** Same as G6 — the classifier is `scripts/build_template_schemas.py:classify_primitive()` (lines 203–259). If `UNIT_KEYWORDS`, `CURRENCY_PATTERNS`, or `LONG_PATTERNS` constants drift between refreshes, the primitive a field maps to changes — and the frontend dispatch switches to a different `<mee-*>` component for that field. The doc has 0 LOC of canonical rule list; the code has the only source of truth.
**Validated:** YES — `classify_primitive()` lines 218–256 implement the SSoT §4 table; doc carries the conceptual table but no canonical implementation pointer.
**Proposed fix:** Move `classify_primitive` from `scripts/` into `backend/app/i18n/primitive_classifier.py` (alongside G6's `step_assignment.py`). Add to §4.1: "Inference is locked in code at `backend/app/i18n/primitive_classifier.py:classify_primitive`. The table above is the spec; the function is the source of truth." Add a regression test (`backend/tests/test_primitive_classifier.py`) that asserts 10–20 canonical (field, expected_primitive) tuples — so any future edit to the constants surfaces immediately.
**Owner:** meesell-data-engineer (doc) + meesell-services-builder (code-move)
**Estimated effort:** S (1–2 hr)
**Dependencies:** G6 (do as one combined `backend/app/i18n/` module bundle)

---

### G8 — 15 Export Adapter golden fixtures NOT authored

**Tier:** 4
**Severity:** BLOCKER-V1
**Type:** missing-artifact
**Source sections in doc:** §5.7.3 (lists fixtures `b01_saree_10003.yaml` through `b12_electric_kettle.yaml`), §5.7.10 (CI gate `round_trip_tests`), §5.5.11 (Golden round-trip "per super-category, 12 total"; §5.7.3 says 15 — minor internal inconsistency between §5.5.11 and §5.7.3)
**Blast radius:** §5.7.10 specifies a CI job that runs `pytest backend/app/services/export_adapter/tests/test_round_trip.py`. The directory `backend/app/services/export_adapter/` **does not exist**. The CI gate will either fail loudly (test file missing → bad) or pass vacuously (no fixtures → no assertions). Either way, philosophy M6 ("Round-trip is sacred") has no enforcement at V1. The Export Adapter is the philosophical centrepiece of the architecture and currently has zero validation.
**Validated:** YES — `ls /Users/mugunthansrinivasan/Project/mesell/backend/app/services/export_adapter/` returns "No such file or directory". Also: §5.5.11 says "12 total" while §5.7.3 lists 15 — small internal inconsistency.
**Proposed fix:** Two-pronged:
1. (doc) Reconcile §5.5.11 ("12") with §5.7.3 ("15") — pick 15 (since §5.7.3 enumerates them by name with edge-case coverage justification).
2. (artifact) Author the 15 YAML fixtures per the §5.7.4 format. Each is ~50 lines of canonical_seller_profile + canonical_product + edges_tested. Total ~750 LOC of structured YAML. Coordinator co-authors with founder for product realism (e.g. the Chaat Masala product needs a credible MRP / FSSAI number).
**Owner:** meesell-services-builder (creates the directory + scaffolding + 1 example fixture); meesell-data-engineer + founder (author the 14 remaining fixtures iteratively, one super-category per session)
**Estimated effort:** L–XL (full day for scaffolding + first fixture; 2–3 hr per super-category for remaining 14 = ~2 days total)
**Dependencies:** Export Adapter implementation must reach pipeline-step-9 (round-trip validator) before fixtures can run — but fixtures can be AUTHORED in parallel (they're just YAML).

---

### G9 — 3 AI eval golden sets NOT authored

**Tier:** 4
**Severity:** BLOCKER-V1
**Type:** missing-artifact
**Source sections in doc:** §5.4 (registry lists `evals/category_picker_golden.yaml`, `autofill_golden.yaml`, `watermark_golden/`); §9.5 (eval framework specifies 50 / 30 / 30 entries respectively); §9.10 (V1 operational readiness: "Golden evals baselined")
**Blast radius:** Same as G8. The directory `evals/` does not exist. CI cannot run the eval gate. The hard guarantee that "Auto-fill ≥0% invalid enums" (§5.2 + §9.5) is unverifiable without the autofill golden set. The Smart Picker "recall ≥80% in top-5" SLA (§5.1 acceptance + §9.5) has no measuring stick. Watermark check "≥85% accuracy" has no test images.
**Validated:** YES — `ls /Users/mugunthansrinivasan/Project/mesell/evals` → No such file or directory.
**Proposed fix:**
1. Create `evals/` directory at repo root.
2. Author `category_picker_golden.yaml` (50 hand-labelled descriptions) — best done by founder + coordinator together; the founder has the seller-side intuition for "what would a typical Tirupur seller type" and which 50 categories matter most. The 50 entries should cluster: 10 from Women Fashion, 10 from Home & Kitchen, 5 each from the remaining 8 super-categories.
3. Author `autofill_golden.yaml` (30 product specs, 5 per super-category across Apparel/Grocery/Electronics/Beauty/Home).
4. Sourcing 30 sample images for `watermark_golden/`: 15 with visible watermarks (scrape competitor catalogs for examples), 15 clean.
**Owner:** meesell-ai-coordinator (owns the eval format + runner); meesell-prompt-engineer (writes the per-set conformance harness); meesell-data-engineer + founder (curate the 50 + 30 descriptions); meesell-image-precheck-builder (sources the 30 images)
**Estimated effort:** L (1 day for picker + autofill curation; ~half day for image sourcing)
**Dependencies:** None — eval sets can be authored before the AI pipeline is built; they're data-only.

---

### G10 — `product_drafts` lifecycle has no TTL or cleanup

**Tier:** 5
**Severity:** BLOCKER-V1 (low-effort but real V1 risk)
**Type:** functional-gap
**Source sections in doc:** §10 / §11.6 (the only lifecycle rules are "upsert on every PATCH; delete on successful export")
**Blast radius:** A seller who starts a product, never exports it, and never deletes it leaves a row in `product_drafts` forever. With 1,000 active sellers each starting ~2 abandoned drafts/month, that's 24K orphan rows/year (low total — but each row carries a full `draft_jsonb` of all wizard fields, potentially 5–20 KB). At V1.5 with 10,000 sellers, this becomes meaningful. More importantly: there is no operational answer to "the seller abandoned a draft, how do we surface that to them later?" without a TTL or staleness signal.
**Validated:** YES — §11.6 in MVP_ARCHITECTURE.md says "On successful POST /api/v1/exports, the corresponding product_drafts row is deleted." No other deletion path; no TTL; no archival.
**Proposed fix:** Add a single sentence to §11.6 and a Celery beat task to the cleanup section of §10:
- (doc) "Drafts older than 30 days with no PATCH activity are deleted by the nightly `cleanup_stale_drafts_task` Celery beat job. The `saved_at` column drives the staleness query."
- (code) ~15 LOC Celery beat task in `backend/app/workers/cleanup_tasks.py`: `DELETE FROM product_drafts WHERE saved_at < NOW() - INTERVAL '30 days'`. Beat schedule: 02:00 IST daily.
- Surface count to operations: log `(deleted_rows, dry_run=False)` per run.
**Owner:** meesell-services-builder (doc + beat task)
**Estimated effort:** S (1 hr including test)
**Dependencies:** none

---

### G11 — `seller_profile.profile_complete` vs `onboarding_complete` naming inconsistency

**Tier:** 1 (NEW — found during audit)
**Severity:** BLOCKER-V1 (cheap fix; high confusion cost)
**Type:** schema-drift
**Source sections in doc:** §2.2 DDL (`profile_complete BOOLEAN`); §3.2 ("`/api/v1/seller-profile → current profile + completion flag`" — calls it generically); SSoT §3 uses `onboarding_complete BOOLEAN`; as-built `backend/app/models/seller_profile.py` line 97 uses `onboarding_complete`.
**Blast radius:** The DDL in §2.2 says `profile_complete`. The SSoT and the live ORM model say `onboarding_complete`. Any agent wiring `/api/v1/seller-profile` based on §2.2 will write code that references a non-existent column and fail at runtime. The Phase 2 migration already used `onboarding_complete`.
**Validated:** YES — grepped both names; §2.2 has `profile_complete`, model and SSoT have `onboarding_complete`.
**Proposed fix:** Rename §2.2 DDL `profile_complete` → `onboarding_complete`. Add cross-reference: "naming aligned with SSoT §3 and as-built model".
**Owner:** meesell-data-engineer (folds into G1 §2.2 rewrite)
**Estimated effort:** S (5 min, part of G1)
**Dependencies:** none

---

### G12 — `seller_profile.active_super_categories` use of super_id vs super_slug is contradictory

**Tier:** 2 (NEW — found during audit)
**Severity:** NON-BLOCKER-V1 (but ambiguous for downstream agents)
**Type:** doc-structure
**Source sections in doc:** §2.2 ("Keyed by Meesho super_id (e.g. "26"="Grocery")"); §3.2 API responses key on super_id ("missing_super_category": "26"); §12 also uses super_id. **BUT** SSoT §3 line 164–166 uses string slugs: `{"grocery": {...}, "books": {...}}`. SSoT §7 table has both columns (Meesho super_id + slug).
**Blast radius:** Backend code writing into `compliance_extensions JSONB` will key either by super_id (e.g. `"26"`) or super_slug (e.g. `"grocery"`). Frontend reads it via the schema endpoint. If the convention diverges, a seller's FSSAI license stored under `"grocery"` is invisible to a query on `"26"`.
**Validated:** YES — MVP_ARCHITECTURE.md is consistent (super_id throughout); SSoT §3 uses slugs in its example JSON.
**Proposed fix:** Update SSoT §3 example JSON to use super_id strings ("26", "13", etc.) matching the as-built convention — OR document an explicit two-step lookup (super_id → slug → key). Founder ruling needed: super_id is opaque to humans (good for stability), slugs are readable (good for debugging). Recommend super_id with a `super_id_to_slug.json` constant for human-readable logs.
**Owner:** founder (ruling) + meesell-data-engineer (apply to SSoT after ruling)
**Estimated effort:** S (15 min after founder decision)
**Dependencies:** Founder ruling

---

### G13 — Caching strategy keys `templates` by `template_id`; doc never confirms that's identical to `template.id`

**Tier:** 3 (NEW — found during audit)
**Severity:** NON-BLOCKER-V1 (the natural reading is correct but the doc never says so)
**Type:** doc-structure
**Source sections in doc:** §6.4 cache key patterns: `cache:template:{template_id}:v{schema_version}` and `cache:enum:{category_id}:{canonical_field_name}:v{schema_version}`. §6.7 worker-LRU pre-warm uses `top_category_ids[:_MAX_HOT_TEMPLATES]` — and assigns it to `_TEMPLATE_LRU[cat_id]`. So is the cache key `template_id` or `category_id`?
**Blast radius:** The two §6 examples disagree silently. The schema endpoint is `/api/v1/categories/{id}/schema` (category id, not template id). Every wizard load fetches by category id; the cache should be keyed by category id, OR the route handler must resolve category → template id before cache lookup. The doc currently allows both interpretations.
**Validated:** YES — §6.4 line `cache:template:{template_id}` vs §6.7 `_TEMPLATE_LRU[cat_id]`.
**Proposed fix:** Pick one keying strategy and apply consistently in §6.4 + §6.7. Recommendation: key by `category_id` (the only thing the API knows on the request path). Internal duplication across categories that share a template is fine — `templates` are 3,557 not millions; cache memory budget (§6.9) is calculated correctly either way.
**Owner:** meesell-data-engineer (doc) + meesell-services-builder (implement consistently)
**Estimated effort:** S (30 min doc + the implementation choice falls out naturally)
**Dependencies:** none

---

### G14 — Orphan superseded draft architecture files in `docs/`

**Tier:** 3 (NEW — found during audit)
**Severity:** NON-BLOCKER-V1 (clutter)
**Type:** doc-structure
**Source sections in doc:** `docs/draft_architecture_section_6_caching.md`, `_7_search.md`, `_9_ai_ops.md`, `_10_multitenancy.md`, `_11_audit_log.md` — all in repo root `docs/`
**Blast radius:** Five files in `docs/` are clearly superseded by the final §6–§11 sections inside MVP_ARCHITECTURE.md. New agents finding them via `ls docs/` may read the draft instead of the canonical (and the draft's internal numbering is the root cause of the §8/§9/§10/§11 numbering bug G3). They're also the historical artifact that explains G3's origin.
**Validated:** YES — `ls docs/ | grep draft` returns all 5 files.
**Proposed fix:** Either (a) delete the 5 draft files (preferred — git history preserves them), or (b) move them to `docs/archive/2026-06-04-pre-integration/` with a README explaining they were the source for §6–§11 of MVP_ARCHITECTURE.md.
**Owner:** meesell-data-engineer
**Estimated effort:** S (15 min)
**Dependencies:** G3 should be done first so cross-references in the live doc don't point at the drafts.

---

### G15 — Multi-tenancy thin-defense: ContextVar for current_user_id

**Tier:** 5
**Severity:** DEFER-V1.5 (V1 acceptance is "app-level filtering + CI linter")
**Type:** functional-gap
**Source sections in doc:** §9 (Multi-tenancy) — accepts app-level filtering as the V1 trade-off; §10.4 ("Every service method ... takes user_id as explicit parameter"); §13 Risks ("Tenant isolation depends on CI linter discipline; a hotfix bypassing the lint could leak across sellers")
**Blast radius:** Currently every service method takes `user_id` explicitly. The CI linter enforces this. But the linter only catches signatures, not call sites — a future developer can still pass the wrong `user_id` (e.g. swap `current_user.id` for `target_user.id` while iterating). The database coordinator's MEMORY suggests a request-scoped `ContextVar[UUID] current_user_id` set by the JWT middleware, then read by service methods, eliminating the wrong-id swap structurally.
**Validated:** YES — §9 explicitly accepts the trade-off; the database coordinator's memory documents the proposal.
**Proposed fix:** Add a sub-section §9.11 to the doc: "Defense-in-depth: ContextVar". Implement ~30 LOC: `backend/app/middleware/auth.py` sets `current_user_id_var.set(user.id)` on JWT verification; service methods can read `current_user_id_var.get()` defensively or via a `ContextScopedSession` factory. This is a hardening pass, not a re-architecture — it does not replace explicit-parameter passing, it adds a safety net.
**Owner:** meesell-auth-builder (middleware) + meesell-services-builder (factory)
**Estimated effort:** S (1–2 hr)
**Dependencies:** none
**Founder note:** Defer-V1.5 unless founder wants a one-day hardening pre-launch. The risk is real but acceptable for V1's tenant count.

---

### G16 — `.gitlab-ci.yml` round_trip_tests path-trigger lists files that don't exist

**Tier:** 4 (NEW — found during audit)
**Severity:** BLOCKER-V1 (CI gate is hollow without these paths existing)
**Type:** missing-artifact
**Source sections in doc:** §5.7.10 (CI YAML excerpt) — triggers on changes to `backend/app/services/export_adapter/**/*`, `scripts/parse_meesho_xlsx.py`, `data/parsed/canonical_field_aliases.json`, `data/parsed/field_display_overrides.json`, `backend/alembic/versions/*templates*.py`
**Blast radius:** Even setting aside G8 (no fixtures), the CI job in `.gitlab-ci.yml` references `scripts/parse_meesho_xlsx.py` — which does not exist. The actual parser is `scripts/build_template_schemas.py` (transformer) and the XLSX-parser logic was historically embedded in `data/parsed/` batch generation. Also `backend/alembic/versions/*templates*.py` matches the baseline `935e55b4852c_v1_baseline_13_tables.py` only weakly (no "templates" substring) — so a templates schema migration would NOT trigger the round-trip gate.
**Validated:** YES — `scripts/` lists `build_template_schemas.py`, `seed_*.py`; no `parse_meesho_xlsx.py` exists.
**Proposed fix:** Update §5.7.10 CI YAML to reference real file paths:
- Change `scripts/parse_meesho_xlsx.py` → `scripts/build_template_schemas.py` (the transformer; the actual XLSX parser is delegated to xlsx-parser agent and outputs into `data/parsed/`)
- Change `backend/alembic/versions/*templates*.py` → broaden to `backend/alembic/versions/*.py` (any schema migration could affect round-trip)
- Add `data/parsed/leaf_id_to_schema_hash.json` to the triggers (since it's the join between templates and categories)
**Owner:** meesell-data-engineer (doc fix); meesell-services-builder owns the actual .gitlab-ci.yml when CI track lands
**Estimated effort:** S (15 min doc fix)
**Dependencies:** G8 (fixtures must exist for CI to do anything)

---

### G17 — `meesell-test-writer` and `meesell-deployer` referenced but explicitly "not created"

**Tier:** 3 (NEW — found during audit)
**Severity:** NON-BLOCKER-V1 (acknowledged in CLAUDE.md)
**Type:** doc-structure
**Source sections in doc:** §5.7.11 ("smoke-test runbook ... owned by `meesell-deployer` when registered"); CLAUDE.md ("Deferred to V1.5: `meesell-brand-master-builder`... `meesell-test-writer` and `meesell-deployer` are not created at this stage")
**Blast radius:** The architecture punts ownership of `docs/release_runbook.md` to an agent that doesn't exist. Same with the round-trip golden test maintenance (§5.7.7) which is split between `meesell-scraper-maintainer` and an implicit "engineer investigates" handoff. For V1 launch, *someone* has to own the smoke test against Meesho's staging panel.
**Validated:** YES — confirmed against CLAUDE.md MeeSell agent ecosystem rules.
**Proposed fix:** Update §5.7.11 to assign smoke-test runbook ownership for V1: "Owned by meesell-data-engineer + founder for V1; transitions to meesell-deployer when that agent is created (V1.5)." Same in §5.7.7. No new agent needed; just explicit interim ownership.
**Owner:** meesell-data-engineer (doc)
**Estimated effort:** S (10 min)
**Dependencies:** none

---

### G18 — `category_attributes.json` in CLAUDE.md / data dir doesn't match the as-built schema layer

**Tier:** 3 (NEW — found during audit)
**Severity:** NON-BLOCKER-V1 (legacy reference)
**Type:** doc-structure
**Source sections in doc:** CLAUDE.md (`backend/app/data/category_attributes.json` — listed in the project structure tree); meesell-data-engineer spec ("xlsx-parser → category_attributes.json"); but the as-built seed pipeline writes to the `templates`, `categories`, `field_enum_values` tables — NOT to a flat `category_attributes.json` file.
**Blast radius:** New agents reading CLAUDE.md think there's a static JSON file driving schema. There isn't — schema is live in Postgres tables. Any code referencing `backend/app/data/category_attributes.json` will hit a missing file.
**Validated:** PARTIAL — verified that the meesell-data-engineer agent spec (this agent's spec) still calls out `category_attributes.json` as a derived artifact. The on-disk artifact `data/parsed/leaf_id_to_schema_hash.json` exists, plus per-batch `batch_*.json` files; no top-level `category_attributes.json` is generated by the V1 pipeline.
**Proposed fix:** In CLAUDE.md (NOT in this analysis — but flag for follow-up), drop `category_attributes.json` from the project tree. Replace with: "schema lives in Postgres `templates`/`categories`/`field_enum_values`/`field_aliases` tables; seed inputs are `data/parsed/batch_*.json`." Same in the meesell-data-engineer agent spec.
**Owner:** founder (CLAUDE.md is founder-owned) + meesell-data-engineer (own agent spec)
**Estimated effort:** S (15 min)
**Dependencies:** none

---

## Section 3 — New gaps surfaced by this audit (not in starting list)

Five new gaps were found in addition to validating the database coordinator's 11:

**G11** (profile_complete vs onboarding_complete) — the **highest-impact new finding**. Database coordinator implemented the SSoT name (`onboarding_complete`), which is correct, but §2.2 of the architecture doc says `profile_complete`. Any new API agent reading §2.2 in isolation will write broken code.

**G12** (super_id vs super_slug) — silent disagreement between MVP_ARCHITECTURE (super_id) and SSoT (slugs). Founder ruling needed.

**G13** (cache key — template_id vs category_id) — §6.4 and §6.7 use different identifiers in their examples. Caching will work either way, but two consumers will diverge.

**G14** (orphan draft files in docs/) — root cause of G3 numbering bug; should be archived or deleted.

**G16** (`.gitlab-ci.yml` path-triggers reference non-existent scripts) — quietly the most dangerous of the new finds: a CI gate that won't fire because no file matches its trigger looks "green" while doing nothing.

**G17** (orphan agent ownership) — referenced ownership for `meesell-deployer` despite CLAUDE.md saying that agent doesn't exist yet.

**G18** (CLAUDE.md tree references obsolete `category_attributes.json`) — minor but real.

**Three most surprising:**

1. **G16** — the CI gate is doubly hollow: no fixtures (G8) AND wrong paths in the trigger. Even after authoring fixtures, the gate wouldn't fire on relevant changes.
2. **G11** — the architecture, SSoT, and as-built schema use three different sources of truth for one boolean column name. The DB has the right one only because the database coordinator deliberately followed the SSoT over §2.
3. **G13** — caching code is the kind of place where "category_id vs template_id" goes unnoticed until the second consumer wires up against a different identifier. The doc invites the bug.

**Systemic pattern observed:** Every section authored as a `draft_architecture_section_N_*.md` file (the 5 still in `docs/`) was inserted into MVP_ARCHITECTURE.md as Section (8/9/10/11) without renumbering its internal sub-headers. This is the root cause of G3, and it indirectly created G14 (orphan files). A simple integration discipline — "when promoting a draft to a section, renumber and delete the draft" — would have prevented both.

---

## Section 4 — Reconciliation Execution Plan

Five phases. Each phase lists gaps covered, the agent + dispatch summary, and total effort.

### Phase R1 — Schema-drift reconciliation (Tier 1)

**Gaps covered:** G1, G2, G11
**Effort:** S (3–4 hr total)
**Founder approval required:** YES (doc rewrite of normative §2)
**Dispatch:**
- Agent: `meesell-data-engineer` (this agent)
- Task: Rewrite §2.2 (drop 3 collapsed columns; rename `profile_complete` → `onboarding_complete`); rewrite §2.3 (add `for_xlsx_export`; add `compliance_shape` + CHECK; replace `enum_values` with `enum_entries`); inline `pricing_calcs` and `exports` DDL into §2.5 verbatim from as-built models; add the §5.5.8 `error_message TEXT NULL` comment.
- Output: PR-sized diff to `docs/MVP_ARCHITECTURE.md` only. No model, no migration, no schema change.

### Phase R2 — Code-lock for prose-only rules (Tier 3)

**Gaps covered:** G6, G7
**Effort:** S (2–3 hr)
**Founder approval required:** NO (refactor + doc cross-reference)
**Dispatch:**
- Agent: `meesell-services-builder` (code-move) + `meesell-data-engineer` (doc)
- Task: Create `backend/app/i18n/step_assignment.py` and `backend/app/i18n/primitive_classifier.py`. Move `STEP_ASSIGNMENT`, `STEP_ORDER`, `classify_primitive` from `scripts/build_template_schemas.py` into these named modules. Have the script import them. Add regression test in `backend/tests/test_primitive_classifier.py` with ~15 (field, expected_primitive) tuples covering all 10 primitives. Update §4.1 and §5.6.3 in the doc to point to the new file paths as the source of truth.
- Output: ~80 LOC moved + ~50 LOC test + 2 small doc edits.
- Gate: Re-running `seed_all.py` produces identical row counts (3566 templates, etc.).

### Phase R3 — Doc structure / readability (Tier 2)

**Gaps covered:** G3, G4, G5, G12, G13, G14, G17, G18
**Effort:** M (4–6 hr including cross-reference sweep)
**Founder approval required:** YES for G12 (super_id vs slug ruling) and G18 (CLAUDE.md edit). Others are pure cosmetic.
**Dispatch:**
- Agent: `meesell-data-engineer` (doc edits) + founder (rulings on G12, G18)
- Task: Renumber §8/§9/§10/§11 sub-headers (G3). Add BIGSERIAL rationale to §2.5 (G4). Reconcile primitive count to 10 (G5). After founder ruling on G12, update SSoT §3 example JSON. Pick `category_id` for cache keys in §6.4 + §6.7 (G13). Archive or delete the 5 `docs/draft_architecture_section_*.md` files (G14). Clarify §5.7.7 + §5.7.11 ownership for V1 (G17). Founder updates CLAUDE.md project tree to remove `category_attributes.json` reference (G18).
- Output: All doc-only edits. No code changes.

### Phase R4 — Missing artifacts (Tier 4)

**Gaps covered:** G8 (fixtures), G9 (eval sets), G16 (CI YAML paths)
**Effort:** XL (3–4 days total, parallelisable)
**Founder approval required:** YES (founder co-authors fixtures + eval sets for realism)
**Dispatch (3 parallel sub-dispatches):**
1. **G8 — Round-trip fixtures:**
   - Agent: `meesell-services-builder` scaffolds `backend/app/services/export_adapter/tests/golden_fixtures/` + 1 example. `meesell-data-engineer` + founder co-author the remaining 14 (one super-category per session).
   - Effort: ~2 days (founder time-bounded)
2. **G9 — AI eval golden sets:**
   - Agent: `meesell-ai-coordinator` owns format + runner. `meesell-prompt-engineer` writes the per-set harness. `meesell-data-engineer` + founder curate the 50 picker descriptions + 30 autofill specs. `meesell-image-precheck-builder` sources 30 watermark sample images.
   - Effort: ~1.5 days (founder time-bounded for the curation steps)
3. **G16 — CI YAML path fix:**
   - Agent: `meesell-services-builder` (when CI track activates) — but the doc fix is `meesell-data-engineer` now.
   - Effort: 30 min doc + a few lines of .gitlab-ci.yml edit during CI track.

**Acceptance gate:** §5.7.10 CI job runs on a stub commit and exits non-zero if any fixture fails; §9.5 eval runner exits non-zero if recall < 80% / invalid enums > 0% / watermark accuracy < 85%.

### Phase R5 — Functional gaps (Tier 5)

**Gaps covered:** G10 (product_drafts TTL — V1), G15 (ContextVar — defer V1.5)
**Effort:** S (1 hr for G10; G15 deferred)
**Founder approval required:** YES (TTL value: 30 days proposed; ContextVar defer-or-do decision)
**Dispatch:**
- Agent for G10: `meesell-services-builder` — add `cleanup_stale_drafts_task` Celery beat task; doc one sentence in §11.6.
- Agent for G15: `meesell-auth-builder` (V1.5 — unless founder authorizes one-day hardening pre-launch)

---

## Section 5 — What this analysis is NOT proposing

To prevent scope creep, this analysis explicitly **does NOT** propose:

- **No schema migrations.** Database is locked at `935e55b4852c`. All deltas are doc-side reconciliation, not code-side change.
- **No new tables.** All 13 tables stay.
- **No re-seeding.** Counts (field_aliases=67, templates=3566, categories=3772, field_enum_values=49259) stay.
- **No re-architecting locked decisions.** §12 founder decisions stay as-is. Where a section drifted from §12 (e.g. §2.2 still has the 3 collapsed columns dropped by §12.6), this analysis fixes the drift in §2 — it does NOT touch §12.
- **No new agents.** `meesell-deployer` and `meesell-test-writer` stay deferred (G17 resolves with interim ownership).
- **No revisiting CORE_PHILOSOPHY.md.** All 10 mandates + 8 forbids + 5 patterns stay locked.
- **No data model change for multi-tenancy.** RLS stays V1.5 per §9.2; G15 ContextVar is the only V1 hardening considered, and only if founder authorizes.

### Sidebar — agreements with §12 locked decisions

This analysis **agrees with every §12 founder-locked decision**, including the ones the database coordinator surfaced as friction points. Specifically:

- §12.6 (Eye-Serum: collect 9 standard, transform at export) is the right call. The drift in §2.2 (still showing 3 collapsed columns) is a documentation bug, not a re-litigation of §12.6.
- §12.4 (Group ID behind Advanced fields toggle) is the right call. No revisiting.
- §12.2 (Meesho typos: auto-correct internally, restore on export) is the right call. The `for_xlsx_export` column is the correct implementation.

No founder-locked decision is being challenged. All proposed work backports §12's decisions to the sections where they're missing.

---

## Section 6 — Recap for founder review

| Phase | Gaps | Effort | V1 blocker? | Need founder approval to start? |
|---|---|---|---|---|
| R1 — Schema-drift reconciliation | G1, G2, G11 | 3–4 hr | YES (3 BLOCKER-V1) | Yes (rewriting normative §2) |
| R2 — Code-lock for prose rules | G6, G7 | 2–3 hr | No (becomes blocker before next quarterly refresh) | No |
| R3 — Doc structure | G3, G4, G5, G12, G13, G14, G17, G18 | 4–6 hr | No | Partial (G12, G18 need ruling) |
| R4 — Missing artifacts | G8, G9, G16 | 3–4 days | YES (G8 BLOCKER; G9 BLOCKER) | Yes (founder co-authors content) |
| R5 — Functional gaps | G10, G15 | 1 hr V1; G15 deferred | G10 yes (V1), G15 no | Yes for both |

**Total V1 effort if all approved:** ~5–6 person-days, of which ~3–4 days is founder-bounded (R4 content authoring).

**Recommended dispatch order:**
1. **R1 + R3** (parallel, doc-only) — unblock downstream agents reading §2 + §6 + §9 + §10 + §11 with accurate information. Half day.
2. **R2** (parallel with R1/R3) — small, mechanical, no founder time needed. Half day.
3. **R5 G10** (immediately after R1) — small Celery beat task.
4. **R4** (sequential, founder-time-bounded) — author golden fixtures and eval sets. Founder co-authors. Spread over 2–3 sessions.

---

*End of gap analysis. Awaiting founder review and authorisation of phases.*

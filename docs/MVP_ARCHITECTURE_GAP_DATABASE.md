# MVP Architecture Gaps — DATABASE TRACK SCOPE

**Owner:** DATABASE coordinator (mesell-database-session-2)
**Date:** 2026-06-05
**Status:** DRAFT — pending founder review
**Parent doc:** `docs/MVP_ARCHITECTURE_GAP_ANALYSIS.md` (full 18-gap analysis by meesell-data-engineer)

**Scope discipline:** This is the database-only filter of the parent analysis. Gaps that touch backend services, frontend, AI pipeline, CI, or infra are flagged in §3 (Out-of-Scope Tracker) and routed to the master session for assignment to the appropriate track.

---

## Section 1 — Database-Owned Gaps (8 gaps)

These touch the database schema (`backend/app/models/`, `backend/alembic/versions/`), seed pipeline (`scripts/seed_*.py`, `scripts/build_template_schemas.py`), or the table lifecycle (TTL, cleanup, audit semantics).

### G1 — §2 DDL stale relative to live schema (4 schema deltas)

**Severity:** BLOCKER-V1
**Type:** schema-drift
**Source:** `docs/MVP_ARCHITECTURE.md` §2.2, §2.3 (stale); §5.5.13, §5.6.4, §12.2, §12.6 (correct)
**Status in DB:** Already correct. Phase 1 applied all 4 deltas to live schema.
**Risk:** Any future agent reading §2 in isolation will write code referencing non-existent columns OR try to "fix" the live schema back to the stale §2 shape.

**The 4 deltas (already live in Postgres):**

| # | §2 says | Live in DB | Source of truth |
|---|---|---|---|
| 1a | `field_aliases` has 3 columns | + `for_xlsx_export BOOLEAN NOT NULL DEFAULT FALSE` (4 columns) | §12.2 + SSoT §6 |
| 1b | `templates` has 5 columns | + `compliance_shape VARCHAR(10) NOT NULL DEFAULT 'standard'` + CHECK | §5.5.13 + §12.6 |
| 1c | `field_enum_values.enum_values JSONB` (simple array) | `enum_entries JSONB` (richer per §5.6.4) | §5.6.4 |
| 1d | `seller_profile` has 9 + 3 collapsed compliance fields | only 9 standard fields (collapsed dropped) | §12.6 revised |

**Database-track action:** Doc rewrite of §2.2 + §2.3 is data-engineer territory (they own MVP_ARCHITECTURE.md). My role: provide the as-built schema as the source of truth + verify post-edit that the rewritten §2 matches live DB column-for-column.

**Effort:** S (1-2 hr — data-engineer writes; I verify)

---

### G2 — `pricing_calcs` + `exports` DDL still points to legacy V1_FEATURE_SPEC §4

**Severity:** BLOCKER-V1
**Type:** schema-drift / doc-structure
**Source:** §2.5 placeholder `-- per V1_FEATURE_SPEC §4`
**Status in DB:** Live. `exports.error_message TEXT NULL` (added per §5.5.8) is in the model and DDL; V1_FEATURE_SPEC does not have this column.

**Risk:** V1_FEATURE_SPEC is the legacy doc MVP_ARCHITECTURE supersedes. Any agent following the breadcrumb finds outdated DDL.

**Specific drift:**
- Live `pricing_calcs` matches V1_FEATURE_SPEC column-for-column ✓
- Live `exports` adds `error_message TEXT NULL` (per §5.5.8 — Celery surfaces failure to polling endpoint) — NOT in legacy doc
- Live `exports.user_id` has explicit FK to users(id) — legacy doc shows it without FK semantics

**Database-track action:** Provide as-built DDL extracted from `backend/app/models/pricing_calc.py` + `backend/app/models/export.py` to data-engineer for inlining into §2.5. Delete V1_FEATURE_SPEC reference line.

**Effort:** S (30 min)

---

### G4 — `audit_events.id BIGSERIAL` rationale missing from §2

**Severity:** NON-BLOCKER-V1
**Type:** doc-structure (schema-rationale gap)
**Source:** §2.5 mentions audit_events only by name; rationale lives in `backend/app/models/audit_event.py` comment + Section 10 prose

**Risk:** Every other PK is UUID. `audit_events.id BIGSERIAL` is a deliberate exception (high-volume append-only, monotonic ordering aids time-range scans, zero UUID-gen overhead). The decision is sound but undocumented in the DDL section.

**Database-track action:** Add a one-line bullet to §2.5 explaining why `audit_events.id` is BIGSERIAL not UUID, with cross-reference to §10 (Audit Log) for full DDL.

**Effort:** S (15 min)

---

### G6 — Step ID assignment rules in prose only (no canonical code module)

**Severity:** NON-BLOCKER-V1 (becomes BLOCKER before first quarterly Meesho refresh)
**Type:** prose-vs-code
**Source:** §5.6.3 describes step composition in prose; live implementation is `scripts/build_template_schemas.py:STEP_ASSIGNMENT` (lines 88-115) + `STEP_ORDER` (lines 118-132)

**Risk:** Step assignment ruleset is currently buried inside the seed script. At the next quarterly refresh, if regex order shuffles or rules drift, `templates.schema_jsonb.fields[*].step_id` drifts → frontend wizard re-orders steps for active sellers mid-cycle.

**Database-track action:** Promote `STEP_ASSIGNMENT` + `STEP_ORDER` from `scripts/build_template_schemas.py` into versioned module `backend/app/i18n/step_assignment.py`. Seed script imports from there. Add regression test pinning ~15 (field_name, expected_step_id) tuples.

**Effort:** S (1-2 hr — code-move + import wiring + regression test + smoke that re-seed produces identical `step_id` values)

---

### G7 — Primitive inference rules in prose only (no canonical code module)

**Severity:** NON-BLOCKER-V1 (becomes BLOCKER before first quarterly Meesho refresh)
**Type:** prose-vs-code
**Source:** §4.1 + §5.6.5 in prose; live implementation is `scripts/build_template_schemas.py:classify_primitive()` (lines 203-259) with constants `UNIT_KEYWORDS`, `CURRENCY_PATTERNS`, `LONG_PATTERNS`

**Risk:** Same as G6 — silent drift between quarterly refreshes. The primitive a field maps to determines which `<mee-*>` component the frontend renders. A drifted classifier silently swaps components for affected fields.

**Database-track action:** Move `classify_primitive()` + its constants from `scripts/` into `backend/app/i18n/primitive_classifier.py` (alongside G6's `step_assignment.py`). Seed script imports from there. Add regression test `backend/tests/test_primitive_classifier.py` with ~15 canonical tuples.

**Effort:** S (1-2 hr — do together with G6 as combined `backend/app/i18n/` bundle)

**Dependencies:** G6 (combine into one dispatch)

---

### G10 — `product_drafts` lifecycle has no TTL or cleanup

**Severity:** BLOCKER-V1 (low-effort, real V1 operational risk)
**Type:** functional-gap
**Source:** §10 / §11.6 — only lifecycle rule is "upsert on PATCH; delete on successful export". No path for abandoned drafts.

**Risk:** A seller starts a wizard, walks away, never returns. Row sits in `product_drafts` forever. `draft_jsonb` is 5-20 KB per row. At 1,000 sellers × 2 abandonments/month = 24K orphan rows/year carrying ~300 MB. At V1.5 with 10K sellers, this becomes meaningful — but also: there's no operational signal to surface "you have stale drafts" to sellers.

**Database-track action:** Define the TTL contract (proposed: 30 days from `saved_at` with no PATCH activity → DELETE). Implementation is a Celery beat task owned by services-builder, but the database track must:
1. Confirm `product_drafts.saved_at` is the right staleness driver (it is — already indexed implicitly via PK)
2. Add the deletion SQL to the doc: `DELETE FROM product_drafts WHERE saved_at < NOW() - INTERVAL '30 days'`
3. Hand off task creation to services-builder

**Effort:** S (15 min from database side; 1 hr total including services-builder doing the Celery beat task)

**Founder decision needed:** TTL value — 30 days proposed. Confirm or override.

---

### G11 — `seller_profile.profile_complete` vs `onboarding_complete` naming inconsistency

**Severity:** BLOCKER-V1 (cheap fix, high confusion cost)
**Type:** schema-drift
**Source:** MVP §2.2 DDL says `profile_complete`. SSoT §3 + live ORM model use `onboarding_complete`.
**Status in DB:** Live column is `onboarding_complete` (correct per SSoT). Phase 1 + Phase 2 used the SSoT name.

**Risk:** Any agent reading §2.2 in isolation will write API code referencing `profile_complete` and 500 at runtime.

**Database-track action:** Folds into G1 §2.2 rewrite. No DB change needed (column already correct).

**Effort:** S (5 min, part of G1)

---

### G12 — `seller_profile.compliance_extensions` JSONB keying — super_id vs super_slug

**Severity:** NON-BLOCKER-V1 (ambiguous for downstream agents)
**Type:** schema-drift (in the JSONB shape contract)
**Source:** MVP §2.2 example uses `super_id` strings ("26", "13"). SSoT §3 lines 164-166 example uses slug strings ("grocery", "books"). MVP §3.2 API responses use super_id.
**Status in DB:** JSONB structure is undefined at the column level (it's free-form). The convention only exists in code that writes/reads it.

**Risk:** Backend code writing `compliance_extensions["26"]` will be invisible to a query against `compliance_extensions["grocery"]`. Founder ruling needed for which key style.

**Database-track action:** Surface the ambiguity. Recommend `super_id` (opaque but stable; slugs are human-readable but drift-prone). If founder rules super_id, add a `backend/app/constants/super_categories.py` constant `SUPER_ID_TO_SLUG = {"26": "grocery", "13": "kids_toys", ...}` so logs and queries can be human-readable without changing storage.

**Effort:** S (15 min after founder ruling — DDL is unchanged; only the JSONB convention is documented)

**Founder decision needed:** super_id (recommended) or super_slug?

---

## Section 2 — Database-Adjacent Gaps (2 gaps)

These touch our storage but the policy decision lives in another track. Flagged for context; not my track's action.

### G5 — 10 vs 11 primitives, `address_group` classification ambiguous

**Why adjacent:** We store `primitive` strings in `templates.schema_jsonb.fields[*].primitive`. The seed pipeline (Phase 3) already chose a 10-element vocabulary (no `address_group` value emitted). The doc still says 11 in MVP §4.1. The vocabulary choice affects what backend services and the frontend dispatch on.

**Database-track action:** None. Surface to the master session — frontend track owns the decision (is `address_group` a stored primitive or just an onboarding-only wizard composite?).

**Status:** Database implementation already aligns with SSoT §4 (10 primitives). Doc needs to match — but that's data-engineer + frontend coordination.

---

### G18 — `category_attributes.json` in CLAUDE.md references obsolete artifact

**Why adjacent:** CLAUDE.md project tree lists `backend/app/data/category_attributes.json` as a seed input. It's not — V1 seed inputs are `data/parsed/batch_*.json` files (which Phase 3 consumed). No `category_attributes.json` is generated by the V1 pipeline.

**Database-track action:** None directly. Surface to the master session — founder owns CLAUDE.md.

**Status:** Database track is unaffected (we already use the correct inputs). Cleanup is hygiene.

---

## Section 3 — Out-of-Scope Tracker (8 gaps → other tracks)

Flagged here for the master session to route to the right coordinators. **Database track will not action these.**

| Gap | Owner track | One-line summary |
|---|---|---|
| G3 | data-engineer (doc structure) | §8/§9/§10/§11 sub-header numbering broken; collisions every cross-reference |
| G8 | services-builder + data-engineer | 15 Export Adapter golden fixtures unauthored; `backend/app/services/export_adapter/` doesn't exist; round-trip CI gate hollow |
| G9 | ai-coordinator + prompt-engineer | 3 AI eval golden sets (`evals/category_picker_golden.yaml`, `autofill_golden.yaml`, `watermark_golden/`) unauthored |
| G13 | services-builder (caching) | §6.4 cache key uses `template_id`; §6.7 LRU uses `cat_id`; two consumers will diverge |
| G14 | data-engineer (doc hygiene) | 5 orphan `docs/draft_architecture_section_*.md` files superseded but not removed |
| G15 | auth-builder + services-builder (V1.5) | ContextVar for `current_user_id` defense-in-depth; DEFER-V1.5 per founder §9.2 acceptance |
| G16 | services-builder (CI) | `.gitlab-ci.yml` round_trip_tests path-triggers reference non-existent `scripts/parse_meesho_xlsx.py` |
| G17 | data-engineer (ownership) | §5.7.7 + §5.7.11 reference `meesell-deployer` which CLAUDE.md says is "not created at this stage" |

---

## Section 4 — Database Track Reconciliation Plan

Three focused dispatches handle the 8 database-owned gaps:

### DR1 — Provide as-built DDL for §2 rewrite (supports G1, G2, G4, G11)

**What database track does:**
1. Extract live DDL from `backend/app/models/` for the 4 G1 drifted tables + `pricing_calcs` + `exports` (G2)
2. Document `audit_events.id BIGSERIAL` rationale (G4)
3. Confirm `onboarding_complete` is the column name (G11 — already done in Phase 1)
4. Hand to meesell-data-engineer for the §2 doc rewrite
5. Post-rewrite: verify §2 matches live DB column-for-column

**Effort:** S (1 hr from database side — extract + verify)
**Founder approval:** Yes (rewriting normative §2)

### DR2 — Code-lock the seed pipeline rules (G6 + G7 combined)

**What database track does:**
1. Refactor `scripts/build_template_schemas.py`:
   - Move `STEP_ASSIGNMENT` + `STEP_ORDER` → `backend/app/i18n/step_assignment.py`
   - Move `classify_primitive()` + its constants → `backend/app/i18n/primitive_classifier.py`
2. Update seed script to import from new modules
3. Add `backend/tests/test_primitive_classifier.py` and `test_step_assignment.py` — each with ~15 canonical tuples
4. Smoke test: re-run `seed_all.py` and confirm row counts identical (3566 templates, 49259 enum values)
5. Update doc (§4.1 + §5.6.3) to point at the new file paths as source of truth (data-engineer does the doc edit)

**Effort:** S (2-3 hr)
**Founder approval:** Not required (refactor + doc cross-reference)

### DR3 — Lock `product_drafts` TTL contract (G10) + super_id convention (G12)

**What database track does:**
1. Add `idx_product_drafts_saved_at` index on `saved_at` for cleanup query performance (~5 LOC migration — new revision after `935e55b4852c`)
2. Document the TTL contract in §11.6: "Drafts older than 30 days deleted nightly by `cleanup_stale_drafts_task`. `saved_at` drives staleness."
3. After founder rules on G12 (super_id vs super_slug): document the JSONB key convention in §2.2 + add `backend/app/constants/super_categories.py` if needed
4. Hand off Celery beat task creation to services-builder (out of database scope but coordinated)

**Effort:** S (30 min from database side; needs founder ruling on G10 TTL value + G12 keying)
**Founder approval:** Yes (TTL value + super_id ruling)

---

## Section 5 — Founder Decisions Awaiting Input

Three decisions block database track reconciliation:

1. **G10 — `product_drafts` TTL value.** Recommended: 30 days from last `saved_at`. Confirm or override?
2. **G12 — `compliance_extensions` JSONB key style.** Recommended: `super_id` strings (e.g., `"26"`) with a `SUPER_ID_TO_SLUG` constant for human readability. Confirm or override (super_slug)?
3. **DR1 dispatch authorization.** Rewriting normative §2 requires founder sign-off. Authorize meesell-data-engineer to proceed with as-built DDL provided by database track?

---

## Section 6 — What Database Track is NOT Doing

To prevent scope creep:

- No new schema migration beyond G10's tiny `idx_product_drafts_saved_at` index (and only after founder authorizes)
- No re-seeding (counts stay: field_aliases=67, templates=3566, categories=3772, field_enum_values=49259)
- No touching MVP_ARCHITECTURE.md directly (data-engineer owns it; database track supplies as-built DDL as the source of truth)
- No work on Export Adapter (G8), AI evals (G9), caching (G13), CI YAML (G16), ContextVar (G15), or any other non-database gap — those route to their respective tracks via the master session
- No touching CLAUDE.md (founder-owned)

---

*End of database-track gap view. Awaiting founder decision on §5 items before launching DR1/DR2/DR3.*

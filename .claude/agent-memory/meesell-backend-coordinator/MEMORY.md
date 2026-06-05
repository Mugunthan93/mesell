# Memory — meesell-backend-coordinator

## Agent Identity
Backend coordinator for MeeSell. Orchestrates the 4 backend specialists (database, api-routes, services, auth). Owns STATUS_BACKEND.md, integration tests, contract cohesion. Decentralized memory ecosystem.

## MEMORY.md (Index)
- [project_session_2_gap_pass.md](project_session_2_gap_pass.md) — 2026-06-05 gap remediation plan, audit of 10 routers, 5 gaps identified
- [reference_authoritative_endpoint_inventory.md](reference_authoritative_endpoint_inventory.md) — founder ruling that §3+§7.7+§11.6 = 25 endpoints supersedes §11.1's stale "16+4=20"
- [reference_isadvanced_state.md](reference_isadvanced_state.md) — is_advanced is ALREADY wired in build_template_schemas.py line 291 for group_id; the founder-flagged "never wired" claim is partially incorrect — gap is narrower (no override entries in field_display_overrides.json beyond group_id, and seed never re-run after the changes)

## Recurring patterns observed
- Founder's gap descriptions are directionally right but exact mechanics worth verifying — verify the actual code state before quoting the gap shape in a plan
- §11.1 of MVP_ARCHITECTURE is stale on multiple counts (model count: says 8, actually 13; endpoint count: says 20, actually ~25). Treat §3+§7.7+§11.6 as authoritative per founder ruling 2026-06-05
- backend/app/models/ has NO sku.py or image.py — those names were renamed to product.py and product_image.py in the burn-and-rebuild. 4 of 10 routers still import the deleted names

## Founder decisions referenced this session
- §11.1 endpoint count is stale; use §3+§7.7+§11.6 = 25 endpoints (founder 2026-06-05)
- RLS deferred to V1.5 (app-level user_id scoping for V1)
- §12.4: is_advanced metadata gates Group ID behind "Advanced fields" toggle
- §12.2: field_aliases.for_xlsx_export reverses canonical → raw on Meesho XLSX emit

## Dispatch caveats
- This turn had NO Agent tool available — coordinator-direct analysis used in lieu of dispatching meesell-database-builder + meesell-api-routes-builder in parallel. Construction phase MUST be launched from a parent session that has Agent dispatch.

## Session 2 close-out — 2026-06-05 (mesell-backend-session-2)

### What landed this session
Gap pass closed in full, plus residual cleanup. Backend is now construction-ready (not started).

- **G1** — is_advanced wiring verified for canonical_name="group_id" only (single-element ADVANCED_CANONICAL_NAMES). Seed re-run idempotently; 2 new section-H tests in `backend/tests/test_database.py` validate the flag. Test suite 42/42.
- **G2 / G3** — Legacy router/schema/service/worker/test purge complete. 25 files deleted in total: 9 routers, 6 schemas, 4 services, 3 workers, 10 tests, 2 already-renamed models. `backend/app/main.py` mounts ONLY `auth_router`; 9 routes on the app.
- **G4** — pg_trgm extension + 3 GIN trgm indexes shipped via `backend/alembic/versions/a1b2c3d4e5f6_pg_trgm_and_category_gin.py`. Alembic env.py patched with `transaction_per_migration=True` to allow `autocommit_block()`. Head chain: `a1b2c3d4e5f6 -> f31c75438e61`. Round-trip downgrade/upgrade clean. Bitmap Index Scan confirmed via EXPLAIN ANALYZE.
- **G5** — Auth URL paths rewritten to §3.1: `/send-otp -> /otp/send`, `/verify-otp -> /otp/verify`. Tests + conftest updated.
- **Residual cleanup** — 3 dead worker modules removed; 7 dead test files removed; `celery_app.py` modified to `include=[]` + `task_reject_on_worker_lost=True`; deleted-queue routes pruned.

### Construction-readiness state
All 6 acceptance conditions from the gap-pass plan are satisfied. Boot integration 7/7 PASS, DB schema 42/42 PASS, zero import errors, zero collection errors, zero URL-mismatch failures. Infrastructure-dependent tests (Postgres tunnel / Valkey) fail as pre-existing.

### Queued for construction (do NOT treat as session-3 blockers — these are construction work items)
1. **services/pricing_engine.py latent import bug** — line 23 imports `from app.schemas.pricing import PricingAlert`; the schema module was deleted in G3. The file is unimportable but no live importer hits it today (main.py does not register a pricing router). Construction-phase fix: re-author `schemas/pricing.py` with `PricingAlert` (and the rest of the Feature 7 contract), OR refactor pricing_engine.py to use a plain dataclass / inline Pydantic model. Decide during the Feature 7 dispatch, not before.
2. **§3.4 doc amendment promise** — the gap-pass plan agreed to defer reconciliation of MVP_ARCHITECTURE.md §3.4 (catalog / product endpoint surface wording) to the construction phase. When the Feature 2 / Feature 3 endpoints land, update §3.4 in the same dispatch to match the implemented shape. Do not let this drift.
3. **§11.1 stale-count nuance** — §11.1 says "20 endpoints / 8 models". Founder ruling 2026-06-05: this line is STALE. Authoritative counts come from §3 + §7.7 + §11.6 (25 endpoints) and the live DB (13 tables). Future audits MUST quote §3 + §7.7 + §11.6, not §11.1. A construction-phase doc amendment can correct §11.1 inline, but until then, the cross-reference is "ignore §11.1 counts; trust §3/§7.7/§11.6 + alembic head".

### Decisions locked this session (record for session 3)
- D1: Legacy code deleted outright, no archive branch.
- D2: is_advanced gates ONLY `group_id`. Do not expand the set without a spec change.
- D3: §3.4 amendment happens in construction phase alongside the Feature 2/3 dispatch.
- D4: Specialist dispatch happens from the parent (master) session that holds the Agent tool — sub-sessions without Agent fall back to coordinator-direct (works for surgical cleanup, will not scale to construction).
- Founder ruling: 25-endpoint count from §3 + §7.7 + §11.6 supersedes §11.1's "20".

### First-action recommendation for session 3 (if founder greenlights construction)
Dispatch **`meesell-auth-builder`** for **Feature 1 (OTP + JWT)** as the first specialist task. Rationale: the auth track has NO router-tree dependency (auth.py is already mounted and clean, its endpoints already match §3.1, and its contract is self-contained — no shared schema with the not-yet-built product/catalog/export routers). It is also the unblocker for every subsequent feature dispatch because every product / catalog / image / export endpoint needs `get_current_user`. Acceptance criteria: MSG91 send-OTP + verify-OTP wired end-to-end against Valkey DB 0 (3/h rate limit per phone), JWT issuance + verification middleware, `GET /api/v1/auth/me` returning the current user, 4 of 4 `test_auth.py` tests green against a live tunnel. Dispatch from the master session (not a sub-session) so the Agent tool is available; provide the auth-builder with `docs/MVP_ARCHITECTURE.md` §3.1 + §9 + §11.7 as the contract slice.

## Session 3 turn 1 — 2026-06-05 — BACKEND_ARCHITECTURE.md skeleton authored
`docs/BACKEND_ARCHITECTURE.md` now exists in SKELETON state. It is the construction contract for the four backend specialists, modeled after `docs/MVP_ARCHITECTURE.md` for the DATA track. The architecture is locked as a **Modular Monolith with extraction-ready boundaries**: 8 domain modules (`iam`, `customer`, `category`, `catalog`, `image`, `pricing`, `dashboard`, `export`) + `adapters/` (gemini, msg91, razorpay, gcs) + `core/` (cross-cutting) + `shared/` (foundation). The doc has 23 sections (0-22) following the founder's proposed structure verbatim — no deviations. Each section carries an explicit `STATUS: SKELETON | DRAFT | LOCKED` line directly under its heading; specialists are NOT to begin code on a section until that section's status flips to `LOCKED`. The deep content for each section will be authored across subsequent founder-reviewed turns, one section at a time. Founder's next intended turn: review the TOC, then drill into Section 0 (Architectural Premises) first. Specialist dispatches remain BLOCKED until at least Sections 0, 1, 2, 3, 4, 5, 6, and the relevant module section are LOCKED for the feature being built.

## Session 3 turn 2 — 2026-06-05 — BACKEND_ARCHITECTURE.md gap-closure amendments
Founder approved closing 4 hard gaps and 5 soft gaps surfaced in the coverage audit vs MVP_ARCHITECTURE.md, still at skeleton level. Three NEW sections inserted as 2-4 sentence stubs: §5A "Presentation Layer Contract + i18n" (between 5 and 6, locks the `templates.schema_jsonb.fields[]` contract + locale-aware Pydantic message library + `app/i18n/` package), §6A "AI Operations Layer" (between 6 and 7, owns per-call cost tracking + 3-layer hallucination guardrail + ₹500 daily cap + LangFuse + prompt registry + 3 golden eval sets), §22A "Risk Register & Mitigations" (appendix after 22, 10 risks from MVP_ARCH §13 each paired with the mitigation this doc carries). Five existing stubs amended (NOT replaced) with +1-2 sentences: §4 (core/) cites JWT claims `{sub,exp,plan}` per §11.7 + audit-after-write ordering per §11.8; §5 (shared/) cites 13-table access pattern + MVP_ARCH §2.6 as authoritative migration DDL; §6 (adapters/) locks GCS layout `gs://meesell-images/{user_id}/{product_id}/{image_idx}.jpg` + signed URL TTL 1h per §10.8; §10 (catalog) makes `GET /products/{id}/draft` explicit per §11.6; §11 (image) mirrors the GCS layout citation; §19 (Test Strategy) consolidates four perf budgets (schema fetch P95 ≤50/200ms per §6.6, browse P95 ≤200ms per §7.5, export ≤30s per §5.5.10, AI cost ≤₹0.05 avg per §8.2). **TOC is now LOCKED at 26 sections** (23 original + 3 lettered: 5A, 6A, 22A) using the lettered-subsection convention so future amendments don't force renumbering. Files touched this turn: 2 (`docs/BACKEND_ARCHITECTURE.md` + this MEMORY.md). Next dispatch begins authoring deep content for Section 0 (Architectural Premises).

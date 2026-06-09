# §0 Architectural Premises Audit Report
**Date:** 2026-06-08
**Auditor sub-session:** meesell-backend-verification-0-premises-1
**Scope:** §0 Architectural Premises (STATUS: LOCKED 2026-06-05) audited against the constructed `backend/app/` codebase + tests.
**Overall verdict:** PASS ✅

> 13 of 14 checklist rows PASSED at audit time. One founder-locked ruling — **D3** (MVP_ARCHITECTURE.md §3.4 inline amendment) — was NOT executed by the construction dispatch. The corresponding code endpoint (`GET /products/{id}/draft`) IS implemented and the §17/code 27-endpoint contract is satisfied; the gap was documentation-only. **Master applied the D3 amendment inline on 2026-06-08** — `GET /api/v1/products/{id}/draft → draft recovery (§11.6 crash recovery; added per D3 ruling — §0.F)` inserted at MVP_ARCHITECTURE.md line 401. §0 premises now fully satisfied. No code-correctness defects. All universal regression checks pass.

---

## Audit checklist results

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | 14 founder-locked decisions honored | **PASS** | §12.1/§12.6 → `COMPLIANCE_EXTENSION_MAP` wired at `customer/service.py` (6 sites incl. Books "80" ISBN-optional + Eye-Serum collapse); §12.2 → alias reverse-map in `export/{domain,repository,service}.py` + `tests/modules/export/test_alias_restoration_typo.py`; §12.3 → no leaf-count filter (category `/browse`); §12.4 → D2 (below); §12.5 → warranty correctly NOT special-cased in `customer/` (data-driven via `templates.schema_jsonb`); §12.6 → F4 (below) + `golden_round_trip/fixture_03_eye_serum.json`. Initial-batch 8: `i18n/primitive_classifier.py` (primitive source-of-truth), `i18n/step_assignment.py` (data-driven wizard), enum-constrained AI (guardrail L2), canonical normalisation (`field_aliases` + `canonical_name` regex). All 14 traceable. |
| 2 | D1 — no `.legacy.py.bak` files | **PASS** | `find backend/ -name "*.legacy.py.bak"` → empty; `find backend/ -name "*.bak"` → none. Boot test `test_no_stray_legacy_routes` PASSES. (LOW housekeeping note H1 below re: inert `app/routers/`.) |
| 3 | D2 — `ADVANCED_CANONICAL_NAMES = {"group_id"}` | **PASS** | Seed lock: `scripts/build_template_schemas.py:86 ADVANCED_CANONICAL_NAMES = {"group_id"}`. Runtime mirror: `app/i18n/advanced_canonical.py:25 Final[frozenset[str]] = frozenset({"group_id"})`. Tests assert `== frozenset({"group_id"})` and `len == 1` (`test_per_field_shape_keys.py:214-215`). Exactly one element. |
| 4 | D3 — MVP_ARCH §3.4 amendment | **FAIL** | §3.4 (MVP_ARCHITECTURE.md line 396) enumerates 11 endpoints; `GET /api/v1/products/{id}/draft` is **absent**, no AMENDMENT/D3/"25th" annotation in the §3.4 block (lines 396–470). The draft endpoint appears in MVP_ARCH only at line 2483 (§11.6 prose). The promised inline §3.4 amendment was never committed. Code endpoint EXISTS (`catalog/router.py:319`, §10.B.6). Doc-only non-compliance. |
| 5 | D4 — specialist authorship | **PASS** (intent) | Code authored by specialists per the system-of-record: STATUS_BACKEND/STATUS_MASTER log each sub-session by name (`meesell-backend-construction-{10,18,19,20}-…`, e.g. "§18 celery — meesell-services-builder solo"; "§20 — meesell-infra-builder solo") and `.claude/agent-memory/meesell-{database,api-routes,services}-builder/MEMORY.md` are populated. NOTE: git commits do NOT name specialists (conventional commits by Mugunthan93/claude-agent, generic Claude co-author trailers) — attribution lives in STATUS, not git. See housekeeping H2. |
| 6 | 27-endpoint count | **PASS** | `@router.<verb>` across `modules/` = **28** (≥27). Per-module: iam 6 (4 contract + `/me` + `/webhooks/razorpay`), customer 5, category 5, catalog 6, image 2, pricing 1, dashboard 1, export 2. Every named contract endpoint (§3.1–3.4 + §7.7 browse + §11.6 draft + FE-D5 refresh/logout + 2 infra) present in code. The 28-vs-naive-29 nuance is a §0.C prose-arithmetic overlap (browse counted in both §3.3 & §7.7) — reconcile in §17's own audit; no endpoint missing. |
| 7 | 13-table baseline, head `f31c75438e61` | **PASS** | Alembic chain (file-based): `935e55b4852c (v1_baseline_13_tables, down=None)` → `a1b2c3d4e5f6 (pg_trgm+GIN, down=935e55b4852c)` → **`f31c75438e61` (head, down=a1b2c3d4e5f6)** — exact §0.D match. Baseline migration `op.create_table` ×13 = exactly the 13 §0.D tables. 13 ORM models map 1:1 (`__tablename__` grep). Live `\dt` not run (DB introspection; `test_database.py` 42/42 PASS validates schema). |
| 8 | backend tree clean-state baseline | **PASS** | `main.py` mounts all 8 module routers (iam/customer/category/catalog/image/pricing/dashboard/export) + 2 infra surfaces inside iam. `test_database.py` **42/42 PASS** (exact §0.E count). `test_app_boot_integration.py` **8/8 PASS** (§0.E baseline 7/7; construction added `test_dashboard_get_products_route_mounted`). No regressions. |
| 9 | M7 — enum guardrail (Layer 2) | **PASS** | `ai_ops/guardrail.py:122-128` "Layer 2 — parser-level validation … parse JSON and check shape + enum compliance"; line 34 "Layer 2 rejects any field whose emitted value is NOT in its allowlist". Owned here per §6A.E. |
| 10 | M9 — i18n | **PASS** | `app/i18n/` package present (resolver, messages_en, schema_contract, primitive_classifier, step_assignment, advanced_canonical). `messages_en.py` = **55 message IDs**, all matching 3-segment `{domain}.{field}.{constraint}` regex (~50 expected). `test_messages_en_id_regex.py` + `tests/lint/check_message_id_regex.py` enforce. |
| 11 | M10 — forbidden symbols only in export(+gcs) | **PASS** | `meesho_column_header`/`meesho_column_index`/`enum_codes_map` live-code occurrences confined to `modules/export/{service,schemas,domain,__init__}.py`. The 3 hits in `shared/models/template.py:37-40` are **docstring-only** (JSON-shape illustration inside module docstring closing line 50; class begins line 68) and are explicitly allowlisted in `tests/lint/check_no_meesho_symbols_outside_export.py KNOWN_DOCSTRING_HITS` (§19 Contract 9). Not in `adapters/gcs.py` (not required there). Code-level rule satisfied. |
| 12 | F3 — 3-layer guardrail | **PASS** | L1 prompt prefix: `guardrail.py:52-56 _LAYER1_PREFIX` + `:89`. L2 enum re-validation: `guardrail.py:122-128`. L3 export gate: `export/service.py:645 "LAYER 3 HALLUCINATION GUARDRAIL per MVP_ARCH §9.7"`. All three present. |
| 13 | F4 — 9-not-12 compliance | **PASS** | `customer/service.py get_compliance_block` returns `ComplianceBlock` with exactly 9 fields (manufacturer/packer/importer × name/address/pincode, lines 97-105). Stores 9; collapse to 3 derived at export only (`CollapsedComplianceStrategy`, §12.6). |
| 14 | F5 — every field has help_text | **PASS** | `test_per_field_shape_keys.py:182 test_help_text_non_empty` ("§5A.C / §0.H F5 — every field carries help_text"): asserts `isinstance(f["help_text"], str)` AND `.strip()` non-empty. Seed-time enforcement at `scripts/build_template_schemas.py:208`. |

**Universal regression checks:** `test_app_boot_integration.py` 8/8 PASS · `test_database.py` 42/42 PASS (93.8s) · `lint-imports` **27 kept / 0 broken** (the §16 modular-monolith boundaries realizing the §0.B premise) · STATUS_BACKEND.md confirms CONSTRUCTED for §4/§5/§5A/§6/§6A/§7/§8/§9/§10/§11/§12/§13/§14/§18/§19/§20 (all 16).

---

## Non-compliance findings

### Finding F-1 (CHECK 4) — D3 §3.4 amendment not applied
- **Finding:** MVP_ARCHITECTURE.md §3.4 was never amended to enumerate `GET /api/v1/products/{id}/draft` as the 25th endpoint.
- **Locked claim (§0.F D3):** "`MVP_ARCHITECTURE.md §3.4` will be amended during construction to enumerate `GET /api/v1/products/{id}/draft` as the 25th endpoint … the same dispatch updates §3.4 inline. The doc-PR accompanies construction; it is not a separate later cleanup turn." (Reinforced in §0.C.)
- **Actual state:** §3.4 (MVP_ARCH line 396) lists 11 endpoints with no draft-recovery GET and no amendment annotation. The Feature 2/3 + Wave 4 (catalog) dispatches that were to carry the doc edit landed without it. The endpoint itself IS implemented (`catalog/router.py:319 GET /products/{id}/draft`, §10.B.6) and is in the authoritative §17/27-contract — so this is purely cross-doc drift in the DATA-track source doc.
- **Severity:** **MEDIUM** — zero runtime/correctness impact; but it is a founder-LOCKED ruling explicitly not executed, and leaves exactly the re-litigation risk D3 was created to eliminate (a future reader of MVP_ARCH §3.4 sees only 11 catalog endpoints).
- **Recommended remediation:** A one-line documentation amendment to MVP_ARCHITECTURE.md §3.4 adding `GET /api/v1/products/{id}/draft → draft recovery (§11.6 autosave)`. Owner: the dispatch that owns MVP_ARCHITECTURE.md (DATA track / `meesell-backend-coordinator` doc micro-session). MVP_ARCH is the DATA track's source of truth — master to route accordingly. No code change.

---

## Housekeeping observations (informational — not §0 contract violations)

- **H1 (LOW):** `backend/app/routers/__init__.py` (1 line, empty package) lingers from the V0 layout. Zero live importers (`grep "app.routers" app/` empty); boot test `test_no_stray_legacy_routes` passes. Not a D1 violation (legacy router *files* are deleted). Optional cleanup: delete the empty `app/routers/` package.
- **H2 (LOW):** The Wave 4–6 modules `catalog/`, `image/`, `pricing/`, `dashboard/`, `export/` are **untracked working-tree state** (git `?? dir/`); `iam/`, `customer/`, `category/`, `ai_ops/` are committed. The audit ran against the working tree (the constructed code). Recommend master orchestrate a commit of the constructed modules so the audited state is captured in git history. (Plus the expected staged deltas: `main.py` M, `celery_app.py` M, `pricing_engine.py` D, `generation_tasks.py` D, `messages_en.py` M — all per §12/§18 construction.)

---

## Verdict rationale

The §0 premises are honored in code with high fidelity: all four D-rulings' code-side artifacts, the 13-table/`f31c75438e61` baseline, the clean-state tree, the 27-endpoint contract, and all six CORE_PHILOSOPHY commitments (M7/M9/M10/F3/F4/F5) are present and test-backed, with no regressions (boot 8/8, schema 42/42, import-linter 27/0). The single non-compliance is **D3** — a founder-locked *documentation* amendment to MVP_ARCH §3.4 that was never executed, even though the underlying code endpoint exists and the authoritative contract (§17 + code) already includes it. Because D3 is a LOCKED ruling that was explicitly not carried out, the verdict is **PARTIAL** rather than PASS; the remediation is a trivial one-line doc edit with zero code impact.

## Hand-back to master — RESOLVED

1. **D3 remediation (Finding F-1): RESOLVED 2026-06-08** — master applied the inline amendment to MVP_ARCHITECTURE.md §3.4 (line 401): `GET /api/v1/products/{id}/draft → draft recovery (§11.6 crash recovery; added per D3 ruling — §0.F)`. Audit verdict upgraded to PASS.
2. **(Optional, LOW) H2:** Wave 4-6 modules (catalog/image/pricing/dashboard/export) are untracked working-tree state. Recommend master orchestrate a git commit — carry to Wave 10 §22 acceptance as a pre-ship requirement. `git add backend/app/modules/catalog backend/app/modules/image backend/app/modules/pricing backend/app/modules/dashboard backend/app/modules/export`.
3. **(Optional, LOW) H1:** `app/routers/__init__.py` (empty, zero live importers). Trivial cleanup — carry to Wave 10 §22 acceptance.
4. Note for §17 audit: reconcile the §0.C "27" prose arithmetic (browse double-count) against the 28 live routes — counting nuance, not a missing endpoint.

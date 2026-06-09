# §22A Risk Register Audit Report

**Date:** 2026-06-09
**Auditor sub-session:** meesell-backend-verification-22A-risks-1
**Audit target:** `docs/BACKEND_ARCHITECTURE.md` §22A.B — the 12 backend risk mitigations
**Scope:** read-only verification that all 12 backend risk mitigations are present **and effective** in code/architecture
**Overall verdict:** ✅ **PASS** — all 12 mitigations present and effective. One non-blocking hardening advisory on R9 (Valkey-unavailability robustness; not a §15.C lock violation).

Wave 1–7 CONSTRUCTED confirmed (STATUS_BACKEND.md: §5, §11/§12/§13, §14, §18, §19, §20). STATUS_BACKEND.md carries 38 `CONSTRUCTED` entries.

---

## Audit checklist results

| # | Risk | Mitigation present? | Evidence |
|---|---|---|---|
| R1 | AI hallucination — 3-layer guardrail | **PASS** | **L1** `ai_ops/guardrail.py::apply_prompt_constraint` prepends workload-bonded prefix + appends `allowed_enums` block for autofill (L52–110). **L2** `ai_ops/client.py` `for attempt in range(3)` (=up-to-2 retries / 3 total calls, L211) → `guardrail.parse_and_validate(...)` re-validates enums; on `None` increments `layer2_retries` + `build_retry_prompt` stricter retry (L268–291); final exhaustion → graceful fallback. **L3** `modules/export/service.py::_translate_enums` (Step 5, called L330) hard-`raise ExportEnumValidationError` on unknown canonical enum (L679); exception defined `export/exceptions.py:123`. 3 layers independent. |
| R2 | Server-side pagination + cache | **PASS** | `dashboard/router.py` `page: Query(ge=1)=1`, `limit: Query(ge=1,le=100)=20` (L89–90) → `dashboard/service.list_products_for_dashboard` builds `Pagination(page,limit)` → delegates `catalog.service.list_products`; `catalog/repository.py` server-side SQL `offset=max(0,(page-1)*limit)` + `.limit(limit).offset(offset)` (L366–372). Field-enum single-flight cache per §15.C. |
| R3 | ComplianceStrategy dispatch | **PASS** | `modules/export/domain.py`: `ComplianceStrategy(ABC)` L155 + `StandardComplianceStrategy` L222 + `CollapsedComplianceStrategy` L294. Dispatch `export/service.py::_select_strategy(compliance_shape)` → `"standard"`→Standard / `"collapsed"`→Collapsed / else `ComplianceStrategyError` (L455–463); called from pipeline L319–320. |
| R4 | 15 golden round-trip fixtures | **PASS** | `tests/integration/golden_round_trip/` = `fixture_01_sarees.json … fixture_15_special_chars.json` (exactly 15; incl. `fixture_03_eye_serum`, `fixture_04_fssai_grocery`). Runner `test_golden_fixtures_runner.py` present. |
| R5 | `wizard_step_count` populated | **PASS** | API contract requires it: `category/schemas.py:175 wizard_step_count: int`; `i18n/schema_contract.py:140,152`. Backend materialises the §5A.B envelope in `category/repository.fetch_schema_uncached` (`envelope = dict(schema_jsonb)`), surfaced by `category/service.fetch_schema`. Integer value seeded into `templates.schema_jsonb` (data track); contract enforces presence + `int` type. |
| R6 | FSSAI compulsory in compliance map | **PASS** | `customer/domain.py::COMPLIANCE_EXTENSION_MAP` → `super_id="26"` Grocery, `required_keys=("fssai_license_number",)`, `compulsory=True` (L158–162). `compulsory=True` gates `onboarding_complete` (requires all `required_keys` populated). |
| R7 | `field_aliases.for_xlsx_export` rows present | **PASS** | Column+index in baseline migration `935e55b4852c` (`for_xlsx_export BOOLEAN NOT NULL DEFAULT false`, `idx_field_aliases_for_export`); model `shared/models/field_alias.py:50`. Seed `scripts/seed_field_aliases.py` sets `for_xlsx_export = (variant != canonical)` (L123/140/154/169) → TRUE for all Meesho-wire-format variants over `data/parsed/canonical_field_aliases.json` (38 canonical groups). Export `service._restore_aliases` (Step 7, L332/712) consumes the reverse map. |
| R8 | Isolation regression + scope_to_user linter | **PASS** | `tests/integration/test_multi_tenant_isolation.py` (9.8 KB) — 4 cross-tenant attack vectors, asserts 404-not-403 (no info leak), cites §15.B Layer1 `scope_to_user` + Layer2 `assert_product_ownership`. `tests/lint/check_scope_to_user.py` **executed → exit 0**: "§19.C Contract 8 PASS — every public repository method on 5 owned-table modules carries `user_id`." |
| R9 | Cache fallback to PG on miss | **PASS** (+ advisory) | `core/cache.py::get_or_set` calls `fetch_fn()` (Postgres) on cache miss in all 3 branches (L96 simple, L106 single-flight elected, L130 poll-timeout degrade) and never raises on miss. Matches the LOCKED §15.C mitigation ("fall back to Postgres **on cache miss**"). **Advisory (non-blocking):** no `try/except` wraps the Valkey `client.get/set` calls, so a Valkey **connection failure** (vs. a miss) would propagate, not degrade-to-PG-with-warning. This stricter "never-raise-on-unavailability" posture is NOT locked by §15.C (which even tolerates "erroring" after single-flight poll-timeout). Recommend V1.5 hardening: wrap reads in `try/except → logger.warning + fetch_fn`. |
| R10 | ₹500 cap + per-workload fallback | **PASS** | `ai_ops/budget_cap.py`: DAILY GLOBAL **₹500** cap; bands 0–80% normal / 80–100% Prometheus alarm / 100%+ hard-stop `check_and_reserve` raises `BudgetExceededError`; atomic Lua cap check (`if total > cap`). Per-workload fallback `client._fallback_parsed`: smart_picker `{suggestions:[],fallback_offered:True}`, autofill `{fields:{},fallback_offered:True}`, watermark `"skipped_budget"`. Consumer `category/service.suggest_categories` returns 200 + `fallback_offered=True` on `BudgetExceededError` (L267, never raises). |
| R11 | HMAC pepper + Lua EVAL | **PASS** | `core/auth.py::refresh_allowlist_key` → `hmac.new(REFRESH_TOKEN_PEPPER.encode(), token, sha256).hexdigest()` → `cache:refresh:{digest}` (L329–334, HMAC-with-pepper not bare SHA-256). `REFRESH_ROTATE_LUA` atomic GET→DEL old→SET new EX (L352+). `SCRIPT LOAD` once → `EVALSHA` thereafter, transparent `EVAL` fallback on NOSCRIPT (L391–419). `secrets.compare_digest` constant-time compare (bonus). `REFRESH_TOKEN_PEPPER` in `shared/config.py:57,112` (Secret Manager `refresh-token-pepper` LIVE per §20). |
| R12 | `services/pricing_engine.py` DELETED | **PASS** | `ls app/services/pricing_engine.py` → No such file. Git working tree shows `D backend/app/services/pricing_engine.py` (deletion). Fresh `modules/pricing/{service,domain,schemas,repository,router,exceptions}.py` subtree present per §3.C. |

---

## Non-compliance findings

**None blocking.** All 12 risk mitigations are present and effective.

**Advisory A-1 (R9, LOW, non-blocking) — Valkey-unavailability resilience.** `core/cache.get_or_set` has no `try/except` around Valkey I/O. A Valkey connection failure (not a cache miss) would raise rather than degrade to Postgres with a logged warning. This does NOT violate the LOCKED §15.C design (which locks only cache-miss → PG fallback and explicitly tolerates erroring after single-flight poll-timeout). Recommend tracking a V1.5 hardening ticket: wrap cache reads in `try/except (ConnectionError, TimeoutError) → logger.warning + fetch_fn`.

**Environmental note E-1 (non-blocking).** `lint-imports` (import-linter) binary not installed in this verification sub-session env, so the §19 Contract 1–7 import-graph check could not be executed live here; STATUS_BACKEND.md §19 records "27 kept / 0 broken" from the construction sub-session. The 3 standalone AST scanners (`check_scope_to_user`, `check_no_meesho_symbols_outside_export`, `check_message_id_regex`) were all executed in this audit → exit 0.

**Working-tree note W-1 (informational, pre-existing, from §1 topology audit H2).** Wave 4–6 module subtrees (`catalog/`, `dashboard/`, `export/`, `image/`, `pricing/`) are untracked (git `??`); `pricing_engine.py` + `generation_tasks.py` are staged deletions. Audited against working-tree state. Recommend `git add` + commit before §22 final acceptance so the audited state lands in history. Not a §22A risk-mitigation defect.

---

## Verdict rationale

Every one of the 12 backend risks in §22A.B carries a mitigation that is (a) present in code/architecture and (b) effective for what its locking section specifies — verified by file inspection, grep, fixture count, executed linter, and live `git` deletion evidence for R12. The two CRITICAL risks (R1 score 20, R6 score 20) and the top HIGH (R7 score 15) — which the register flags as carrying the most documentation density — were each verified to the implementation level: R1's three layers are independent and Layer 3 hard-raises; R6's compulsory FSSAI is gated (not hidden) and blocks onboarding completion; R7's reverse map is seeded TRUE-for-variant and consumed by the export adapter. R8's tenant-isolation linter and R11's HMAC-pepper + atomic-Lua rotation — the cross-tenant-leak and account-takeover defenses — were executed/inspected and hold. R12's deletion path is doubly confirmed. The single advisory (R9 Valkey-down robustness) is a stricter posture than §15.C locks and is recorded as a non-blocking V1.5 hardening item.

**No risk is left unmitigated.**

---

## Hand-back to master

§22A Risk Register audit: **PASS (12/12)**. All backend risk mitigations present and effective; no escalation triggered. One non-blocking V1.5 hardening advisory (R9 Valkey-unavailability try/except) + one env note (lint-imports binary absent here; AST scanners passed) + reminder to `git add` Wave 4–6 module subtrees before §22 acceptance. Report saved at `docs/audits/§22A_risks_audit_2026-06-09.md`. STATUS_BACKEND.md UPDATE block appended.

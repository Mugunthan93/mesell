# §15 Cross-Cutting Walkthrough Audit Report
**Date:** 2026-06-09
**Auditor sub-session:** meesell-backend-verification-15-crosscutting-1
**Overall verdict:** PARTIAL (7 PASS · 3 PARTIAL · 0 FAIL · 0 CRITICAL escalation triggers)

§15 is a *consolidation/walkthrough* section that mirrors contracts locked in §4/§6A/§7–§14. This audit verifies that each cross-cutting concern's per-module participation, as summarized in §15, is faithfully realized in the LIVE `backend/app/` source (Wave 1–7 CONSTRUCTED). The 3 PARTIALs are **construction-completeness gaps vs the §15 narrative**, not security defects — the three CRITICAL triggers (multi-tenancy layer missing, AI-ops single-import breach, CSRF posture change) did **not** fire.

---

## Audit checklist results

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | Multi-tenancy 3-layer | **PASS** | L1 `scope_to_user` in catalog/customer/export/image/pricing repos (`core/tenancy.py:73` def); category=global-data exception (§19 allowlist), iam users=identity N/A, dashboard=no-repo composition. L2 `assert_product_ownership` def `catalog/service.py:919`, consumed by image (`service.py:162,248`), pricing (`134,241`), export (`174`). L3 GCS prefix `adapters/gcs.py:20-22` `meesell-images/{user_id}/{product_id}/…` + `meesell-exports/{user_id}/{export_id}/…`. Matches §15.B matrix exactly. |
| 2 | `core/cache.py` sole Valkey DB 3 | **PARTIAL** | `get_or_set` is sole read-through surface (`core/cache.py:58`); version-prefixed `meesell:{CACHE_VERSION}:…`. **Deviation:** `customer/service.py:324` imports `get_valkey_cache` directly for `client.delete()` cache **invalidation** — `core/cache.py` exposes no invalidation helper. iam `valkey.get/set` = DB 0 (OTP/refresh), out of §15.C DB-3 scope. |
| 3 | pg_trgm GIN indexes | **PASS** | Migration `a1b2c3d4e5f6` creates `pg_trgm` ext + 3 GIN trgm idx (`idx_categories_path_trgm`, `_leaf_name_trgm`, `_super_name_trgm`) via `USING GIN (… gin_trgm_ops)`. Head chain `935e55b4852c → a1b2c3d4e5f6 → f31c75438e61` confirmed. Live `\di` deferred (dev SSH tunnel down) — migration is authoritative source. |
| 4 | Audit mw + 7 direct-write exceptions | **PARTIAL** | `audit_mw.py` post-2xx (`:227`), 5-min coalescing (`:145,238`), PII scrub (`:114,120`) ✅. 7 direct-write `event_type=` literals fire: `ai.call`, `auth.login.success`, `auth.logout`, `auth.token.refreshed`, `auth.token.refresh_failed`, `image.precheck.completed`, `razorpay.webhook.captured`. **GAP-1:** `export.completed`/`export.failed` documented in `export/tasks.py:15-18` docstring but **never written** — zero `export.*` audit rows in codebase. **GAP-2:** §15.E-named shared helper `core/audit_helpers.audit_event_write` **does not exist**; direct writes are per-site `AuditEvent(...)` (cost_tracker:229, image/tasks:388) + iam-local `_write_audit_direct`. |
| 5 | AI Ops single import + 3 workloads + guardrail + cap + fallback | **PASS** | Single surface: `adapters.gemini` imported ONLY by `ai_ops/client.py:52,54` (import-linter Contract 5 KEPT); zero module imports. 3 workloads `smart_picker/autofill/watermark` (`client.py:116-127`). 3-layer guardrail: L1 prompt prefix (`guardrail.py:84`), L2 enum re-validation, L3 export `_round_trip_validate`+`ExportEnumValidationError`. ₹500 cap + `_today_kolkata_str` Asia/Kolkata (`budget_cap.py`). Fallbacks: smart_picker `{suggestions:[],fallback_offered}`, autofill `{fields:{},fallback_offered}`, watermark `"skipped_budget"`. |
| 6 | Plan_guard 4 resources | **PASS** | `PlanResource = Literal["product_count","ai_autofill_hourly","smart_picker_hourly","create_product_hourly"]` (`plan_guard.py:53`); limits (100/None),(50/3600),(100/3600),(20/3600). Enforced: catalog.create_product (product_count + create_product_hourly), catalog.autofill (ai_autofill_hourly), category.suggest (smart_picker_hourly). Matches §15.G. **Note:** prompt checklist item #6 mis-named the resources ("active_products_count", "autofill_hourly", "autosave_coalescing_5min") — code matches the authoritative §15.G/§4.E, not the checklist phrasing. |
| 7 | FE-D5 refresh allowlist (HMAC + Lua EVAL) | **PASS** | HMAC-SHA256+pepper `core/auth.py:329` `hmac.new(REFRESH_TOKEN_PEPPER…)`, key `cache:refresh:{hmac_sha256(token,pepper)}` (`:321`). `secrets.compare_digest` (`iam/service.py:310`). Lua: `REFRESH_ROTATE_LUA` (`auth.py:352`) → `load_lua_script` (SCRIPT LOAD→SHA1) → `eval_lua_script` EVALSHA-first + EVAL fallback on `NoScriptError`/NOSCRIPT (`shared/valkey.py:160-165`). Replay handled (race_lost→refresh_failed). Secret `refresh-token-pepper` LIVE v1. |
| 8 | CSRF posture (no middleware) | **PASS** | `grep -i csrf app/` → **0 matches** (no CSRF middleware). Refresh cookie `samesite="strict"` (`iam/router.py:78,92`); access token Bearer-header. Structurally CSRF-resistant per §15.I. Posture unchanged — no escalation. |
| 9 | Observability (request_id + Prometheus + LangFuse) | **PARTIAL** | request_id ✅ (`request_id.py` X-Request-ID, uuid4, registered `main.py:96`). LangFuse ✅ (call-site `ai_ops/client.py:22` step 8; `adapters/langfuse.py` httpx-direct fire-and-forget, no-op on missing creds). **GAP:** Prometheus **entirely unimplemented** — zero `Counter/Histogram/Gauge`, no `prometheus_client` import, no `/metrics` mount in `main.py`, absent from `requirements.txt`. §15.J's 7 "Key V1 metrics" are unbuilt; `auth_mw.py:18` anticipates a `/metrics` endpoint that does not exist. |
| 10 | i18n ~50 message IDs | **PASS** | `app/i18n/messages_en.py` `VALIDATION_MESSAGES` dict — **55** keys, all conforming to the 3-segment regex `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$`. 55 ≈ "~50" (§15.K). |
| — | **Universal: import-linter** | **PASS** | Independently re-run via `backend/.venv` (import-linter 2.11): **27 kept / 0 broken**. Contract 5 ("ai_ops consumed only by category/catalog/image") corroborates Check 5. |

---

## Non-compliance findings

### F-15-1 (MEDIUM) — Export worker emits no audit rows [Check 4, GAP-1]
`export/tasks.py:15-18` documents *"Direct audit writes for `export.completed`/`export.failed`"* but no `AuditEvent(...)` constructor or `event_type="export.*"` literal exists anywhere in `backend/app/`. The export worker persists only domain status (`exports.status="completed"/"failed"`), not an `audit_events` row. §15.E (exception table), §14.E, and §17.F all assert these worker-direct writes as V1 behavior. `export.initiated` (POST route, 2xx) may be covered generically by `audit_mw._derive_event_type`, but the two **terminal worker events are absent** — an audit-trail completeness gap for the seller's primary value action.
**Recommendation (master decision):** either (a) implement the two worker-direct writes, or (b) amend §14.E/§15.E to mark export terminal-event audit as V1.5-deferred and re-mirror §15.

### F-15-2 (MEDIUM) — Prometheus metrics unimplemented [Check 9, GAP]
§15.J enumerates 7 "Key V1 metrics" (`ai_ops_budget_alarm_total`, `i18n_resolver_missing_key`, `http_request_duration_seconds`, `http_requests_total`, `celery_queue_depth`, `ai_ops_cost_inr`, `auth_token_refresh_failed_total`). None exist: no `prometheus_client` dependency, no metric definitions, no `/metrics` ASGI mount. `auth_mw.py:18` comments anticipate a `/metrics` scrape path that is not wired. request_id + LangFuse legs are intact; only the Prometheus leg is missing.
**Recommendation:** implement a `prometheus_client` instrumentator + `/metrics` mount (and add the dep), OR amend §1/§4/§15.J to mark Prometheus V1.5-deferred. Note §20 K8s scrape config presumes `/metrics` exists — coordinate with infra.

### F-15-3 (LOW) — Direct DB-3 invalidation in customer service [Check 2]
`customer/service.py:324` bypasses `core/cache.py` to `client.delete()` the required-fields cache. Substance of §15.C holds (read-through is centralized via `get_or_set`; correctly version-prefixed; drop-on-failure wrapped) — but `core/cache.py` exposes no `invalidate()` helper, so the module had no sanctioned alternative. Strict §15.C "sole DB-3 access" claim is violated.
**Recommendation:** add `core.cache.invalidate(key)` and route customer through it (closes the grep-anchor cleanly), OR amend §15.C to document the invalidation carve-out.

### F-15-4 (LOW / structural) — `core/audit_helpers` shared helper absent [Check 4, GAP-2]
§15.E, §11.E, §14.E, and §17 PII-redaction prose reference `core/audit_helpers.audit_event_write(...)` as the shared worker-context write+redact helper. It does not exist; direct writes are per-site `AuditEvent(...)`, and iam duplicates `_hash_phone_for_audit` (`service.py:233`, with an in-code comment noting the duplication of `audit_mw._hash_phone`). Behavior is delivered, but redaction is decentralized rather than centralized as documented — a divergence risk if one site's redaction drifts.
**Recommendation:** extract `core/audit_helpers.py` (centralizes PII redaction for direct-write sites) per the §15.E contract, OR amend the four sections to canonicalize the per-site pattern.

---

## Verdict rationale

**PASS (7):** Checks 1, 3, 5, 6, 7, 8, 10 + import-linter. The three security-critical cross-cutting invariants are intact and independently verified: **multi-tenancy 3-layer defense** (no cross-tenant leak path), the **AI-ops single import surface** (import-linter Contract 5 KEPT — the single most important boundary in the codebase), and the **CSRF posture** (no middleware; SameSite=Strict + Bearer split). The FE-D5 refresh allowlist (HMAC-pepper + atomic Lua EVALSHA/EVAL rotation) is fully realized.

**PARTIAL (3):** Checks 2, 4, 9 — all are *§15-narrative-vs-implementation completeness* gaps, not contract violations of the security model:
- Check 9 (Prometheus) and Check 4 (export audit + `audit_helpers`) describe V1 behavior in §15 that was deferred or shaped differently during construction.
- Check 2 (customer invalidation) is a low-severity carve-out forced by a missing helper.

Per §15.A — *"§15 does NOT introduce new contracts… amendments land in the original section, and §15 is updated to mirror"* — each PARTIAL resolves **either** by building the missing piece **or** by amending the original locking section (§14.E, §1/§4, §15.C, §11.E) and re-mirroring §15. That build-vs-defer choice is a master/founder decision, not an auditor call.

**No CRITICAL escalation triggered.** None of the three escalation conditions (tenancy layer missing, AI-ops single-import breach, CSRF change) occurred.

---

## Hand-back to master

§15 cross-cutting audit complete. **PARTIAL** — 7 PASS / 3 PARTIAL / 0 FAIL, 0 CRITICAL. Security model (tenancy, AI single-import, CSRF, refresh allowlist) fully intact and independently verified; import-linter 27/0 re-run clean. Three completeness gaps surfaced — F-15-1 export worker audit rows unimplemented (MEDIUM), F-15-2 Prometheus metrics unimplemented (MEDIUM), F-15-3 customer direct DB-3 invalidation (LOW), F-15-4 `core/audit_helpers` shared helper absent (LOW). Each is build-or-amend; recommend founder ruling on V1-build vs V1.5-defer for F-15-1/F-15-2 before §22 final acceptance. No LOCKED code touched; read-only audit.

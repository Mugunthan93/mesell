# audit_flag_parity_sweep.md — comprehensive V1 backend feature-flag parity audit

**Session:** mesell-flag-parity-sweep-session-1 (HYBRID STEP 1 — audit + SPECs only; no feature code, no dispatch)
**Date:** 2026-06-12
**Base:** origin/develop @ `2b5ec60` (5 flag features already merged 195b275..01abfbf this morning)
**Premise (proven 6x):** V1 backend modules ~100% as-built on develop; recurring REAL gap = feature-flag parity (missing `FEATURE_X_ENABLED` in `shared/config.py` §3.2 + missing route guards + missing flag-404 tests).

---

## Flag inventory on develop (shared/config.py §3.2 — file:line)
| Flag | config.py line | Default | Status |
|---|---|---|---|
| FEATURE_SMART_PICKER_ENABLED | 184 | True | PRESENT |
| FEATURE_XLSX_EXPORT_ENABLED | 193 | True | PRESENT |
| FEATURE_IMAGE_PRECHECK_ENABLED | 202 | True | PRESENT |
| FEATURE_CATALOG_FORM_ENABLED | 209 | True | PRESENT |
| FEATURE_AI_AUTOFILL_ENABLED | 216 | True | PRESENT |
5 flags = exactly the 5 done features. No others.

---

## Per-module verdict table (honest list; file:line evidence)
| Module / Feature | Plan mandate | Flag in config? | Route guard? | Flag-404 test? | VERDICT |
|---|---|---|---|---|---|
| smart-picker (category /suggest) | D2 standard | YES (184) | YES in-handler `category/router.py:117` | YES `test_suggest_flag_404.py` | FLAG-MANDATED-AND-PRESENT |
| xlsx-export | D2 standard | YES (193) | YES POST gate `export/router.py` | YES `test_export_flag_404.py` | FLAG-MANDATED-AND-PRESENT |
| image-precheck | D2 | YES (202) | YES POST gate | YES `image/test_flag_gate.py` | FLAG-MANDATED-AND-PRESENT |
| catalog-form | D2 standard | YES (209) | YES main.py conditional-include `main.py:126` | YES (unit dir) | FLAG-MANDATED-AND-PRESENT (drift D-1) |
| ai-autofill | D2 | YES (216) | YES in-handler `catalog/router.py ~227` | YES (integration) | FLAG-MANDATED-AND-PRESENT |
| **price-calculator** (pricing POST /products/{id}/price-calc) | **D2 Standard; §1.B "not yet wired, D2 work item"** | **NO** | **NO** `pricing/router.py:68` POST no guard | **NO** (`tests/modules/pricing/` 4 files none flag) | **FLAG-MANDATED-AND-MISSING -> G1** |
| **tracking-dashboard** (dashboard GET /api/v1/products) | **D3 kill-switch; "When OFF: GET /api/v1/products returns 404"** | **NO** | **NO** `dashboard/router.py:80` GET no guard | **NO** (`tests/modules/dashboard/` 3 files none flag) | **FLAG-MANDATED-AND-MISSING -> G2** |
| **live-preview** (catalog GET /products/{id}/preview) | **D3 gated rollout default False; "When disabled: GET preview returns 404 code feature.live_preview.disabled"** | **NO** | **NO** route EXISTS `catalog/router.py:268` no guard | **NO** | **FLAG-MANDATED-AND-MISSING -> G3** |
| auth-otp (iam /api/v1/auth/*) | **D2 explicit: "Skip the feature flag. FEATURE_AUTH_OTP_ENABLED NOT created. No 404 guard."** (FEATURE_PLAN.md:40-42) | NO | NO | N/A | **NO-FLAG-BY-DESIGN** |
| customer (/api/v1/seller-profile/*) | no FEATURE_PLAN; no flag anywhere (grep empty) | NO | NO | N/A | **NO-FLAG-BY-DESIGN** (foundational onboarding surface) |
| category browse/tree/schema/field-enum | only /suggest flagged | suggest only | suggest only | suggest only | **NO-FLAG-BY-DESIGN** (foundational catalog surface) |
| iam refresh/logout/me/webhook | same auth D2 | NO | NO | N/A | **NO-FLAG-BY-DESIGN** |

---

## Real-gap G-list (3 gaps; do NOT inflate)
- **G1 price-calculator** (FEATURE_PLAN §1.B D2): G1a add `FEATURE_PRICE_CALCULATOR_ENABLED: bool = True` to config.py §3.2 after L216; G1b in-handler 404 in `pricing/router.py:76` price_calc (POST/write -> in-handler per smart-picker `category/router.py:117`); G1c `tests/modules/pricing/test_feature_flag.py` NEW (true->not-404; false->404).
- **G2 tracking-dashboard** (FEATURE_PLAN §2.2 D3): G2a add `FEATURE_TRACKING_DASHBOARD_ENABLED: bool = True`; G2b in-handler 404 in `dashboard/router.py:86` list_products. DIVERGENCE (R1): GET/read route but D3 explicitly mandates 404 because dashboard IS the feature -> honor plan; G2c `tests/modules/dashboard/test_feature_flag.py` NEW.
- **G3 live-preview** (FEATURE_PLAN §3 D3): G3a add `FEATURE_LIVE_PREVIEW_ENABLED: bool = False` (default False! gated rollout); G3b in-handler 404 in `catalog/router.py:268` preview, body `{"detail":"Preview unavailable","code":"feature.live_preview.disabled"}` (NOT new core/feature_flags.py — R3); G3c `tests/integration/test_live_preview_flag_404.py` NEW (default-False -> 404; override true -> not-404).

---

## Drift notes (5 done features coexisting — FOUNDER FYI, do NOT churn)
- **D-1 guard-mechanism drift (as-is, accepted at each prior gate):** catalog-form = main.py conditional-include (`main.py:126`, whole-module 404); ai-autofill/smart-picker = in-handler raise (per-route); xlsx/image = in-handler POST gate. Both valid; conditional-include cheaper for whole-module flag, in-handler the precedent for single-route flag in multi-route module. The 3 new gaps all target single routes -> all use in-handler raise (smart-picker consistent). Cosmetic only; master-plan §3.2 amendment candidate IF founder wants one canonical mechanism, not required.
- **D-2 Gate-1 unit RED on develop** (infra PR #145, tip 2b5ec60): not this sweep's scope; new flag-404 tests must not worsen it — markers consistent w/ precedent + verify in isolation per Py3.11 session-loop gotcha. Cross-ref at merge gate.

---

## Founder rulings needed (FLAG, do not pick)
- **R1 GET-route flag-404 divergence (G2+G3).** Convention = write routes get 404, read routes stay usable. But tracking-dashboard D3 + live-preview D3 BOTH explicitly mandate 404-on-read (the read route IS the feature). Recommendation: HONOR THE PLANS — in-handler 404 on the GET routes. Confirm.
- **R2 message-id wording.** price-calc says `feature.disabled`; live-preview says `feature.live_preview.disabled`; smart-picker has its own. Recommendation: match each plan verbatim (G1->feature.disabled, G3->feature.live_preview.disabled, G2->feature.disabled). FLAG: `feature.*` likely out of §5A.H 3-segment `validation.*` regex scope — confirm.
- **R3 core/feature_flags.py vs in-handler.** live-preview floats a NEW generic `require_feature_flag(name)` dependency factory (absent on develop). Recommendation: do NOT introduce for V1 parity (every as-built flag = in-handler raise; new abstraction for 3 routes = scope creep). Defer to V1.5. Confirm in-handler.
- **R4 live-preview default False.** Unlike all others (True), G3a mandates bool=False (gated rollout). Confirm ship default-False (test overrides to true for not-404 path).

---

## Scope — ONE api-routes-builder slice on chore/flag-parity
All 3 gaps = config field + in-handler guard + flag-404 test = pure api-routes-builder. NO database-builder (no schema), NO services-builder (request-time settings read in handler). ONE branch, ONE PR. Consolidation precedent (chore batches).
Branch chore/flag-parity off origin/develop 2b5ec60, worktree /tmp/mesell-wt/flag-parity, pushed.

## Carry to STEP 2/3
- Dispatch ONE meesell-api-routes-builder (sonnet) from master, session mesell-flag-parity-sweep-session-1, SPEC below.
- Settle R1-R4 before dispatch (R1 honor plans; R3 in-handler; R4 default False).
- Merge gate: squash chore/flag-parity -> develop directly (chore, D1 N/A, ci-gate-fix precedent).
- Verify 3 new tests green; run new async test dirs IN ISOLATION on Py3.11 (MEMORY.md gotcha).

## Files touched STEP 1
- this memo (NEW); feature_board_backend.md IN PROGRESS row; STATUS_BACKEND.md UPDATE block; MEMORY.md index+learnings.
## NOT touched
- No feature code; no frontend/k8s/terraform/.github; no other agent memory; no LOCKED arch section.

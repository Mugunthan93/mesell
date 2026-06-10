# §17 Endpoint Inventory Audit Report

**Date:** 2026-06-08
**Auditor sub-session:** meesell-backend-verification-17-endpoints-1
**Section under audit:** §17 Endpoint Inventory (27 contract + 2 infrastructure surfaces)
**Method:** Live `app.routes` introspection (`.venv/bin/python`) + per-router static inspection (all 8 modules) + owning-section (§7–§14) cross-check + middleware (`audit_mw`, `rate_limit_mw`, `plan_guard`) inspection + boot-test run.
**Overall verdict:** **PARTIAL** — endpoint *surfaces*, *auth posture*, and *plan-guard core* are substantially correct; §17's consolidated **Rate-Limit** and **Audit-Event** columns have **systematically drifted** from the owning module sections (§7–§14), and four **code-level audit/plan defects** were found. No endpoint is missing or unauthorized. No regressions.

---

## Audit checklist results

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | 27 contract endpoints mounted | **PARTIAL** | Live = 26 distinct contract `APIRoute`s (rows 1–26) + 2 infra = **28** `/api/v1` routes. "27" reconciles via §17.B.1 placeholder row 27. All surfaces present **except** row 25 path drift (F1). |
| 2 | 2 infrastructure endpoints mounted | **PASS** | `GET /api/v1/auth/me` ✓ + `POST /api/v1/webhooks/razorpay` ✓ both live. |
| 3 | Auth posture (per §17.C) | **PASS** (1 count note) | Per-route auth mode correct on all 28: **23 JWT / 2 cookie / 2 none / 1 HMAC**. §17.C headline "22 JWT" undercounts by 1 (rows 5–26 = 22 **+ I1** = 23). |
| 4 | Rate-limit decorators correct | **FAIL** | 5 §17 registry values wrong (rows 4,6,7,8,19,23) + systemic key-distribution deviation (decorator has no `key=` param). |
| 5 | Audit event distribution correct | **FAIL** | §17.F names wrong on 10 of 14; row 1 event fictional; customer/export emit catch-all names (missing `@audit_event`); no read-flood gate. |
| 6 | Plan_guard 4 resources enforced | **PARTIAL** | 3/4 enforced with correct names+limits; `create_product_hourly` defined-but-unenforced; autosave coalescing regex never matches PATCH path. |

---

## Live route inventory (authoritative)

`28` routes under `/api/v1` (introspected from `app.main:app`):

```
NONE (2):    POST /auth/otp/send · POST /auth/otp/verify
COOKIE (2):  POST /auth/refresh · POST /auth/logout
JWT (23):    GET /auth/me · GET|PATCH /seller-profile · PATCH /seller-profile/active-categories
             · PATCH /seller-profile/compliance/{super_id} · GET /seller-profile/required-fields
             · GET /categories/suggest|browse · GET /categories · GET /categories/{id}/schema
             · GET /categories/{id}/field-enum/{name} · POST /products · PATCH|DELETE /products/{id}
             · POST /products/{id}/autofill · GET /products/{id}/preview · GET /products/{id}/draft
             · POST|GET /products/{id}/images · POST /products/{id}/price-calc · GET /products (dashboard)
             · POST /products/{product_id}/export-xlsx · GET /exports/{export_id}
HMAC (1):    POST /webhooks/razorpay
```

Total app surface (dev) = **34** (28 + `/health` + `/docs` + `/docs/oauth2-redirect` + `/redoc` + `/openapi.json`; `/dev-static` is a Mount, not a Route). Boot test **8/8 PASS**.

---

## Non-compliance findings

### F1 — Export create path drift (§17 registry defect; code correct)
- **§17.B row 25** records `POST /api/v1/exports`. **Owning §14.B.1** (line 5162) locks `POST /api/v1/products/{id}/export-xlsx`, and the **code matches the owning section** (`export/router.py:88`).
- §17's own preamble: *"§17 does NOT introduce new contracts — every endpoint is locked at its owning module's §X.B."* → the **owning section wins**; §17.B row 25 path is the defect.
- Same drift also at **§18.B (line 6968), §18 retry (7037), §22 acceptance (7870)** — all say `/api/v1/exports`.
- **Class:** identical pattern to the already-resolved `export.xlsx`/`export.generate` §14.E-vs-§17 inconsistency (founder ruled owning section wins). **Recommend founder ruling + §17/§18/§22 path correction.**

### F2 — Route-count narrative inaccurate (§17 doc defect)
- §17.G asserts **"29 routes mounted"**; §17.B.3 asserts **"35 total"**. Live reality = **28** `/api/v1` routes, **34** total (dev).
- Root cause: §17.B.1 correctly says there are **26 distinct contract rows** (row 27 is a counter-alignment *placeholder*), but §17.B.2/§17.G/§17.B.3 then treat "27" as 27 real mounted routes → overcount by 1 (28→"29", 34→"35").
- §17.B.3's "5 FastAPI defaults (`/docs`,`/redoc`,`/openapi.json`,`/`,`/favicon.ico`)" is also wrong — actual defaults are `/docs`,`/docs/oauth2-redirect`,`/redoc`,`/openapi.json`.
- The cited §19 boot test does **not** assert 29/35 (it only checks otp routes + framework + `/health`). No operational breakage; doc prose only.

### F3 — Rate-limit registry values wrong (§17 defects; owning + code agree)
Per-route adjudication against the **literal owning §X.B** decorators:

| Row | Endpoint | §17.B value | Owning §X.B | Code | Fault |
|---|---|---|---|---|---|
| 4 | POST /auth/logout | 60/h/user | §7.B.4 = **none** (idempotent) | none | **§17 wrong** |
| 6 | PATCH /seller-profile | 20/h/user | §8.B.2 = **60/h** | 60/h | **§17 wrong** |
| 7 | PATCH /…/active-categories | 20/h/user | §8.B.3 = **60/h** | 60/h | **§17 wrong** |
| 8 | PATCH /…/compliance/{id} | 20/h/user | §8.B.4 = **60/h** | 60/h | **§17 wrong** |
| 19 | DELETE /products/{id} | 10/h/user | §10.B.5 = **60/h** | 60/h | **§17 wrong** |
| 23 | POST /…/price-calc | 30/h/user | §12.B.1 = **per-IP only** | 600/h/user | **§17 wrong** + code dev (F4) |

### F4 — Rate-limit KEY deviation is systemic (code deviation; documented D-flags)
- The Wave-1 `@rate_limit(scope, limit, window)` decorator (`core/middleware/rate_limit_mw.py`) has **no `key=` parameter**. Effective keying: **authenticated routes → per-user; anonymous routes → per-IP** — automatically, with no override.
- Consequence: §17.D's KEY distribution is **not achieved at runtime**:
  - Rows 1–2 OTP: §17 + owning = **per-phone**; runtime = **per-IP** (anon).
  - Rows 3–4 refresh/logout: §17 = per-user/cookie-user; runtime = **per-IP** (anon, no `get_current_user`).
  - Rows 16/18/20/22/24 + 23: owning §X.B = **per-IP only** (`key="ip"`); runtime = **per-user** (auth) — *inverted*, and rows 23/24 ADD a 600/h cap where the owning section wanted per-IP fallback only.
- **Documented** as D-flags in every router (iam D2, customer §8-ROUTES-D1, catalog D-notes, pricing, dashboard §13-D1). Stated V1.5 fix = decorator `key=` enhancement. **Not a §17 defect; a known accepted code limitation that §17.D's table silently misrepresents.**

### F5 — Audit-event names: §17.F drifted on 10 of 14 (§17 defects)
Actual emitted names (service direct-writes for iam; `@audit_event` decorators for catalog/image/pricing; verified in code):

| Row | §17.F name | Actual emitted (code) | Owning §X.I | Fault |
|---|---|---|---|---|
| 1 | `otp.send.requested` | **(none emitted)** | §7 — no send-success event | **§17 fictional** |
| 2 | `auth.login` | `auth.login.success` / `.failed` | §7.B.2 | §17 wrong |
| 3 | `auth.refresh` | `auth.token.refreshed` / `.refresh_failed` | §7.B.3 / §15.E | §17 wrong |
| 4 | `auth.logout` | `auth.logout` | §7.B.4 | **MATCH ✓** |
| 15 | `product.create` | `catalog.product.created` | §10.B.1 | §17 wrong |
| 16 | `product.patch` | `catalog.product.updated` | §10.B.2 | §17 wrong |
| 17 | `product.autofill` | `catalog.autofill.invoked` | §10.B.3 | §17 wrong |
| 19 | `product.delete` | `catalog.product.deleted` | §10.B.5 | §17 wrong |
| 21 | `image.upload.received` | `image.upload.received` | §11.J | **MATCH ✓** |
| 23 | `pricing.calc.created` | `pricing.calculated` | §12.I / §15.E | §17 wrong |
| 25 | `product.export.initiated` | **catch-all** (F6) | §14.J = `export.initiated` | §17 wrong + code (F6) |
| I2 | `razorpay.webhook.received` | `razorpay.webhook.captured` | §7.B.6 | §17 wrong |

Only **2 of 14** §17.F names (rows 4, 21) are correct. (iam rows 6/7/8 customer events `seller_profile.update`/`active_categories_update`/`compliance_update` in §17.F also mismatch owning §8 `customer.active_categories.updated` AND are not actually emitted — see F6.)

### F6 — CODE defect: customer (3 PATCH) + export (POST) lack `@audit_event` → catch-all event_type written to DB
- `customer/router.py` and `export/router.py` import only `rate_limit` (NOT `audit_event`); their write handlers carry no `@audit_event` decorator.
- `audit_mw._derive_event_type` (audit_mw.py:171) falls back to `"{method}.{path}"[:40]` when untagged. Result rows actually written:
  - row 6 → `patch./api/v1/seller-profile` · row 7 → `patch./api/v1/seller-profile/active-cat` (truncated) · row 8 → truncated · row 25 → `post./api/v1/products/{product_id}/expo` (truncated).
- These match **neither** §17.F **nor** the owning §8/§14 names. **Functional defect** — semantically meaningless event_types persisted. (Catalog/image/pricing are unaffected — they carry explicit decorators.)

### F7 — CODE defect: `audit_mw` has no read-flood / method gate
- Write gate is only: (1) 2xx, (2) `request.state.user_id` set, (3) autosave coalesce. **No GET/read-only exclusion.**
- Any authenticated 2xx **GET** (e.g. `/auth/me`, `/categories`, `/products/{id}/preview`, dashboard `/products`, `/exports/{id}`) therefore writes a catch-all `get.{path}` row — **contradicting the §17.F "NONE (read-only)" posture** and the `MVP_ARCH §11.3` read-flood rule the architecture repeatedly cites. Owner = §4.G / §15.E. **Recommend §4.G middleware review.**

### F8 — CODE defect: `create_product_hourly` plan-guard resource defined but never enforced
- `core/plan_guard.py` defines all 4 §17.E resources (`product_count` 100, `ai_autofill_hourly` 50/h, `smart_picker_hourly` 100/h, `create_product_hourly` 20/h).
- `enforce_plan_limit` is called for **only 3**: `product_count` (catalog/service.py:394), `ai_autofill_hourly` (:610), `smart_picker_hourly` (category/service.py:226). **`create_product_hourly` is never invoked.**
- §17.B row 15 / §17.E claim POST /products enforces **`create_product_hourly` + product_count**. The 20/h create cap *is* enforced — but via `@rate_limit(scope="create_product", limit=20)` (security layer), not via plan_guard. Functionally covered; **§17.E's plan-guard attribution is half-met** and the plan resource is dead code at the plan layer.

### F9 — Autosave coalescing not wired to PATCH path (documented D2)
- §17.F row 16 + §15.E claim `product.patch` coalesces 5-min per `(user_id, product_id)`. `audit_mw._AUTOSAVE_PATH` regex matches only `/products/{id}/(draft|autosave)` — **NOT** `PATCH /products/{id}`. So PATCH events never coalesce → the 30× volume reduction is not achieved. Documented as catalog router DECISION FLAG §10-CATALOG-D2 ("regex widen queued as a §4.G amendment").

---

## What PASSED cleanly
- **All 28 route surfaces mounted** (26 contract + 2 infra); no missing, no stray/unauthorized endpoint. Boot test 8/8.
- **Per-route auth posture correct** on every endpoint: 23 JWT (`Depends(get_current_user)`), 2 cookie-only (`Cookie()`, no JWT dep — refresh/logout), 2 public (otp send/verify), 1 HMAC (webhook reads `X-Razorpay-Signature`, raw body before parse). The payment-adjacent webhook is correctly HMAC-gated; no auth-posture regression on any critical endpoint.
- **Plan-guard core (3/4):** `product_count`, `ai_autofill_hourly`, `smart_picker_hourly` enforced inside the correct services with names + limits exactly matching §17.E/§4.E.
- **Rate-limit LIMIT magnitudes** correct on rows 1 (3/h), 2 (10/h), 10 (100/h), 15 (20/h), 17 (50/h), 21 (10/min) — these match §17.B.
- Audit-event names correct on rows 4 (`auth.logout`) + 21 (`image.upload.received`).

---

## Verdict rationale

§17 fulfils its **operational** purpose — it is an accurate *route-registration checklist* (every surface it lists is mounted; nothing extra is mounted). But as the **single-source-of-truth consolidation** it claims to be, its derived columns have decayed relative to the owning sections it is contractually bound to mirror:

- **Rate-Limit column:** 5 wrong values (rows 4,6,7,8,19,23) + a KEY distribution (§17.D) that no longer reflects the decorator's per-user/per-IP-only reality.
- **Audit-Event column:** only 2 of 14 names match the code/owning sections; 1 name is fictional.
- **Path (row 25)** + **route counts (§17.G/§17.B.3)** drifted.

Separately, the audit surfaced **four genuine code defects** (F6 catch-all event names, F7 read-flood, F8 unenforced `create_product_hourly`, F9 coalescing regex) that are NOT mere doc drift — these are owned by §4.G/§8/§14 construction, not §17, but are reported here because they were found while validating §17.F/§17.E compliance.

Because no endpoint is missing/unauthorized, auth posture is correct, and plan-guard core holds, this is **PARTIAL**, not FAIL. Checks 4 and 5 individually FAIL.

---

## Hand-back to master

**Per HARD RULES, nothing was modified.** Recommended remediation (master → founder):

1. **Founder ruling (precedent: export.xlsx/export.generate)** on the §17-vs-owning-section drifts — owning sections (§7–§14) are authoritative; correct §17's Rate-Limit values (rows 4,6,7,8,19,23), Audit-Event names (10 rows), row-25 path, and the §17.G/§17.B.3 route counts (29→28, 35→34) + §17.C JWT count (22→23). Mirror path fix into §18.B/§22.
2. **Code tickets** (separate from §17 doc fix): F6 add `@audit_event` to customer 3 PATCH + export POST; F7 add read-only method gate to `audit_mw`; F8 enforce `create_product_hourly` or re-document it as rate-limit-layer-only; F9 widen autosave regex (already queued).
3. **Accept-as-documented:** F4 rate-limit `key=` deviation (V1.5 decorator enhancement) — but §17.D's KEY table should carry a deviation note.

**Escalation triggers:** none fired (no count mismatch beyond the documented placeholder; auth posture correct on all critical endpoints incl. webhook HMAC; OTP abuse limits 3/h + 10/h present). The §17 registry drift + F6/F7/F8 are **report-and-decide**, not stop-the-line.

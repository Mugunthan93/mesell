# SUB-PLAN G — `iam` Service Extraction (the auth authority)

**STATUS: PHASE 1 (sub-plan + spec) — DOCS-ONLY. Execution Phase 2 GATED on Wave MS-3 complete.**
Authored under session `mesell-ms-iam-session-1` (2026-06-12, MS-PAR-1 parallel program).
This is the iam extraction sub-plan — MASTER_PLAN §4 row **G** (`iam`, complexity **L**),
re-keyed to **Wave MS-4** by the MS-PAR-1 federation pattern (pilot → parallel pairs → riskiest last).

> **Filename alias note.** MASTER_PLAN §4's roster row calls this file
> `SUB_PLAN_07_iam_extraction.md` (the original serial-order numbering). The
> MS-PAR-1 dispatch (newer founder ruling, `00-ms-parallel-program-dispatch.md`)
> names it **`SUB_PLAN_0G_iam_extraction.md`** (wave-letter convention, parallel
> with `SUB_PLAN_0F_category_extraction.md`). **This file uses the MS-PAR-1 name
> `SUB_PLAN_0G`.** The `_07_` alias refers to the same artifact; do not author a
> second file.

> **Wave / gating header (MS-PAR-1).**
> - **Wave:** MS-4 (`F category ‖ G iam`).
> - **Execution opens when:** Wave MS-3 complete — BOTH the `D pricing` AND
>   `E customer` founder-gate PRs merged to `develop` (MS-PAR-1 wave table).
> - **Parallel partner:** **MS-F (category)** runs concurrently. Shared-file
>   discipline (common rule 4) — this names the **SAME three shared surfaces** as
>   `SUB_PLAN_0F_category_extraction.md` (0F §"MS-4 parallel note" + 0F R6, which
>   lists `main.py` additive-minimal, Traefik/gateway + `k8s/` as new manifests, and
>   shared `JWT_SECRET`): `backend/app/main.py` router removal is additive-minimal
>   (delete the single `main.py:114` iam `include_router` + its import at cutover
>   ONLY — touch nothing else); gateway/Traefik + `k8s/` shared files are additive
>   (new svc-iam manifests, NOT edits to category's); the iam integration branch
>   merges `origin/develop` BEFORE its founder-gate PR opens; union-merge conflicts
>   keep-both. **D7 parallel-safety:** iam and category never couple on the request
>   path — both validate JWTs LOCALLY via vendored `core/auth.py` + the shared
>   Secret-Manager `JWT_SECRET` (0F F2 / R6), so neither needs the other up to serve.
> - **Dev cluster only.** No staging/prod. Strangler-fig: the monolith keeps
>   serving `/api/v1/auth/*` until the founder-gated cutover flip.

> Authoritative inputs read for this sub-plan (authored 2026-06-12 against develop
> `6d6ee51`; **re-grounded 2026-06-12 at origin/develop `aa7513e`** — see §0.1 + v1.1
> revision row):
> - `docs/plans/microservices_migration/MASTER_PLAN.md` (v1.3, §3.A.1-aware — §2.D schema-isolation table, §2.D cross-schema-FK drop policy, §3.B dependency-order rationale [iam second-to-last], §5.A A2/D7 lock, §5.D secrets mapping, §6 Risk #2 [iam breaks every authenticated route])
> - `docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md` (the SHAPE TEMPLATE — canonical section structure)
> - `docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md` (MS-PAR-1 common rules — Wave-6 lessons are LAW)
> - AS-BUILT SOURCE: `backend/app/modules/iam/{router,service,repository,domain,schemas,exceptions,__init__}.py`, `backend/app/core/auth.py`, `backend/app/core/middleware/*`, `backend/app/main.py`, `backend/app/shared/models/*.py`, `backend/alembic/versions/935e55b4852c_v1_baseline_13_tables.py`
> - `.claude/agent-memory/meesell-backend-coordinator/{spec_msA_backend.md, handoff_msA_infra.md, auth_otp_feature.md, reference_authoritative_endpoint_inventory.md}` (extraction recipe + MS-A shim freeze + FE-D5 contract)

---

## 0. GROUND TRUTH — verified against source 2026-06-12 (NOT plan prose)

Per Wave-6 law (common rule 3): every contract below is cited `file:line` from the
as-built tree. Contracts were authored against develop `6d6ee51` and **re-verified
against origin/develop `aa7513e`** (§0.1); the `modules/iam/` tree + `core/auth.py`
were byte-identical across that rebase, so all `file:line` citations hold unchanged.
Where MASTER_PLAN prose disagrees with source, the source wins and the contradiction
is flagged (§0.7).

### 0.1 Branch / tree state

This is a docs-only Phase-1 session committed on `docs/msG-subplan-0G`. It was
**authored against local develop `6d6ee51`**, then **re-grounded at origin/develop
`aa7513e`** (the true origin tip — local develop was behind origin at authoring time;
the branch was rebased onto `aa7513e`).

**Rebase reconciliation (`6d6ee51` → `aa7513e`).** `git diff 6d6ee51 aa7513e --stat --
backend/app/modules/iam/ backend/app/core/auth.py` = **EMPTY** — the iam module and the
vendored-everywhere `core/auth.py` are **byte-identical** across the rebase, so every
`file:line` citation in §0.2–§0.7 holds verbatim (incl. `main.py:114` iam mount, §0.6
FE-D5 cookie/allowlist lines, §0.7 6-FK set). Three core files changed between the two
bases and were inspected — **all inert for iam**:
> - `core/middleware/audit_mw.py` — `_is_autosave(method, path)` widened to coalesce
>   bare `PATCH /api/v1/products/{id}` (catalog-form autosave). Matches **only**
>   `/api/v1/products/{id}` — iam's routes are `/api/v1/auth/*` + `/api/v1/webhooks/razorpay`,
>   never matched. iam-svc ships this vendored `audit_mw` carrying the widening, which is
>   **catalog-path-only and inert for every iam route**. No statement in §0.6 (vendored
>   6-mw chain) is contradicted.
> - `core/tenancy.py` — added `_GLOBAL_TABLES` frozenset
>   `{categories, templates, field_enum_values, field_aliases}` + `__all__` export. A
>   **documentation sentinel** (not yet a §19 linter input). None of the four tables is an
>   iam table (`users`, `audit_events`); the carve-out is irrelevant to iam's scoping.
>   No §0.6 statement contradicted.
> - `main.py` — catalog router mount wrapped in `if settings.FEATURE_CATALOG_FORM_ENABLED:`
>   at `main.py:123+`, **below** the unchanged iam mount at `main.py:114`. iam mount and
>   ordering unaffected.

The Phase-2 coding session cuts from `origin/develop` tip at execution time (after the
MS-3 + MS-4-sibling merges move develop forward). Per the MS-A op-learning (spec_msA §0.1)
— reinforced by this very rebase (local develop trailed origin) — ALWAYS re-verify
`git ls-remote origin develop` at coding-session start and cut from the **live origin
tip**, never a stale local `develop`.

### 0.2 iam module = 7 files — CONFIRMED

`backend/app/modules/iam/`: `__init__.py`, `domain.py`, `exceptions.py`, `repository.py`,
`router.py`, `schemas.py`, `service.py` = **7 files**. iam has **NO `tasks.py`** (no Celery —
confirmed by `MASTER_PLAN §1.A` "Celery? no" for iam). This is one fewer file than export's 8.

### 0.3 MOUNTED iam routes — VERIFIED IN main.py (the row-26 lesson)

The row-26 lesson is LAW: count MOUNTED `APIRoute` objects, not schema existence.
`backend/app/main.py:114` `app.include_router(iam_router)` — the iam router is mounted FIRST
of the 8 routers. The iam router (`backend/app/modules/iam/router.py:99`
`APIRouter(prefix="/api/v1", tags=["iam"])`) declares **exactly 6 route decorators**:

| # | Method + path | router.py decorator line | response | auth posture | rate-limit |
|---|---|---|---|---|---|
| 1 | `POST /api/v1/auth/otp/send` | `:105` | 202 `SendOtpResponse` | PUBLIC (per-IP) | `@rate_limit(scope="otp_send", limit=3, window=3600)` `:111` |
| 2 | `POST /api/v1/auth/otp/verify` | `:124` | 200 `VerifyOtpResponse` + Set-Cookie | PUBLIC (per-IP) | `@rate_limit(scope="otp_verify", limit=10, window=3600)` `:129` |
| 3 | `POST /api/v1/auth/refresh` | `:152` | 200 `RefreshResponse` + Set-Cookie | COOKIE (refresh_token) | `@rate_limit(scope="auth_refresh", limit=60, window=3600)` `:157` |
| 4 | `POST /api/v1/auth/logout` | `:194` | 204 + clear-cookie | COOKIE (refresh_token) | NONE (idempotent, no abuse vector — `:205`) |
| 5 | `GET /api/v1/auth/me` | `:220` | 200 `MeResponse` | JWT (`Depends(get_current_user)` `:226`) | NONE (per-IP floor — `:229`) |
| 6 | `POST /api/v1/webhooks/razorpay` | `:247` | 200 `WebhookCaptureResponse` | HMAC (X-Razorpay-Signature) | NONE |

This matches MASTER_PLAN §1.A ("iam: 6 (4 auth + /me + razorpay webhook)") and the
endpoint-inventory memory exactly. **6 mounted routes is the inventory unit** Phase-2
api-routes-builder must reproduce — no more, no less.

Auth-posture breakdown (the §17 audit shape for iam's slice): 1 JWT (`/me`) + 2 cookie
(`/refresh`, `/logout`) + 2 public (`/otp/send`, `/otp/verify`) + 1 HMAC (`/webhooks/razorpay`).

### 0.4 iam is ALL-✗ in the cross-module call matrix — NO inbound /internal/* shim

**This is the defining structural difference from every other extraction.** Per
MASTER_PLAN §1.C / §2.D: `iam` is all-`✗` by design — "its contract to other modules
is the `get_current_user` middleware, NOT a service call."

Verified against source:
- **iam has ZERO outbound cross-module calls.** `backend/app/modules/iam/service.py`
  imports `app.adapters.msg91` (`:33`), `app.adapters.razorpay` (`:34`),
  `app.core.auth` (`:35`), `app.core.metrics` (`:42`), `app.modules.iam.{repository,domain,exceptions}`,
  `app.shared.{config,database}`, `app.shared.models.audit_event` (`:64`). It imports
  **NO `app.modules.<other>` service.** So iam needs **ZERO `core/extracted_clients/` shims**
  (unlike export's 4). iam-svc is a pure leaf-producer of identity.
- **iam has ZERO inbound cross-module service calls.** MS-A's export extraction froze
  6 `/internal/*` shims against catalog(2)/category(2)/customer(1)/image(1) —
  **NONE against iam** (verified: `spec_msA_backend.md §0.4`; the only iam mentions in
  MS-A artifacts are MASTER_PLAN/SUB_PLAN_01 prose, not a shim contract). No earlier
  wave (MS-1..3) freezes any iam `/internal/*` endpoint either, because every consumer
  reaches identity through the **vendored middleware + shared JWT secret**, never an
  HTTP call to iam.

**CONSEQUENCE (encode prominently — inventing a shim is a reject):** iam-svc exposes
its 6 public routes through Traefik and **NO `/internal/*` routes at all.** Do NOT
invent an iam `/internal/*` shim. iam's "contract to other services" is two artifacts,
both already in every service image per A2/D7:
1. the vendored `core/auth.py` (`get_current_user` + JWT verify + refresh primitives), and
2. the shared `JWT_SECRET` (HS256) from Secret Manager.

### 0.5 The vendored-everywhere auth surface — `core/auth.py` (A2/D7 anchor)

`backend/app/core/auth.py` is the single most load-bearing file in the extraction. It is
**already vendored into every extracted service** per the A2/D7 lock (export-svc vendors
the 6-mw chain incl. `auth_mw` which depends on this). Its public surface (`__all__`
`:521-535`):

| Symbol | auth.py line | Role |
|---|---|---|
| `CurrentUser` (frozen dataclass `{user_id, plan}`) | `:116` | the shape every authenticated route receives |
| `get_current_user` (FastAPI dep) | `:250` | LOCAL JWT decode + `users` row lookup → `CurrentUser` |
| `issue_access_token(user_id, plan)` | `:210` | HS256 JWT, claims `{sub, exp, plan}` `:221-225` |
| `issue_refresh_token()` | `:306` | opaque `secrets.token_urlsafe(48)` |
| `refresh_allowlist_key(token, *, pepper, version)` | `:329` | **dual-pepper versioned key** `cache:refresh:v{N}:{hmac_sha256(token, pepper)}` `:370` |
| `validate_refresh_allowlist(valkey, token)` | `:373` | dual-pepper READ (current vN, fallback vN-1), returns `(matched_key, value)` |
| `compare_tokens(a, b)` | `:420` | `secrets.compare_digest` constant-time |
| `rotate_refresh_token(valkey, old_key, new_key, new_value, ttl)` | `:465` | EVALSHA→EVAL Lua atomic rotation |
| `REFRESH_ROTATE_LUA` | `:435` | the verbatim Lua body (GET→DEL→SET, returns 1/0) |
| `TokenMissingError` / `TokenExpiredError` / `UserNotFoundError` | `:133/:154/:171` | 401/401/403 auth exceptions (MeesellError subclasses) |

**Key extraction fact:** `core/auth.py`'s import allowlist (`:41-44` docstring) is
`shared.*` + `core.errors` ONLY — never `app.modules.*` or `app.adapters.*`. This is what
makes it cleanly vendorable: it has no module dependencies. iam-svc ships the IDENTICAL
file; so does every other service. There is exactly ONE behavioral difference: iam-svc is
the only service that also runs the **issuance/rotation** functions
(`issue_access_token`, `issue_refresh_token`, `rotate_refresh_token`) from a route;
other services call only the **verification** half (`get_current_user`). Same file, same
secret, different call sites. Zero code divergence — verified-identical vendoring is a
merge-gate check (§"Review + iteration protocol").

### 0.6 The FE-D5 cookie + allowlist contract — LIVE and FROZEN (cited from source)

The frontend is live against this. Zero drift permitted. Cited from source:

**Cookie attributes** (`router.py:68-93`, `_set_refresh_cookie` / `_clear_refresh_cookie`):
- name `refresh_token` (`router.py:63`)
- **`path=/api/v1/auth`** (`router.py:64` `_REFRESH_COOKIE_PATH = "/api/v1/auth"`) — NOT `/auth`
- `domain=.mesell.xyz` (`router.py:65`)
- `secure=True`, `httponly=True`, `samesite="strict"` (`router.py:76-78`)
- Set on `/otp/verify` 2xx (`router.py:142`) and `/refresh` 2xx (`router.py:184`);
  cleared (Max-Age=0) on `/refresh` 401 (`router.py:181`) and `/logout` (`router.py:212`).

**Valkey DB 0 allowlist keyspace** (`core/auth.py:329-370`):
- Key format `cache:refresh:v{version}:{hmac_sha256(token, pepper)}` (`:370`).
- HMAC-with-pepper, NOT bare SHA-256 (`:365-369` `hmac.new(pepper, token, hashlib.sha256)`).
- **Dual-pepper (R5, landed PR #66):** `version` segment + `validate_refresh_allowlist`
  reads current `vN` then falls back to `vN-1` with `REFRESH_TOKEN_PEPPER_PREVIOUS`
  (`:401-410`). Writes ALWAYS use current `vN` (`:394-398`).
- Read by `service.verify_otp_and_issue_tokens` (`service.py:355` SET on issue),
  `service.rotate_refresh_token` (`service.py:423` validate + `:452` rotate),
  `service.revoke_refresh_token` (`service.py:528` validate + `:537` DEL).

**Rotation Lua (verbatim, `core/auth.py:435-443`):**
```
if redis.call('GET', KEYS[1]) then
    redis.call('DEL', KEYS[1])
    redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2])
    return 1
else
    return 0
end
```
Loaded once via `load_lua_script` → cached SHA1 → `EVALSHA` thereafter with `EVAL`
fallback on NOSCRIPT (`core/auth.py:495-506`).

**FROZEN-VERBATIM mandate for iam-svc:** the extracted service ships `core/auth.py`
byte-for-byte (the same allowlist key derivation, the same Lua, the same dual-pepper read),
AND `router.py`'s cookie helpers byte-for-byte (same Path, Domain, attrs). The Traefik
route for iam-svc MUST preserve `/api/v1/auth/*` EXACTLY — **no path-strip / rewrite** that
alters the `Set-Cookie: ...; Path=/api/v1/auth` scoping. A path rewrite that drops or
rewrites the `/api/v1/auth` prefix breaks the cookie's `Path` scoping and every live
frontend session silently fails to send the refresh cookie. This is the single highest-blast-radius
infra constraint in the whole migration — it is repeated in the infra handoff (§I4) and the
acceptance gate.

### 0.7 Cross-schema FKs referencing `users(id)` — the DROP set (cited from source)

Per MASTER_PLAN §2.D locked policy: "we **drop** these cross-schema FKs as part of the
iam extraction … We rely on application-layer enforcement (`assert_owned` + the existing
`scope_to_user` predicates)." iam owns schema `iam` (table `users`); after `users` moves
to schema `iam`, every FK that points at `users.id` from a table in another schema becomes
a cross-schema FK and is DROPPED.

**The complete DROP set — 6 FKs (verified in both ORM models AND the baseline migration):**

| # | FK | ORM model:line | Baseline migration:line | ondelete | Belongs to schema (post-split) |
|---|---|---|---|---|---|
| 1 | `audit_events.user_id → users.id` | `audit_event.py:54` | `935e55b4852c:66` | RESTRICT | `public` (shared audit table) |
| 2 | `seller_profile.user_id → users.id` (`fk_seller_profile_user_id`) | `seller_profile.py:123` | `935e55b4852c:105` | CASCADE | `customer` |
| 3 | `catalogs.user_id → users.id` | `catalog.py:42` | `935e55b4852c:118` | CASCADE | `catalog` |
| 4 | `products.user_id → users.id` | `product.py:55` | `935e55b4852c:149` | RESTRICT | `catalog` |
| 5 | `exports.user_id → users.id` | `export.py:48` | `935e55b4852c:168` | RESTRICT | `export` |
| 6 | `product_drafts.user_id → users.id` (`fk_product_drafts_user_id`) | `product_draft.py:194`† | `935e55b4852c:194` | CASCADE | `catalog` |

† `product_draft.py` uses a table-level `ForeignKeyConstraint(["user_id"], ["users.id"], …, name="fk_product_drafts_user_id")` at `:76-81`; the migration emits it at `:194`.

**Important sequencing nuance (encode for the database-builder spec):** these 6 FKs live on
tables owned by FIVE different services (`public` audit, `customer`, `catalog`×3, `export`).
By Wave MS-4, services A/B/C/D/E (export, dashboard, image, pricing, customer) are ALREADY
extracted and own their schemas; F (category) is extracting in parallel; H (catalog) is NOT
yet extracted. So at iam-extraction time:
- FKs #2 (customer), #5 (export) already point at `users` across schemas (those services
  extracted in waves MS-2/MS-3 but `users` was still in `public` then — so they were
  cross-schema-but-same-public-target, or already dropped by those waves' migrations).
- FKs #1 (audit/public), #3/#4/#6 (catalog, NOT yet extracted at MS-4) still reference
  `public.users` at iam-extraction time.

**SIBLING-OWNERSHIP ANNOTATION (post-rebase reconciliation vs the 4 visible Phase-1
sub-plans).** Two of the six FKs are dropped by a *sibling* extraction at its OWN cutover,
on the referencing-table side, BEFORE iam reaches MS-4 — so by iam-extraction time they may
already be gone from `pg_constraint`:
- **FK #2 `seller_profile.user_id → users.id` (CASCADE) — DROPPED BY CUSTOMER, NOT iam.**
  `SUB_PLAN_0E_customer_extraction.md §0.6 / §"Cross-schema FK drop (Risk #5)"` (0E:144,
  0E:372) locks that customer drops its own `seller_profile.user_id → users.id` FK +
  severs the `relationship("User", …)` back-ref at **customer's MS-3 cutover** (before
  iam's MS-4). iam's migration must therefore expect FK #2 to be **already absent** and
  drop it only if the live `pg_constraint` scan still shows it.
- **FK #5 `exports.user_id → users.id` (RESTRICT)** — export extracted at MS-1
  (`SUB_PLAN_01`); whether its `users.id` FK was dropped then or survives as a
  cross-schema-to-`public.users` FK is resolved by the live scan below.
- FKs #3/#4/#6 belong to **catalog** (`SUB_PLAN_0H`, MS-5, extracts LAST) — catalog is
  in-`public` at MS-4, so these three still reference `public.users` and ARE dropped by the
  iam migration. (Cross-checked against `0C`/`0D`: neither `product_images` (0C:121 — no
  `user_id` column) nor `pricing_calcs` (0D:234 — its cross-schema FK is to `products.id`,
  NOT `users.id`) introduces a NEW `users.id` FK; the set stays at exactly these 6.)
This is precisely why the live `pg_constraint` cross-check below is mandatory rather than
advisory — the database-builder drops the **residual** cross-schema `users` FKs the scan
actually returns, neither asserting the full 6 nor assuming a sibling already cleared one.

**The iam extraction migration drops ALL 6 by name/column**, regardless of which schema the
referencing table currently sits in, because `users` is leaving `public` for schema `iam`.
The Phase-2 database-builder MUST cross-check the actual live FK set with
`SELECT conname, conrelid::regclass FROM pg_constraint WHERE confrelid = 'users'::regclass;`
at execution time (waves MS-2/MS-3 may already have dropped some during their own schema
moves) and drop exactly the residual cross-schema FKs to `users` — neither more nor less.
This is the Risk #5 (silent data-integrity loss) surface; the integrity pre-scan (§"database-builder spec")
runs BEFORE any drop.

**No contradictions found** between MASTER_PLAN §2.D prose and the as-built FK set — the
"`products.user_id REFERENCES users(id)`" example in §2.D is real (`product.py:55`), and the
policy "drop these cross-schema FKs as part of the iam extraction" maps cleanly to the 6-FK
set above. The only refinement source adds over prose: the set is **6 FKs across 5 schemas**,
not just the one `products` example §2.D names.

### 0.8 The DPDP / webhook V1 gaps — carried, NOT fixed in extraction

Two pre-existing V1 gaps live in the iam source and MUST be carried VERBATIM into iam-svc
(extraction preserves behavior; it does not fix bugs):
- **DPDP column gap** (`repository.py:18-32` + `:91-99`): `capture_dpdp=True` is passed but
  `users` has no `dpdp_consented_at` column — the write is a no-op + WARNING log. iam-svc
  preserves this exactly. (V1.5 schema add, out of extraction scope.)
- **Razorpay webhook audit gap** (`service.py:597-632`): the webhook has no `user_id`, and
  `audit_events.user_id` is NOT NULL, so the capture LOGS rather than writing an audit row
  (returns `audit_event_id=0` placeholder). iam-svc preserves this exactly. (V1.5 resolution:
  nullable `user_id` or a `webhook_events` table.)

These are §"Documentation deliverables" hand-off notes, not extraction work.

### 0.9 Test count — re-count at session start (do NOT hardcode)

Per MS-A op-learning (spec_msA §0.9), the dispatch's "~823+" is NOT the `def test_` count
(it is a collected-items / parametrize-expanded measure). The Phase-2 session MUST
`grep -rn "def test_" backend/tests/` at start and assert the full-suite count is **MONOTONIC**
vs the live baseline (the extraction ADDS iam-svc tests, removes none until the 7-day
strangler window closes). iam's own tests live under `tests/modules/iam/` +
`tests/integration/test_iam_*` (per `auth_otp_feature.md`). Quote the live count at PR time;
do NOT assert a hardcoded number.

---

## Decisions

iam carries NO Sub-Plan-time open decisions of its own — every cross-cutting decision it
touches was LOCKED upstream. Recorded here for the Phase-2 session so nothing gets re-litigated:

### G1 — JWT verification stays LOCAL (A2/D7 — LOCKED 2026-06-10, founder ruling, MASTER_PLAN §5.A)

**LOCKED, not open.** The 6-middleware chain (CORS → request_id → auth_mw → tenancy_mw →
rate_limit_mw → plan_guard_mw → audit_mw) is VENDORED per service; JWT VERIFICATION runs
LOCALLY in every service via vendored `core/auth.py` + shared HS256 `JWT_SECRET` from Secret
Manager. **iam-svc owns ONLY OTP/login/issue/refresh/revoke (+ /me + razorpay webhook).**
Gateway-JWT validation was **REJECTED** (Traefik cannot attach the resolved `User`, run
plan_guard, or scope_to_user). **There is NO per-request callback to iam-svc, EVER** — Risk #2
mitigation. iam-svc downtime affects only login/refresh/logout; existing valid access tokens
keep working for their TTL.

**Encode as a reject-class rule:** any Phase-2 artifact that (a) adds an iam `/internal/*`
token-validation endpoint, (b) makes another service call iam to validate a token, or (c)
moves JWT validation to Traefik — is REJECTED at the merge gate, citing §5.A / D7.

### G2 — `iam` contract to other services = vendored middleware + shared secret (NOT an HTTP shim)

**LOCKED corollary of G1 / §0.4.** iam is all-✗ in the dependency matrix. It exposes NO
`/internal/*`. Do NOT invent shim work. (Restated here because it is the single most likely
place a Phase-2 specialist over-builds.)

### G3 — Extraction order — iam SECOND-TO-LAST (CONFIRMATION of locked order)

**CONFIRMED, already locked at §3.B.** iam extracts at order position 7 (Wave MS-4) because
"every other service must have its `get_current_user` shim ready BEFORE iam goes out … By
extracting iam late, we minimize the window during which the monolith does cross-service auth
calls." Since validation is LOCAL (G1), the "shim" is the vendored `core/auth.py` — already
in every service by MS-4. Only catalog (H, MS-5) extracts after iam.

### G4 — Cross-schema FK drop policy (CONFIRMATION of locked §2.D policy)

**CONFIRMED, already locked at §2.D.** The 6 FKs in §0.7 are dropped; application-layer
`assert_owned`/`scope_to_user` (CI Contract 8 `check_scope_to_user.py`) is the replacement
defense. Risk #5 integrity pre-scan runs before any drop.

---

## Agent lineup

Per MASTER_PLAN §4 row G, the iam specialist set differs from export's — `meesell-auth-builder`
leads the heavy lift (it is the sole owner of iam per `iam/__init__.py:3` + §4.B lock).

| Lead | Specialists dispatched | What each specialist builds |
|---|---|---|
| `meesell-backend-coordinator` (lead) | — | Authors this sub-plan + `spec_msG_backend.md`; owns the merge gate `feature/microservices-iam/backend` → `…/integration`; verifies `core/auth.py` + cookie helpers vendored byte-for-byte (§16.G); verifies NO `/internal/*` invented; updates `feature_board_backend.md`. |
| `meesell-backend-coordinator` → `meesell-auth-builder` (opus) | `meesell-auth-builder` | THE HEAVY LIFT. Extracts `service.py` (6 methods) + vendors `core/auth.py` byte-for-byte + the MSG91/razorpay adapter wiring + the FE-D5 cookie/allowlist/dual-pepper contract; builds standalone `main.py` (6-mw chain) and trimmed Settings. |
| `meesell-backend-coordinator` → `meesell-api-routes-builder` (sonnet) | `meesell-api-routes-builder` | Extracts `router.py` (6 routes verbatim incl. cookie helpers + rate-limit decorators) + `schemas.py` (7 Pydantic models); confirms NO `/internal/*`; regenerates standalone OpenAPI (6 endpoints). |
| `meesell-backend-coordinator` → `meesell-services-builder` (opus) | `meesell-services-builder` | Extracts `repository.py` + `domain.py` + `exceptions.py`; vendors the trimmed `shared/{database,config,valkey}.py` + the 6-mw chain + `core/errors.py` + `i18n` subset; preserves the §7.I direct-ORM audit-write path + DPDP/webhook gaps verbatim. (Overlaps auth-builder on shared scaffolding — see dispatch order for the seam.) |
| `meesell-backend-coordinator` → `meesell-database-builder` (sonnet) | `meesell-database-builder` | Authors the `users`-schema-move Alembic migration (`public.users` → schema `iam`, `version_table_schema="iam"`) + the 6-FK DROP (§0.7) + the Risk #5 integrity pre-scan + tested downgrade. |
| `meesell-infra-builder` (standalone, via cross-lead memo `handoff_msG_infra.md`) | — | Dockerfile, K8s Deployment+Service (2-replica min + HPA burst per Risk #2), Traefik IngressRoute preserving `/api/v1/auth/*` EXACTLY, Postgres `iam` schema + `iam_user` role grant, Secret Manager wiring (`refresh-token-pepper` + `razorpay-webhook-secret` + shared `JWT_SECRET` ownership/rotation note). |

### Dispatch order (critical path)

```
PHASE A (parallel — no inter-dependency):
  meesell-database-builder → users schema-move migration + 6-FK DROP + Risk#5 pre-scan + downgrade
  [INFRA LANE — meesell-infra-builder, NOT a backend specialist — see handoff_msG_infra.md]

PHASE B (depends on A — service code targets the new iam schema):
  meesell-auth-builder      → THE HEAVY LIFT: service.py (6 methods) + vendored core/auth.py (byte-for-byte)
                              + MSG91/razorpay adapters + FE-D5 cookie/allowlist/dual-pepper + standalone main.py
  meesell-services-builder  → repository.py + domain.py + exceptions.py + vendored shared/* + 6-mw chain
                              + core/errors + i18n subset (freezes the scaffolding auth-builder's main.py imports)
  meesell-api-routes-builder→ router.py (6 routes + cookie helpers + rate-limit decorators) + schemas.py + OpenAPI
                              (starts once auth-builder freezes the service-method signatures — near-parallel in Phase B)

PHASE C (depends on B — integration; LEAD-owned, not specialist):
  meesell-backend-coordinator → hybrid-mode CI wiring (in-process + extracted-svc); test_iam_extraction.py;
                                merge-gate review STEP 3; board MERGED flip
```

**Recommended order:** `database-builder` (Phase A) FIRST + parallel with the infra handoff →
then `services-builder` lands the shared scaffolding (`shared/*`, `core/errors`, 6-mw,
`core/auth.py` vendor) so `auth-builder`'s `main.py` imports resolve → then `auth-builder`
(heavy lift) → then `api-routes-builder` once service signatures freeze → then lead Phase C.
The auth-builder/services-builder seam: **auth-builder owns `service.py` + `core/auth.py`
vendor**; **services-builder owns repository/domain/exceptions + the rest of the vendored
scaffolding** — agreed at dispatch so they don't both touch `core/auth.py`. Iteration cap 3
per specialist.

---

## Code surfaces

The new home is `backend/services/svc-iam/`. The old `backend/app/modules/iam/` (7 files) +
`backend/app/core/auth.py` stay live until hybrid-mode CI passes ≥7 days (strangler fig).

### Backend — new service tree (`backend/services/svc-iam/`)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `app/main.py` | NEW | Standalone FastAPI; mounts iam router; registers the **full 6-mw chain** (`plan_guard_mw` runs but is NO-OP — iam participates in no plan_guard resource); `core/errors` handlers; `/health` + `/metrics`. | auth-builder |
| `app/router.py` | NEW (from `modules/iam/router.py`) | 6 public routes verbatim incl. `_set_refresh_cookie`/`_clear_refresh_cookie` helpers (Path=/api/v1/auth, Domain=.mesell.xyz) + rate-limit decorators. **NO `/internal/*`** (§0.4). | api-routes-builder |
| `app/service.py` | NEW (from `modules/iam/service.py`) | 6 public methods + §7.I direct-ORM audit path + DPDP/webhook gaps verbatim. NO cross-module import changes (iam imports no other module — §0.4). | auth-builder |
| `app/repository.py` | NEW (from `modules/iam/repository.py`) | `users`-table CRUD; bound to schema `iam`. DPDP no-op preserved. | services-builder |
| `app/domain.py` | NEW (from `modules/iam/domain.py`) | 8 frozen dataclasses (OtpRecord, RefreshAllowlistEntry, …). | services-builder |
| `app/schemas.py` | NEW (from `modules/iam/schemas.py`) | 7 Pydantic models (Send/Verify/Refresh/Me/Webhook). | api-routes-builder |
| `app/exceptions.py` | NEW (from `modules/iam/exceptions.py`) | 9-class IamError hierarchy (3-segment validation_message_id). | services-builder |
| `app/core/auth.py` | NEW (VENDORED BYTE-FOR-BYTE from `core/auth.py`) | `CurrentUser`, `get_current_user`, `issue_access_token`, `issue_refresh_token`, `refresh_allowlist_key` (dual-pepper), `validate_refresh_allowlist`, `rotate_refresh_token`, `REFRESH_ROTATE_LUA`. **Identical to the copy in every other service** — iam is the only one that also calls the issuance/rotation half from a route. | auth-builder |
| `app/core/errors.py` | NEW (vendored) | `MeesellError` base + envelope; `register_error_handlers`. | services-builder |
| `app/core/middleware/*` | NEW (vendored) | 6-mw chain (audit/auth/plan_guard/rate_limit/request_id/tenancy). | services-builder |
| `app/core/metrics.py` | NEW (vendored) | 7 §15.J singletons incl. `AUTH_TOKEN_REFRESH_FAILED` (used by `service.py:403` etc.); per-service `service="iam"` label. | services-builder |
| `app/shared/{database,config,valkey}.py` | NEW (vendored, TRIMMED) | Settings carries: `DATABASE_URL`@schema `iam`, `VALKEY_URL`, `JWT_SECRET`+`JWT_ALGORITHM`, all FE-D5 fields (`ACCESS_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_PEPPER`, `REFRESH_TOKEN_PEPPER_PREVIOUS`, `REFRESH_TOKEN_PEPPER_VERSION`), `MSG91_*`, `RAZORPAY_*` (incl. `RAZORPAY_WEBHOOK_SECRET`), `AUDIT_PII_SALT`, `CORS_*`, `APP_ENV`. **NO GEMINI/LANGFUSE/GCS** (iam has no AI/storage). `valkey.py` keeps DB 0 factory (OTP + allowlist) + the Lua `load_lua_script`/`eval_lua_script` helpers. | services-builder |
| `app/i18n/messages_en.py` | NEW (vendored subset) | ONLY iam's `validation_message_id` strings (the 9 from `exceptions.py` + 3 `auth.token.*` from `core/auth.py`). | services-builder |
| `app/shared/models/{user,audit_event}.py` | NEW (vendored) | `User` (owned, schema `iam`) + `AuditEvent` (cross-schema write target in `public` — read/write only, NOT owned). The `User.relationships` to SellerProfile/Catalog/Product/Export/ProductDraft are DROPPED (those models don't live in iam-svc) — `User` ships relationship-free in iam-svc. | database-builder + auth-builder |
| `requirements.txt` | NEW | fastapi, sqlalchemy, asyncpg, pydantic, redis, pyjwt, httpx. **NO gemini/langfuse/google-cloud-storage/celery** (iam has no AI/storage/Celery). | auth-builder |
| `Dockerfile` | NEW (placeholder) | FROM python:3.12-slim; infra lead authors the real one on the infra branch. | infra-builder |
| `alembic/` | NEW | Own chain rooted at schema `iam`; `version_table_schema="iam"`; the `users` schema-move + 6-FK DROP. | database-builder |
| `tests/test_iam_extraction.py` | NEW | Hybrid-mode integration test (in-process + extracted-svc). REAL assertions (§"Validation"). | backend-coordinator |

### Backend — monolith-side changes (during strangler window)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `backend/app/modules/iam/` (7 files) + `backend/app/core/auth.py` | KEEP-then-(auth.py STAYS) | iam module deleted after hybrid-mode CI green ≥7 days. **`core/auth.py` is NOT deleted** — it remains the vendored source-of-truth that every still-monolithic + every extracted service imports for LOCAL JWT verification. iam-svc's copy and the monolith's copy must stay byte-identical (version-pin). | backend-coordinator |
| `backend/app/main.py` | MODIFY (additive-minimal, at cutover) | Remove the `app.include_router(iam_router)` mount (`main.py:114`) ONLY at cutover. Until cutover, stays mounted (both modes run). Shared-file with MS-F — additive-minimal one-line removal, union-merge keep-both. | backend-coordinator |

### Infra (placeholders only — owned by infra lead, land on infra branch — see handoff_msG_infra.md)

| File | Tag | Description |
|---|---|---|
| `k8s/svc-iam/deployment.yaml` | NEW (placeholder) | **2 replicas minimum** (Risk #2) + HPA 4-replica burst on OTP-send spikes. |
| `k8s/svc-iam/service.yaml` | NEW (placeholder) | ClusterIP `iam-svc:8001`. |
| Traefik IngressRoute | NEW (placeholder) | `/api/v1/auth/*` + `/api/v1/auth/me` + `/api/v1/webhooks/razorpay` → `iam-svc:8001`. **Path PRESERVED — no strip/rewrite of `/api/v1/auth`** (§0.6). |
| Postgres schema `iam` + `iam_user` role | NEW (placeholder) | `CREATE SCHEMA iam; GRANT … TO iam_user;` + `GRANT INSERT ON public.audit_events TO iam_user` (cross-schema audit write — §7.I). |
| Secret Manager wiring | NEW (placeholder) | `refresh-token-pepper`, `razorpay-webhook-secret`, shared `JWT_SECRET`. |

---

## Documentation deliverables (gate conditions — land with the merge)

- **svc-iam standalone OpenAPI** — 6 endpoints, 7 schemas.
- **`BACKEND_ARCHITECTURE.md §7` amendment** — "Extracted to svc-iam (V1.5)" note. **§7 is LOCKED → FOUNDER APPROVAL REQUIRED** (§7.3); do NOT self-amend a LOCKED section.
- **`MASTER_PLAN.md §4 row G` annotation** — flip to "Sub-Plan G authored 2026-06-12 (Phase 1); execution Wave MS-4".
- **NO HTTP-shim contract doc** — iam exposes no `/internal/*` (§0.4). This is the ONE extraction with no shim-contract deliverable; state that explicitly so its absence reads as intentional.
- **`docs/runbooks/svc-iam-rollback.md`** — §3.C rollback specialized for iam (Traefik `/api/v1/auth/*` back to monolith ClusterIP; `core/extracted_clients` N/A since iam has no callers; `users` schema back to `public` + 6-FK RESTORE; the dual-pepper allowlist in shared Valkey DB 0 survives the rollback unchanged since the Valkey instance is shared).
- **Auth-secret-rotation runbook cross-ref** — confirm `docs/runbooks/auth-secret-rotation.md` §2 (dual-pepper grace window, landed PR #46) still applies to iam-svc verbatim (it does — the allowlist Valkey is shared).
- **DPDP + webhook V1-gap carry-forward note** (§0.8) — flagged to V1.5, not fixed.
- **Hybrid-mode CI config note** — which services docker-composed for iam's HTTP-mode CI. Answer: **none of iam's "callers" need to be standalone**, because iam has no callers (§0.4) — every other service validates JWTs locally and never calls iam. iam's HTTP-mode CI tests iam-svc in isolation (OTP/verify/refresh/logout/me/webhook against its own DB + shared Valkey DB 0). This is the SIMPLEST hybrid-CI surface of any extraction.

---

## Branch setup (Model C — common rule 6)

Cut from `origin/develop` (live tip at Phase-2 dispatch — re-verify per §0.1).

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/microservices-iam/integration` | `origin/develop` | Integration; merge commits only; F3 protection (PR-only, review-count 0, checks=[], no force-push/deletions, enforce_admins false) | backend lead (merge approval) + founder (integration→develop gate) |
| `feature/microservices-iam/backend` | `…/integration` | All backend specialist extraction work | backend specialists |
| `feature/microservices-iam/infra` | `…/integration` | Dockerfile, K8s, Postgres schema/role, Traefik route, Secret Manager | meesell-infra-builder |

Worktrees per dispatch under `/tmp/mesell-wt/msG-*` (e.g. `/tmp/mesell-wt/msG-auth`,
`/tmp/mesell-wt/msG-db`, `/tmp/mesell-wt/msG-routes`). NEVER `git add -A` in a symlinked
worktree — scope every stage to the exact `backend/services/svc-iam/` path (PILOT op-learning #3).

**PR flow:** group → integration is the LEAD gate (squash). integration → develop is the
**FOUNDER gate (left OPEN — lead does NOT approve)**, per D1.

```
feature/microservices-iam/backend ─(backend lead; squash)─┐
                                                          ├─► feature/microservices-iam/integration ─(FOUNDER; merge-commit)─► develop
feature/microservices-iam/infra   ─(infra lead; squash)───┘
```

**Shared-file discipline with MS-F (category, parallel):** the integration branch merges
`origin/develop` BEFORE the founder-gate PR opens; `main.py` router-removal is additive-minimal;
`k8s/`/Traefik edits are NEW manifests (svc-iam's own), not edits to category's; union-merge keep-both.

### PR templates

| Group PR | Template |
|---|---|
| `…/backend` → `…/integration` | `.github/PULL_REQUEST_TEMPLATE/backend.md` |
| `…/infra` → `…/integration` | `.github/PULL_REQUEST_TEMPLATE/infra.md` |

---

## Per-specialist SPECs (summary — full paste-able prompts in `spec_msG_backend.md`)

### meesell-auth-builder (opus) — the heavy lift

Extract `service.py` (6 methods, byte-for-byte pipeline), vendor `core/auth.py` byte-for-byte,
wire MSG91/razorpay adapters, build standalone `main.py` (6-mw chain), trimmed Settings.
**Acceptance:** `core/auth.py` diff vs monolith = ZERO (byte-identical vendor); FE-D5 cookie
helpers (Path=/api/v1/auth, Domain, attrs) byte-identical; dual-pepper read path intact;
Lua rotation verbatim; Settings carries NO GEMINI/LANGFUSE/GCS; NO `/internal/*` route;
DPDP no-op + webhook-log gaps preserved verbatim; PR template fully filled.
**Re-dispatch triggers:** `core/auth.py` drifted from monolith → re-dispatch quoting §0.5 +
A2/D7; `/internal/*` invented → §0.4 "iam is all-✗"; cookie Path changed from `/api/v1/auth` → §0.6.

### meesell-api-routes-builder (sonnet)

Move the 6 routes + 7 schemas; preserve cookie helpers + rate-limit decorators; NO `/internal/*`;
regenerate OpenAPI (6 endpoints). **Acceptance:** 6 routes MOUNTED (count APIRoute objects, not
schemas — row-26 lesson); handlers call service methods only (no inlined logic); rate-limit
decorators preserved (`otp_send` 3/h, `otp_verify` 10/h, `auth_refresh` 60/h); OpenAPI 6 endpoints
+ 7 schemas. **Re-dispatch:** business logic inlined → §14.B equivalent; route count ≠ 6 → §0.3;
shape invented → re-cite router.py source.

### meesell-services-builder (opus)

Extract repository/domain/exceptions + vendor the trimmed `shared/*`, `core/errors`, 6-mw chain,
`core/metrics`, `i18n` subset. **Acceptance:** repository bound to schema `iam`; §7.I direct-ORM
audit path preserved (in-request SAVEPOINT); DPDP no-op + webhook-log gaps verbatim; trimmed
Settings; 6-mw chain vendored (plan_guard NO-OP). **Re-dispatch:** §7.I audit path altered → re-cite
service.py:154-232; gap "fixed" → §0.8 "extraction preserves behavior".

### meesell-database-builder (sonnet) — Phase A, dispatch FIRST

Author the `public.users` → schema `iam` move migration; `version_table_schema="iam"`; DROP the
6 cross-schema FKs (§0.7) — cross-checked live via `pg_constraint` at execution; Risk #5 integrity
pre-scan BEFORE any drop (every `<table>.user_id` resolves to a real `users` row); tested downgrade
(schema back to `public` + 6-FK RESTORE). **Acceptance:** upgrade+downgrade round-trip clean;
`version_table_schema="iam"` set; dev applied BEFORE staging (head-divergence dev↔staging = P0
escalate); pre-scan output in migration log; exactly the residual cross-schema FKs dropped (neither
more nor less). **Re-dispatch:** head divergence dev↔staging → P0 STOP escalate; FK over/under-drop
→ re-cite §0.7 + the live `pg_constraint` query.

---

## Validation (merge-gate, lead-owned) — Wave-6 lessons are LAW

- **Full backend suite `def test_` count MONOTONIC** vs live baseline (§0.9) — quote live count at PR; do NOT hardcode "823".
- **iam's own tests green in BOTH the monolith (pre-flip) AND the extracted svc-iam** — the validation floor (common rule 9).
- **Mounted routes verified in svc-iam's `main.py`** — exactly 6 `APIRoute` objects (row-26 lesson); NO `/internal/*` route present.
- **`core/auth.py` byte-identical** to the monolith copy (`diff` clean) — the A2/D7 vendoring invariant.
- **FE-D5 contract intact:** cookie Path=`/api/v1/auth`, dual-pepper allowlist key derivation, Lua rotation verbatim — assert via a real round-trip test (issue → refresh → rotate → logout → DEL), NOT a tautology.
- **`ruff` clean** on `backend/services/svc-iam/`.
- **import-linter:** svc-iam tree introduces NO `domain→adapters.gemini` edge (Contract 2 — N/A, iam has no gemini); the `check_scope_to_user.py` Contract 8 — N/A for `users` (the principal IS the row, per `repository.py:11-16`); confirm no NEW violations.
- **NO tautological tests (the pricing lesson):** the hybrid-mode integration test asserts REAL behavior — e.g. `POST /otp/verify` sets a `refresh_token` cookie with `Path=/api/v1/auth`; `POST /refresh` rotates the Valkey key (old key GONE, new key PRESENT under `cache:refresh:v{N}:`); `POST /logout` DELs the key; a request to ANOTHER (still-monolithic) service with the iam-issued access JWT validates LOCALLY (proving G1 — no callback to iam). `assert True`-class echoes are a reject-class offense.
- **Report TRUE branch tips** (common rule 3) at PR time — actual SHAs, not assumed.

---

## Acceptance gate

Sub-Plan G execution (Wave MS-4) is DONE when:

- [ ] `feature/microservices-iam/backend` PR merged to `…/integration` (backend lead gate)
- [ ] `feature/microservices-iam/infra` PR merged to `…/integration` (infra lead gate)
- [ ] Hybrid-mode CI green in BOTH modes for ≥7 days (§3.A)
- [ ] `cd backend && pytest services/svc-iam/tests/test_iam_extraction.py` green
- [ ] **Risk #2 verified:** every OTHER service (already extracted A–F + still-monolithic catalog) validates JWTs LOCALLY with zero callback to iam-svc — confirmed during the 7-day window
- [ ] **FE-D5 verified:** the live frontend's refresh flow works against iam-svc through Traefik with the cookie `Path=/api/v1/auth` preserved (no Set-Cookie Path drift)
- [ ] 6 mounted routes + 7 schemas in svc-iam OpenAPI; NO `/internal/*`
- [ ] Documentation deliverables landed (OpenAPI, §7 amendment w/ founder approval, rollback runbook, DPDP/webhook carry-forward note)
- [ ] V1_FEATURE_SPEC §F1 (Auth) acceptance criteria still met against the extracted service
- [ ] CI gates 1/2/3 green; gates 4/5 advisory
- [ ] `feature_board_backend.md` row reflects MERGED
- [ ] Founder approval on `…/integration` → `develop` PR

---

## Risk register (iam-specific subset of MASTER_PLAN §6)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | iam extraction breaks every authenticated route across all services (MASTER_PLAN Risk #2) | Medium | **Catastrophic** | JWT validation is LOCAL via vendored `core/auth.py` + shared `JWT_SECRET` (G1/A2/D7) — NO service calls iam to validate a token. iam downtime affects only login/refresh/logout; valid access tokens keep working for their TTL. **2-replica minimum + HPA 4-replica burst** (infra I2). Verify zero callbacks during the 7 prior extractions before extracting iam. |
| R2 | Traefik path-strip/rewrite breaks the FE-D5 cookie `Path=/api/v1/auth` scoping → every live session silently fails to send the refresh cookie | Medium | **High** | Traefik route preserves `/api/v1/auth/*` EXACTLY — NO strip/rewrite (§0.6, infra I4). Acceptance gate asserts a live refresh round-trip through Traefik. The cookie helpers + `core/auth.py` allowlist derivation ship byte-for-byte. |
| R3 | Cross-schema FK over/under-drop causes silent data-integrity loss (MASTER_PLAN Risk #5) | Low | High | DROP exactly the 6 §0.7 FKs, cross-checked live via `pg_constraint` at execution (waves MS-2/MS-3 may have dropped some). Risk #5 integrity pre-scan BEFORE any drop. `assert_owned`/`scope_to_user` (CI Contract 8) is the replacement defense. Weekly forensic orphan-scan post-extraction. |
| R4 | The dual-pepper allowlist (R5/PR #66) state is lost when iam moves pods | Low | High | The refresh allowlist lives in **shared Valkey DB 0** (`cache:refresh:v{N}:{hmac}`) — NOT in the iam pod. The Valkey instance is shared across services; moving iam-svc does not touch DB 0. The dual-pepper read (`validate_refresh_allowlist`) + Lua rotation ship byte-for-byte. No backfill needed (unlike export's Celery keyspace). |
| R5 | `core/auth.py` drifts between the iam-svc copy and the other services' copies → JWTs issued by iam-svc fail to validate elsewhere (or vice-versa) | Low | **Catastrophic** | `core/auth.py` is vendored byte-for-byte from ONE source tree + version-pinned. Merge-gate asserts `diff` clean vs monolith. The monolith's `core/auth.py` is NOT deleted at iam cutover (it stays the source-of-truth every service imports). A drift in HS256 secret OR claim shape `{sub, exp, plan}` is the failure mode — the integration test asserts an iam-issued JWT validates in a non-iam service. |

---

## Rollback (per MASTER_PLAN §3.C, specialized for iam)

1. Traefik IngressRoute for `/api/v1/auth/*` + `/api/v1/webhooks/razorpay` → back to monolith ClusterIP.
2. `core/extracted_clients/` — **N/A** (iam has no callers; no shim to revert).
3. `users` schema → back to `public` (`alembic downgrade` the schema-move) + RESTORE the 6 cross-schema FKs (§0.7).
4. `kubectl delete deployment iam-svc`.
5. The dual-pepper allowlist in shared Valkey DB 0 is UNTOUCHED by the rollback (shared instance) — live sessions survive.
6. Re-run hybrid-mode CI in pure in-process mode; document root cause in this sub-plan's "Rollback Log".

Rollback allowed any time BEFORE Sub-Plan G is declared complete (7-day green window).
**Catastrophic post-completion rollback** copies `iam.users` data back to `public.users` + restores the 6 FKs.

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-12 | mesell-ms-iam-session-1 (meesell-backend-coordinator) | Initial PHASE-1 sub-plan. MS-PAR-1 Wave MS-4, parallel with MS-F. All contracts cited file:line from as-built develop `6d6ee51`. 6 mounted iam routes verified in main.py:114 + router.py. iam all-✗ → NO `/internal/*` shim. 6 cross-schema FKs to `users.id` identified for DROP (§0.7). A2/D7 (local JWT) + FE-D5 (cookie Path=/api/v1/auth, dual-pepper allowlist) encoded as reject-class invariants. Execution GATED on Wave MS-3 complete. |
| v1.1 | 2026-06-12 | mesell-ms-iam-session-1 (meesell-backend-coordinator) | **Re-grounding + sibling reconciliation (post-rebase).** Branch rebased from local develop `6d6ee51` onto origin/develop `aa7513e` (true tip). `git diff 6d6ee51 aa7513e -- modules/iam/ core/auth.py` = EMPTY → all file:line citations hold verbatim. 3 changed core files inspected, ALL inert for iam: `audit_mw._is_autosave` (catalog-path-only), `tenancy._GLOBAL_TABLES` (doc-sentinel, no iam table), `main.py` catalog-flag guard at :123+ (below iam mount :114, unchanged). §0.1 + §0 preamble re-grounded; MASTER_PLAN cited as v1.3 §3.A.1-aware. §0.7 annotated with sibling FK-ownership: FK #2 `seller_profile.user_id` dropped by **customer at MS-3** (SUB_PLAN_0E §0.6), FKs #3/#4/#6 still iam's (catalog MS-5); 0C/0D add NO new `users.id` FK (set stays 6). Shared-file discipline aligned with SUB_PLAN_0F (main.py / Traefik / k8s + D7 parallel-safety). No contract collision found → no escalation. No semantic change to deliverables, FK count, or invariants. |

---

**END OF SUB-PLAN G — PHASE 1 (sub-plan authored). Execution Phase 2 GATED on Wave MS-3 complete.**

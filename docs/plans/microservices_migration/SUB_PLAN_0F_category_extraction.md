# SUB-PLAN F — `category` Service Extraction

**STATUS: AUTHORED — EXECUTION GATED ON MS-4 WAVE OPEN.** Authored under
session `mesell-ms-category-session-1` (PHASE 1, hybrid step 1, docs-only —
2026-06-12). This is the sixth extraction sub-plan of the Microservices
Migration MASTER_PLAN (LOCKED 2026-06-10, v1.3). It implements MASTER_PLAN §4
row **F** (`category`, complexity **L**) under the **MS-PAR-1 parallel wave
program** (dispatch doc `docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md`).

> **Execution gate — MS-4 WAVE.** Per MS-PAR-1 (founder ruling "prepare a
> parallel plan for micro service", 2026-06-12), the LOCKED serial A→H order
> is upgraded to **pilot alone → parallel pairs → riskiest last**. `category`
> executes in **MS-4**, **in parallel with MS-G (`iam`)**, and unblocks only
> when **MS-3 (`pricing` + `customer`) are BOTH founder-gate-merged**. The MS-A
> recipe (the pilot extraction toolchain) must exist before any MS-2+ service
> begins. **Sub-plan AUTHORING (this document) is unblocked NOW; EXECUTION is
> MS-4-gated.**
>
> **MASTER_PLAN naming reconciliation (SOURCE WINS):** MASTER_PLAN §4 row F
> (line 306) names this file `SUB_PLAN_06_category_extraction.md` and lists the
> OLD serial dependency chain "A, B, C, D, E complete". The **MS-PAR-1 dispatch
> doc supersedes both**: the canonical filename for the parallel program is
> `SUB_PLAN_0F_category_extraction.md` (this file), and the dependency is
> "MS-3 complete (pricing + customer), parallel with iam" — NOT the full A–E
> serial chain. This is a plan-prose-vs-dispatch reconciliation recorded here
> per the Wave-6 SOURCE-WINS discipline; the §4 row F annotation should be
> updated to point at this file when the founder next touches the master plan.
>
> **Execution posture — PLANNING ONLY.** This document is the executable
> specification a coding session (dispatched once MS-4 opens) will follow. NO
> extraction code is written by the authoring session. The two ai_ops /
> middleware decisions are already **LOCKED** via founder rulings D6 / D7
> (2026-06-10) — see §F1 / §F2.

> Authoritative inputs read for this sub-plan (file:line citations from SOURCE
> per Wave-6 law — never plan prose for enums/contracts):
> - `docs/plans/microservices_migration/MASTER_PLAN.md` (LOCKED v1.3 — §1.A row category line 27, §2.D call matrix lines 62/64/68, §3.C rollback lines 281-291, §3.B/§4 row F line 306, §5.A/B/C/D/E/F, §6 risks, D6/A1 line 221, D7/A2 line 328)
> - `docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md` (THE SHAPE TEMPLATE — canonical section structure; A1/A2 supersession banner)
> - `docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md` (MS-PAR-1 wave structure, common rules 1-9, the Session MS-F prompt block)
> - **MS-A FROZEN shim contract** — the 6-endpoint `/internal/*` contract authored by the pilot (Session MS-A). The two shims `category` implements are cited at §F4 below. *(Authoring note: the MS-A spec files `spec_msA_backend.md` + `handoff_msA_infra.md` are NOT present in this worktree branch nor on `develop` — they are untracked artifacts on the master tree. The two frozen category shim shapes are reproduced here verbatim from the Session MS-F dispatch prompt, which quotes them; this sub-plan IMPLEMENTS those frozen shapes and NEVER renames or invents them. See §F4 + Open Questions.)*
> - As-built source (file:line): `backend/app/modules/category/` (8 files — router.py, service.py, picker.py, repository.py, schemas.py, domain.py, exceptions.py, __init__.py), `backend/app/ai_ops/{client,budget_cap,cost_tracker}.py`, `backend/app/i18n/schema_contract.py`, `backend/app/main.py`

---

## As-built inventory (file:line — SOURCE, not plan prose)

### Mounted routes (verified in `backend/app/main.py`, NOT schema existence)

`backend/app/main.py:41` imports `category_router`; `:120`
`app.include_router(category_router)` mounts it. The router
(`backend/app/modules/category/router.py:77`) carries `prefix="/api/v1"`,
`tags=["category"]`. **5 mounted public routes** (matches MASTER_PLAN §1.A row
category line 27 "5"; §17 endpoint inventory category=5):

| # | Method + path | Handler (router.py) | Service call | Notes |
|---|---|---|---|---|
| 1 | `GET /api/v1/categories/suggest?q=` | `suggest_categories` `:89` | `service.suggest_categories(user_id, q, db)` `:123` | Smart Picker; `@rate_limit(scope="smart_picker", limit=100, window=3600)` `:88`; `FEATURE_SMART_PICKER_ENABLED` 404 guard `:117`; **the ONLY AI-consuming route in category** |
| 2 | `GET /api/v1/categories/browse` | `browse_categories` `:137` | `service.browse_categories(q, super_id, limit, offset, db)` `:168` | pg_trgm; per-IP floor only; no AI |
| 3 | `GET /api/v1/categories` | `get_category_tree` `:182` | `service.get_category_tree(db)` `:199` | full 3,772-leaf tree; GLOBAL cache + ETag/304 `:200-213` |
| 4 | `GET /api/v1/categories/{id}/schema` | `get_category_schema` `:224` | `service.fetch_schema(id, db)` `:249` | §5A.B envelope; GLOBAL cache per id + ETag/304; **frozen shim #1 source** |
| 5 | `GET /api/v1/categories/{id}/field-enum/{name}` | `get_field_enum` `:273` | `service.get_field_enum(id, name, db)` `:295` | single-flight; 291 Brand-pattern enums; **frozen shim #2 source** |

All 5 are read-only → **NO audit rows** (`router.py:19-21`). All 5 require
`Depends(get_current_user)` — routes never decode JWT.

### Public service surface (`backend/app/modules/category/service.py`)

**8 PUBLIC async methods** (`service.py:1-16` docstring; `__all__` `:615-624`):

| Method | Signature (service.py) | Consumer |
|---|---|---|
| `suggest_categories` | `(user_id, q, db) -> dict` `:192` | route 1 |
| `browse_categories` | `(q, super_id, limit, offset, db) -> dict` `:352` | route 2 |
| `get_category_tree` | `(db) -> dict` `:407` | route 3 |
| `fetch_schema` | `(category_id, db) -> dict` `:467` | route 4 **+ frozen shim #1 + cross-module (catalog autofill, export, pricing? — see below)** |
| `get_field_enum` | `(category_id, field_name, db) -> dict` `:491` | route 5 **+ frozen shim #2 + cross-module (export)** |
| `get_commission` | `(category_id, db) -> Decimal` `:548` | **cross-module: pricing** (§2.D line 64) |
| `list_super_categories` | `(db) -> list[SuperCategoryInfo]` `:570` | **cross-module: customer** (§8.C) |
| `assert_category_exists` | `(category_id, db) -> None` `:604` | **cross-module: catalog** (§2.D line 62) |

### Cross-module edges — category as CALLEE (verified by grep)

`category` is called by **3 modules** (grep `from app.modules.category import`
across `backend/app/modules/`, excluding category's own subtree):

| Caller | Import site | Methods consumed |
|---|---|---|
| `catalog` | `catalog/service.py:98` `from app.modules.category import service as category_service` | `assert_category_exists` (404 gate) + `fetch_schema` (autofill enum resolver) per §2.D line 62 |
| `export` | `export/service.py:58` `from app.modules.category import service as category_service` | `fetch_schema` + `get_field_enum` per §2.D line 68 |
| `pricing` | `pricing/service.py:66` `from app.modules.category import service as category_service` | `get_commission` per §2.D line 64 |

**`customer` → `category`:** MASTER_PLAN §8.C documents
`list_super_categories` as a customer-consumed surface; the as-built grep did
NOT surface a `customer/service.py` import of category at the current develop
tip (customer may resolve super-categories another way in V1, or the call is
latent). **Recorded as a CALLEE surface to expose as a `/internal/*` shim
regardless** (see §F4 + Open Questions) — if customer-svc (MS-E, already
extracted by MS-4) needs it, the shim must exist.

### Cross-module edges — category as CALLER

**ZERO.** Grep `from app.modules` inside
`category/{service,picker,repository}.py` returns NOTHING outside category's
own subtree. `category` calls NO other domain module — it is a **pure callee /
leaf-on-the-inbound-graph** for domain calls. It depends only on:
- `app.ai_ops.client` + `app.ai_ops.budget_cap` (the AI seam — `service.py:76-78`)
- `app.core.cache.get_or_set` (`service.py:79`)
- `app.core.plan_guard.enforce_plan_limit` (`service.py:80`)
- `app.shared.*` (config, database, models)
- `app.modules.category.picker` (in-module AI ranking — `service.py:81`)

**Consequence:** `category` implements `/internal/*` shims for its callers but
authors **ZERO outbound HTTP-shim clients** (it consumes no extracted service).
This is the inverse of the export pilot (which had 4 outbound shims, 0 inbound).
Because MS-A (export) is already merged by MS-4, export-svc's outbound
`category_client` shim is already pointing at the monolith ClusterIP; when
category-svc cuts over, the Traefik route flips export-svc's `category_client`
target to category-svc — **no code change in export-svc**, only a route flip
(§16.G call-site preservation).

### DB tables owned (the 3,772-leaf tree + schema contract)

`repository.py:14` docstring + `:42-44` ORM imports. `category` owns READ
access to **4 GLOBAL tables** (MASTER_PLAN §1.A line 27 / §3.A line 187):

| Table | ORM | Where it lives today | Runtime read by category? |
|---|---|---|---|
| `categories` | `app.shared.models.category.Category` (`repository.py:42`) | baseline migration `935e55b4852c` (13-table baseline); 3,772 leaf rows | YES — tree, browse, suggest, commission, exists |
| `templates` | `app.shared.models.template.Template` (`repository.py:44`) | baseline; holds `schema_jsonb` envelopes (the §5A.B compiled wizard schemas) | YES — `fetch_schema` |
| `field_enum_values` | `app.shared.models.field_enum_value.FieldEnumValue` (`repository.py:43`) | baseline; 291 Brand-pattern enum blobs | YES — `get_field_enum` |
| `field_aliases` | (referenced `repository.py:14` docstring; NOT imported as ORM in repository) | baseline (`field_aliases` seed) | **NO at runtime** — see correction below |

> **MASTER_PLAN correction carried from MS-A (SOURCE WINS):** MASTER_PLAN §2.D
> line 68 lists `fetch_xlsx_aliases` among export's category calls, implying a
> runtime `field_aliases` read. **MS-A corrected this: export NEVER calls
> `fetch_xlsx_aliases` at runtime — the canonical→raw alias reversal is a
> SEED-TIME concern (the XLSX template is built once from aliases, not
> re-resolved per export).** Verified against as-built: `category/service.py`
> exposes NO `fetch_xlsx_aliases` method (`__all__` `:615-624` has 8 methods,
> none is `fetch_xlsx_aliases`); `repository.py` imports only Category /
> FieldEnumValue / Template ORM (`:42-44`), **NOT** a FieldAlias ORM. So the
> two frozen `/internal/*` shims category implements are `fetch_schema` +
> `get_field_enum` ONLY — **NOT** a third `fetch_xlsx_aliases` shim. This
> sub-plan carries the MS-A correction forward (see §F4).

**What migrates vs what stays:** all 4 GLOBAL tables move to the `category`
Postgres schema (read-only after seed). The `field_aliases` table moves with
them **but is consumed only by the seed pipeline** (`scripts/build_template_schemas.py`
at repo root — see §F6), not by category-svc runtime; it travels for locality,
not because category-svc reads it at runtime.

### Module-private internals (stay inside the service, no contract surface)

- `repository.py` — 7 module-PRIVATE methods (`fetch_category_tree`,
  `search_via_trigram`, `fetch_schema_uncached`, `fetch_field_enum_uncached`,
  `assert_category_exists_uncached`, `get_commission_uncached`,
  `list_super_id_distinct`). NO `scope_to_user` anywhere — categories are
  GLOBAL (§9.D structural exception; §19 linter allowlist entry).
- `picker.py` — pure AI-ranking helpers (`compress_tree` `:141`,
  `calibrate_confidence` `:270`, `select_top_k` `:305`; `_trigrams`,
  `_overlap`, `_row_field` private). **Imports NO ai_ops** (`picker.py:69-72`
  imports only stdlib + dataclasses) — the `call_gemini` invocation lives in
  `service._build_suggest_payload` (`service.py:262`), and picker only shapes
  the prompt input + post-processes the response. This matters for vendoring
  (§F3): picker travels as pure code; only service.py touches ai_ops.
- `domain.py` — 2 frozen dataclasses (`CategoryRow` `:20`, `SuperCategoryInfo`
  `:39`); cross-module exchange currency per §16.D.
- `exceptions.py` — `CategoryError` base + 4 subclasses (`CategoryNotFoundError`
  `:39`, `FieldEnumNotFoundError` `:54`, `SuggestQueryInvalidError` `:72`,
  `BrowseQueryInvalidError` `:92`).
- `schemas.py` — 5 PRIVATE Pydantic response models (`SuggestResponse`,
  `BrowseResponse`, `CategoryTreeResponse`, `SchemaResponse`,
  `FieldEnumResponse`). PRIVATE wire-shape per §16.C.

---

## Decisions

> **F1 / F2 carry the LOCKED D6 / D7 rulings verbatim.** Unlike the export
> pilot (where A1/A2 were authored as recommendations then locked), this
> sub-plan is authored AFTER the D6/D7 locks — so F1/F2 are stated as LOCKED
> from the start, with the same content the export A1/A2 supersession banner
> carries.

### F1 — `ai_ops/` placement — VENDORED per AI-consuming service (LOCKED, founder ruling D6 / A1, 2026-06-10)

**Relevance to THIS sub-plan: DIRECT and HIGH.** `category` is the FIRST
extraction (in the MS-PAR-1 order) that actually CARRIES an ai_ops dependency
(`category/service.py:76-78` imports `ai_client`, `BudgetExceededError`,
`AICallContext`). The export pilot (MS-A) was deterministic — zero AI — and
explicitly deferred this decision's first real test to Sub-Plan F. **This is
that test.**

**LOCKED ruling (MASTER_PLAN line 221, D6/A1):** `ai_ops/` is a **vendored
Python-package copy per AI-consuming service (category / catalog / image) at
V1.5**; promoted to a dedicated `ai-ops-svc` at V2. **There is NO ai-ops-svc
until V2.** category-svc carries its own vendored copy of the ai_ops code it
uses. **The ₹500 daily BUDGET BRAKE stays SHARED via Valkey DB 0 / the audit-DB
counter across all services regardless of code placement** — so the spend cap
remains GLOBAL.

The full vendoring plan + shared-budget-brake wiring is §F3.

### F2 — Shared `core/middleware/` placement — VENDORED, LOCAL JWT (LOCKED, founder ruling D7 / A2, 2026-06-10)

**Relevance: DIRECT.** category-svc needs `auth_mw` (`get_current_user` on all
5 routes), `rate_limit_mw` (`@rate_limit(scope="smart_picker", limit=100,
window=3600)` on `/suggest`, `router.py:88`), `tenancy_mw`, `request_id_mw`,
`audit_mw` (NO-OP for category — all 5 routes are read-only, zero audit rows),
and `plan_guard_mw`. **plan_guard IS active for category** — `smart_picker_hourly`
(100/h/user) is enforced INSIDE `service.suggest_categories`
(`service.py:226 enforce_plan_limit(...)`) per §4.E, NOT in the middleware
chain decorator — but the `plan_guard_mw` middleware still ships in the chain.

**LOCKED ruling (MASTER_PLAN line 328, D7/A2):** the **6-middleware chain
(CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw →
audit_mw) is VENDORED per service**; **JWT VERIFICATION runs LOCALLY in every
service** via the vendored `core/auth.py` + shared `JWT_SECRET` from Secret
Manager. `iam-svc` (MS-G, extracting in parallel) owns OTP/login/refresh ONLY
— it is NOT consulted per-request for token validation. **Gateway-JWT
validation is REJECTED.** category-svc validates its own JWTs.

> **MS-4 parallel note (category ‖ iam):** MS-F and MS-G extract in the SAME
> wave. category-svc must NOT depend on iam-svc being up to validate tokens —
> D7's local-JWT rule is precisely what makes the parallel extraction safe.
> category-svc gets `JWT_SECRET` from Secret Manager (same secret iam-svc signs
> with) and validates locally. The two services share NO request-path coupling.

### F3 — `ai_ops/` vendoring plan + SHARED budget-brake wiring (the load-bearing decision)

This is the heart of Sub-Plan F. It operationalizes F1 against the as-built
budget-brake code.

#### F3.a — What category-svc vendors

category-svc ships a **trimmed vendored copy of `ai_ops/`** containing ONLY the
code path the smart-picker workload exercises:

| ai_ops file | Vendored into category-svc? | Why |
|---|---|---|
| `client.py` | YES | sole AI import surface; `service.py:76` `from app.ai_ops import client as ai_client`; `:262 call_gemini(ctx, "smart_picker.v1", ...)` |
| `budget_cap.py` | YES | `service.py:77` imports `BudgetExceededError`; the brake's reserve/release Lua runs in-process |
| `cost_tracker.py` | YES | `client.py:62` imports it; writes committed cost + audit_events |
| `guardrail.py` | YES | `client.py:62` — Layer 1 prefix + Layer 2 enum re-validation + retries (the smart_picker hallucination guard) |
| `prompt_registry.py` | YES | `client.py:62` — `resolve()` + `render()` for `smart_picker.v1` |
| `prompts/smart_picker_v1.py` | YES (this ONE prompt module) | the only workload category runs; `prompts/autofill_v1.py` + `prompts/watermark_v1.py` are NOT vendored (catalog/image carry those) |
| `eval.py` | OPTIONAL (vendor for CI golden-set parity) | the Smart Picker top-5 recall ≥80% golden set lives here; vendor it so category-svc CI can run its own eval gate |

`metrics.py` (the 7 Prometheus singletons incl. `AI_OPS_BUDGET_ALARM`,
`AI_OPS_COST_INR`) is vendored per §5.F with the per-service `service="category"`
label.

#### F3.b — The SHARED budget brake — exact Valkey keys + DB table (cited file:line)

The budget brake state is **NOT vendored** — it is SHARED infrastructure that
all AI-consuming services point at. Cited from source:

**Valkey DB 0** (via `get_valkey_otp()` — `budget_cap.py:74`, `:223`, `:299`,
`:334`; `cost_tracker.py:56`, `:186`, `:225`, `:233`):

| Key family | Constant (file:line) | Purpose |
|---|---|---|
| `ai:cost:daily:{YYYY-MM-DD}` | `cost_tracker.py:92 _DAILY_KEY_FMT` | **committed** daily spend (the ₹500 cap numerator) |
| `ai:cost:pending:{YYYY-MM-DD}` | `budget_cap.py:124 _PENDING_KEY_FMT` | **reserved-but-not-committed** (race-safe headroom) |
| `ai:budget:reservation:{reservation_id}` | `budget_cap.py:125 _RESERVATION_KEY_FMT` | per-call 5-min-TTL reservation (`budget_cap.py:130 _RESERVATION_TTL_SECONDS=300`) |
| `ai:cost:user:{user_id}:hourly:{YYYY-MM-DD-HH}` | `cost_tracker.py:93 _USER_HOURLY_KEY_FMT` | per-user hourly cost accumulator (diagnostic) |

The cap check is **atomic** via two Lua scripts (`budget_cap.py:136 _RESERVE_LUA`,
`:153 _RELEASE_LUA`) executed inside Valkey's single-threaded loop — concurrent
`check_and_reserve` from DIFFERENT services serialise here. The cap value is
`settings.AI_DAILY_BUDGET_INR` (`budget_cap.py:207`); the day boundary is
Asia/Kolkata (`_today_kolkata_str()` — `cost_tracker.py:104`); counter TTL
`_DAILY_KEY_TTL_SECONDS=90_000` (`cost_tracker.py:97`, ~25h survives midnight).

**Postgres `audit_events` table** (the committed-cost ledger — direct ORM
write): `cost_tracker.py:55 from app.shared.models.audit_event import AuditEvent`;
the write is a **documented exception to the request-close-hook pattern**
(`cost_tracker.py:250` docstring "Direct ORM write to `audit_events`. Drops on
failure with WARNING."). This is GLOBAL shared state — every AI call's true cost
lands here.

#### F3.c — How the vendored copy points at SHARED state

The vendored `ai_ops/budget_cap.py` + `cost_tracker.py` in category-svc are
**byte-for-byte the monolith versions** (§16.G discipline applies to vendored
infra too). They reach shared state via:

1. **Valkey:** category-svc's vendored `shared/valkey.py` `get_valkey_otp()`
   factory points at the **SAME Valkey instance, SAME DB 0** as the monolith
   (and every other AI service). MASTER_PLAN §2.E (line 209): "All 4 DBs
   continue to be shared." **BUT** §2.E also locks **per-service key
   namespacing** (`{service_name}:` prefix). **CRITICAL CARVE-OUT:** the budget
   brake keys (`ai:cost:*`, `ai:budget:*`) MUST **NOT** be prefixed with
   `category:` — if they were, each service would have its OWN ₹500 counter and
   the GLOBAL cap would break into N independent caps. **The `ai:*` budget
   keyspace is the documented EXCEPTION to the `{service_name}:` prefixing
   rule** — it stays un-prefixed/global precisely because the cap is global.
   (category's OWN cache keys — `smart_picker:{hash}`, `category_tree`,
   `schema:{id}`, `field_enum:{id}:{field}` — DO get the `category:` prefix per
   §2.E; only the shared budget keyspace is exempt.) **This carve-out is a
   merge-gate acceptance item (§F-acceptance) and a contract test.**

2. **Audit DB:** category-svc's vendored `cost_tracker.py` writes
   `audit_events` rows. category-svc's own Postgres schema is `category`, but
   `audit_events` lives in the SHARED ledger (MASTER_PLAN §5.B export
   precedent: cross-schema INSERT to `public.audit_events` via a role grant).
   **category-svc's Postgres role needs `GRANT INSERT ON public.audit_events TO
   category_user`** (infra handoff §F-infra). The AI cost ledger stays unified.

#### F3.d — Drift control (3 vendored copies of ai_ops)

D6 acknowledges the risk: category / catalog / image each carry a copy of
ai_ops; copies drift if unpinned. Mitigation (per export A1 con-column +
MASTER_PLAN §5.F):
- ai_ops is vendored **from one source tree** (`backend/app/ai_ops/` at the
  extraction commit) with a recorded source-commit SHA in each service's
  vendoring manifest.
- Per-service AI cost attribution uses the Prometheus `service="category"`
  label (§5.F), NOT a dedicated service boundary.
- A **contract test** (`test_ai_ops_vendoring_parity`) asserts the vendored
  `budget_cap.py` Lua scripts + key formats are byte-identical to the monolith
  source (catches drift in the load-bearing brake code).
- V2 collapses all 3 copies into `ai-ops-svc` (D6) — drift becomes moot.

---

## F4 — The two FROZEN `/internal/*` shims category implements

`category` is a CALLEE. MS-A (the export pilot) **froze** the `/internal/*`
contract shapes its callees must expose. category implements **exactly TWO**
(the MS-A correction dropped `fetch_xlsx_aliases` — runtime never calls it,
§ as-built inventory above). **These shapes are FROZEN by MS-A — this sub-plan
IMPLEMENTS them; it NEVER renames or re-shapes them.**

### Shim #1 — schema fetch

```
GET  /internal/categories/{id}/schema
  ← backs:  category/service.py:467  fetch_schema(category_id, db) -> dict
  → returns: the §5A.B SchemaEnvelope (7 keys) verbatim — see §F5 zero-drift
  callers (post-extraction, over HTTP): export-svc, catalog-svc
  (today, in-process): export/service.py:58, catalog/service.py:98
```

### Shim #2 — field-enum lookup

```
GET  /internal/categories/{id}/field-enum/{field}
  ← backs:  category/service.py:491  get_field_enum(category_id, field_name, db) -> dict
  → returns: {enum_entries:[{canonical, meesho, labels}], total, truncated}
  callers (post-extraction, over HTTP): export-svc
  (today, in-process): export/service.py:58
```

**§16.G call-site preservation:** export-svc's already-built `category_client`
shim (authored in MS-A) calls these two `/internal/*` paths. When category-svc
cuts over, the Traefik route for `/internal/categories/*` flips from
monolith-svc to category-svc — export-svc's `await category_service.fetch_schema(...)`
call site stays byte-for-byte identical (the shim re-exports the same symbol).
**category-svc authors the SERVER side of these two shims; it does NOT author
client shims (it has zero outbound calls).**

### Latent shim — super-categories (defensive)

`list_super_categories` (`service.py:570`, §8.C customer surface) has no
verified as-built caller import at develop tip, but MS-E (customer-svc) is
already extracted by MS-4. **If** customer-svc consumes super-categories at
runtime, category-svc must expose a third internal shim
`GET /internal/categories/super-categories` ← `list_super_categories(db)`.
**Open Question (§ Open Questions): confirm with the master session whether the
MS-A frozen contract includes a customer→category super-category shim, or
whether customer resolves super-categories from its own seed copy.** Author the
shim defensively unless the master session confirms it is unneeded.

> **`assert_category_exists` + `get_commission` shims:** catalog (MS-H, NOT yet
> extracted at MS-4) calls `assert_category_exists`; pricing (MS-D, extracted at
> MS-3, BEFORE category) calls `get_commission`. **pricing-svc is already a pod
> by the time category extracts** — so category-svc MUST expose
> `GET /internal/categories/{id}/commission` ← `get_commission(category_id, db)`
> for pricing-svc's already-built `category_client`. **This is a THIRD frozen
> shim category implements** if MS-D's sub-plan authored a `get_commission`
> `/internal/*` client. **Open Question: verify against MS-D's (SUB_PLAN_0D)
> frozen contract whether pricing-svc calls category over HTTP for commission,
> and implement the matching server shim.** catalog's `assert_category_exists`
> shim can wait — catalog is MS-5 (after category), so at category's cutover
> catalog is still in-process and reaches `assert_category_exists` via the
> in-process path; the `/internal/categories/{id}/exists` shim is added when
> catalog extracts (MS-5) OR pre-emptively here for completeness.

---

## F5 — PRIMITIVE_VALUES zero-drift contract (LOAD-BEARING for the live frontend)

`backend/app/i18n/schema_contract.py` is the presentation-contract lock. The
live Angular frontend renders wizard fields off the `primitive` value of each
field in the `schema_jsonb` envelope. **Zero drift is allowed.** Cited from
source:

- `schema_contract.py:175 PRIMITIVE_VALUES: Final[frozenset[str]]` — the **11**
  locked primitives (`text_short`, `text_long`, `number`, `number_with_unit`,
  `currency`, `dropdown_small`, `dropdown_medium`, `dropdown_large`,
  `dropdown_api_search`, `image_upload`, `address_group`).
- `:147 ENVELOPE_KEYS` — the **7** top-level keys (the dispatch prompt said "6";
  `schema_contract.py:17-18` CORRECTS this to 7 — the "6-key wording is a
  summary; the spec example shows 7"). **SOURCE WINS: 7 envelope keys.**
- `:108 FIELD_SHAPE_KEYS` — the **9** per-field keys.
- `:163 DATA_TYPE_VALUES` (8), `:190 COMPLIANCE_SHAPE_VALUES` (2),
  `:198 ENUM_RESOLVER_VALUES` (3 incl. `None`).

### What category-svc SERVES vs what STAYS in monolith/shared

**Critical distinction (from `schema_contract.py:8-15`):** `schema_contract.py`
is **documentation-in-code** — "No runtime business logic imports the TypedDicts
here for validation." The **source-of-truth WRITER** is
`scripts/build_template_schemas.py` (repo root — NOT under `backend/`; verified
`find` returns `./scripts/build_template_schemas.py`), per §5A.J. Readers
(category, catalog, export) **trust the envelope verbatim**.

| Surface | Migrates to category-svc? | Rationale |
|---|---|---|
| `templates.schema_jsonb` rows (the actual envelopes) | YES — the `templates` table moves to category schema | category SERVES them via `fetch_schema` shim #1 |
| `i18n/schema_contract.py` (the frozenset locks + TypedDicts) | **VENDORED (read-only copy), NOT owned** | it is doc-in-code; category-svc vendors it so its OWN conformance tests + IDE intellisense have the contract. catalog-svc + export-svc vendor their own copies too. **No single service OWNS it** — it is the shared i18n contract lib (MASTER_PLAN §2.B line 126 "i18n shared lib vendored into each service image"). |
| `scripts/build_template_schemas.py` (the seed-time writer) | **STAYS at repo root with the seed/data pipeline** | it is a build/seed concern owned by the data track (`meesell-data-engineer` territory), runs once at seed time, NOT part of category-svc runtime. It WRITES the `templates.schema_jsonb` rows that category-svc then serves. When category's tables migrate to the category schema, this script's DB target updates to write into the category schema — but the script itself does not become category-svc code. |

### The zero-drift guarantee mechanism

1. **Vendored frozensets are byte-identical.** A contract test
   (`test_primitive_values_parity`) in category-svc asserts the vendored
   `schema_contract.PRIMITIVE_VALUES` (+ `ENVELOPE_KEYS`, `FIELD_SHAPE_KEYS`,
   `DATA_TYPE_VALUES`, `COMPLIANCE_SHAPE_VALUES`, `ENUM_RESOLVER_VALUES`)
   frozensets equal the monolith source frozensets **by value, pinned to the
   exact 11 / 7 / 9 / 8 / 2 / 3 cardinalities**. Any drift fails CI.
2. **Envelope conformance test.** The existing
   `test_schema_jsonb_envelope_keys.py` + `test_per_field_shape_keys.py`
   (cited `schema_contract.py:11`) travel with category-svc and run against the
   migrated `templates` rows — every served envelope has all 7 keys, every
   field has all 9, every `primitive` ∈ the 11.
3. **The frontend contract test (FE side)** is the downstream guard — a
   backend→frontend memo (`handoff_contract_category_primitive.md`) notifies
   the frontend lead that the schema-serving surface moved to category-svc but
   the envelope shape is byte-identical (zero FE change). The cookie/contract
   pair only needs notification, not coordination, because the shape is frozen.

---

## Code surfaces

File-level inventory. The `backend/services/svc-category/` tree is the new
home; the old `backend/app/modules/category/` tree is DELETED only after
hybrid-mode CI passes for ≥7 days (MASTER_PLAN §3.C) — until then both coexist
(strangler fig).

### Backend — new service tree (`backend/services/svc-category/`)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `app/main.py` | NEW | Standalone FastAPI app; mounts the 5 public routes + the 2-3 `/internal/*` shim routes; registers the 6-middleware chain (F2); `/health` + `/metrics`; **worker-startup cache pre-warm** (full-tree + top-100 schemas, §6.7) | services-builder |
| `app/router.py` | NEW (from `modules/category/router.py`) | 5 public routes verbatim (same paths, decorators, ETag/304 logic, flag guard) | api-routes-builder |
| `app/internal_router.py` | NEW | 2 frozen `/internal/*` shims (schema, field-enum) + (defensive) commission + super-categories; **internal routes require service-to-service auth (forwarded JWT per §5.A), NOT `get_current_user` UI flow** | api-routes-builder |
| `app/service.py` | NEW (from `modules/category/service.py`) | 8 public methods verbatim; ai_ops imports rewired to the VENDORED `app.ai_ops` (same import path, vendored package) — **call sites byte-identical (§16.G)** | services-builder |
| `app/picker.py` | NEW (from `modules/category/picker.py`) | pure AI-ranking helpers verbatim (no ai_ops import — travels as pure code) | services-builder + meesell-category-picker-builder (ranking-pipeline verify) |
| `app/repository.py` | NEW (from `modules/category/repository.py`) | 7 private methods; bound to schema `category`; NO scope_to_user | services-builder |
| `app/domain.py` | NEW (from `modules/category/domain.py`) | `CategoryRow`, `SuperCategoryInfo` frozen dataclasses | services-builder |
| `app/schemas.py` | NEW (from `modules/category/schemas.py`) | 5 PRIVATE response models | api-routes-builder |
| `app/exceptions.py` | NEW (from `modules/category/exceptions.py`) | `CategoryError` + 4 subclasses | services-builder |
| `app/ai_ops/{client,budget_cap,cost_tracker,guardrail,prompt_registry,eval,metrics}.py` | NEW (VENDORED, byte-identical) | the smart-picker AI path (F3.a); budget brake points at SHARED Valkey DB 0 + audit DB (F3.c) | services-builder |
| `app/ai_ops/prompts/smart_picker_v1.py` | NEW (VENDORED — this ONE prompt) | the only workload category runs; content owned by prompt-engineer | services-builder (carries verbatim) |
| `app/i18n/{schema_contract,messages_en,resolver,primitive_classifier,...}.py` | NEW (VENDORED read-only) | the i18n shared contract lib (§F5); category's `validation_message_id` subset | services-builder |
| `app/core/middleware/*` | NEW (VENDORED) | 6-middleware chain (F2) | services-builder |
| `app/core/{auth,cache,plan_guard,errors,tenancy,metrics}.py` | NEW (VENDORED) | local JWT (F2); `get_or_set` cache (Valkey DB 3); `smart_picker_hourly` plan_guard | services-builder |
| `app/shared/{database,config,valkey}.py` | NEW (vendored, trimmed) | `Settings` with category's env vars (`DATABASE_URL` @ schema `category`, `VALKEY_URL`, `JWT_SECRET`, `GEMINI_*`, `LANGFUSE_*`, `AI_DAILY_BUDGET_INR`, `CACHE_VERSION`, `APP_ENV`); per-service pool sizing (read-heavy, cache-fronted) | services-builder |
| `requirements.txt` | NEW | fastapi, sqlalchemy, asyncpg, redis, httpx, **google-genai (gemini)**, langfuse (category HAS AI — unlike export); NO openpyxl/celery (category has no XLSX/worker) | services-builder |
| `Dockerfile` | NEW (placeholder) | FROM python:3.12-slim; infra lead authors the real one | infra-builder |
| `alembic/` | NEW | own chain rooted at schema `category`; `version_table_schema="category"` | database-builder |
| `tests/test_category_extraction.py` | NEW | hybrid-mode integration test (in-process + HTTP-shim); PRIMITIVE_VALUES parity; budget-brake-shared assertion | backend-coordinator |

### Backend — monolith-side changes (during strangler window)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `backend/app/modules/category/` (8 files) | KEEP-then-DELETE | stay live until hybrid-mode CI green ≥7 days, then deleted | backend-coordinator |
| `backend/app/main.py` | MODIFY (additive-minimal) | at cutover, the in-process `category_router` mount (`main.py:120`) is removed (Traefik routes category paths to svc-category). **Removal is additive-minimal: delete the single `:120` include + the `:41` import; touch NOTHING else.** Until cutover both modes run. | backend-coordinator |

### Infra (placeholders only — owned by infra lead, land on infra branch)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `k8s/svc-category/deployment.yaml` | NEW (placeholder) | api replicas; requests/limits per infra plan §6.3; **Valkey DB 3 cache-mount + pre-warm sidecar/init** (§6.7 — heaviest cache consumer) | infra-builder |
| `k8s/svc-category/service.yaml` | NEW (placeholder) | ClusterIP :8001 | infra-builder |
| Traefik IngressRoute | NEW (placeholder) | `/api/v1/categories/*` + `/internal/categories/*` → svc-category:8001 | infra-builder |
| Postgres schema `category` + role + grants | NEW (placeholder) | `CREATE SCHEMA category; GRANT ... TO category_user; GRANT INSERT ON public.audit_events TO category_user` (the shared audit ledger grant, F3.c) | infra-builder |
| Secret Manager bindings | NEW (placeholder) | `JWT_SECRET` (same secret iam-svc signs with — F2), `GEMINI_API_KEY`, `LANGFUSE_*` injected per-service | infra-builder |

---

## Documentation deliverables

Land alongside the merged extraction code (gate conditions in Acceptance gate):

- **OpenAPI** — svc-category standalone OpenAPI; 5 public + 2-3 internal endpoints.
- **`BACKEND_ARCHITECTURE.md` §9 amendment** — append an "Extracted to
  svc-category (V1.5)" note: the inbound calls (catalog/export/pricing) are now
  HTTP shims; §16.G call-site contract preserved; ai_ops VENDORED per D6;
  budget brake SHARED. **Founder approval required (§9 is LOCKED).**
- **`MASTER_PLAN.md` §4 row F** — update the row annotation: filename
  `SUB_PLAN_0F` (not `SUB_PLAN_06`); dependency "MS-3 complete, parallel MS-G"
  (not the A–E serial chain); "authored 2026-06-12, execution MS-4-gated."
  **Founder touches the master plan; this sub-plan flags the reconciliation.**
- **HTTP-shim contract doc (callee side)** — the 2 (+1 defensive) `/internal/*`
  endpoints category exposes, frozen-shape-cited per §F4. This is the SERVER
  side of the MS-A frozen contract.
- **Runbook** — `docs/runbooks/svc-category-rollback.md` (§3.C specialized for
  category — incl. the cache-prewarm reattach + the budget-brake-keyspace
  carve-out verification).
- **Hybrid-mode CI config note** — at MS-4, CI docker-composes the
  already-extracted services (export, dashboard, image, pricing, customer) +
  the still-monolithic catalog + iam-in-parallel. category's HTTP-mode CI must
  stand up category-svc + assert export-svc/catalog reach it via the
  `/internal/*` shims.

---

## Branch setup

Model C (per common rule 6): `feature/microservices-category/integration` off
develop + group branches (`feature/microservices-category/backend`,
`feature/microservices-category/infra`); worktrees `/tmp/mesell-wt/msF-*`; F3
protection; founder-gate PR `[FOUNDER GATE — DO NOT MERGE]` LEFT OPEN; squash
group merges; lead-gate as PR comment; `--admin`; ref-delete via `gh api`.
NEVER switch the master tree's branch. Integration branch merges
`origin/develop` BEFORE the founder-gate PR opens (shared-file discipline,
common rule 4). **This PHASE-1 docs sub-plan is authored on
`feature/microservices-category/docs-subplan0f` — a docs-only branch distinct
from the execution branches above.**

---

## Memory protocol

**Memories the coding-session leads MUST read at start:**
- `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (extraction
  contracts, §16.G, the MS-A recipe, this sub-plan's notes
  `spec_msF_backend.md`)
- `.claude/agent-memory/meesell-services-builder/MEMORY.md`
- `.claude/agent-memory/meesell-category-picker-builder/MEMORY.md` (smart-picker
  ranking pipeline; calibration constants)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (svc sizing, schema-
  per-service, Traefik, Valkey DB-3 cache mount)
- `.claude/agent-memory/meesell-database-builder/MEMORY.md` (Alembic head chain
  `935e55b4852c → a1b2c3d4e5f6 → f31c75438e61`; schema-move procedure; the 4
  GLOBAL tables)

**Memos created during this extraction:**
- `.claude/agent-memory/meesell-backend-coordinator/spec_msF_backend.md` (the
  executable specialist task spec — companion to THIS sub-plan)
- `.claude/agent-memory/meesell-backend-coordinator/handoff_msF_infra.md`
  (K8s/Postgres/Traefik/Secret placeholders + the audit-DB grant + Valkey-DB-3
  cache mount)
- `.claude/agent-memory/meesell-backend-coordinator/handoff_contract_category_primitive.md`
  (frontend notification — schema-serving surface moved, envelope byte-identical)

---

## Dispatch templates

See the companion spec `spec_msF_backend.md` for the full paste-able specialist
prompts (services-builder / api-routes-builder / database-builder), dispatch
sequence, and per-specialist acceptance criteria. **Not dispatched by this
planning session** (PHASE 1 is authoring only; the session cannot dispatch
agents per CLAUDE.md HYBRID rule 7 — the master session runs steps 2-3 at MS-4).

---

## Acceptance gate

Sub-Plan F execution (MS-4) is DONE when:

- [ ] `feature/microservices-category/backend` PR merged to `.../integration` (backend lead gate)
- [ ] `feature/microservices-category/infra` PR merged to `.../integration` (infra lead gate)
- [ ] Hybrid-mode CI green in BOTH modes (in-process monolith + svc-category-as-pod) per §3.A, for ≥7 days
- [ ] `cd backend && pytest services/svc-category/tests/test_category_extraction.py` green
- [ ] **PRIMITIVE_VALUES parity test green** — vendored `schema_contract` frozensets byte-identical to monolith (11/7/9/8/2/3 cardinalities); envelope + per-field conformance green against migrated `templates` rows
- [ ] **Budget-brake-shared assertion green** — a 2-service test (monolith + svc-category) confirms a `check_and_reserve` from svc-category and one from the monolith both decrement the SAME `ai:cost:daily:{date}` counter (the carve-out: `ai:*` keys NOT `category:`-prefixed)
- [ ] **ai_ops vendoring parity test green** — vendored `budget_cap.py` Lua + key formats byte-identical to source (drift guard, F3.d)
- [ ] **Smart Picker golden eval ≥80% top-5 recall** on the vendored eval set (the smart_picker workload still ranks correctly post-extraction)
- [ ] The 2 frozen `/internal/*` shims (schema, field-enum) respond with the MS-A-frozen shapes; export-svc + catalog reach them via Traefik route flip with ZERO call-site diff (§16.G)
- [ ] `get_commission` `/internal/*` shim served IF MS-D (pricing-svc) calls it over HTTP (Open Question resolution)
- [ ] P95 for `/categories/{id}/schema` (the catalog-autosave hot path) within the §15.E budget — cache hit ≥99% (full-tree + top-100 pre-warm reattached on the extracted pod)
- [ ] CI gates 1 (unit), 2 (smoke), 3 (lint) green; gates 4/5 advisory
- [ ] Documentation deliverables landed (OpenAPI, §9 amendment w/ founder approval, runbook, shim contract doc)
- [ ] V1_FEATURE_SPEC §F2 (Smart Category Picker) + the schema/browse/tree/field-enum acceptance still met against the extracted service
- [ ] `feature_board_backend.md` row reflects MERGED (F2 discipline)
- [ ] Founder approval on `feature/microservices-category/integration` → `develop` PR

> **D3 VM checkpoint (per MS-PAR-1):** at MS-4, the deploy is monolith +
> export + dashboard + image + pricing + customer + category + iam (8 services
> + shrinking monolith) on the dev node. **This is the wave most likely to
> exceed the e2-standard-2 node.** Per the MASTER_PLAN D3 pre-approval, the
> e2-standard-4 upgrade (~₹2,600/mo) is plan-approved BUT the SPEND gets a
> fresh founder ask at the moment the wave's deploy doesn't fit. **STOP and ask
> the founder before provisioning** — never provision on the strength of the
> plan-level pre-approval alone (master-session standing rule).

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | The `ai:*` budget keyspace accidentally gets the `category:` prefix during §2.E namespacing, splitting the GLOBAL ₹500 cap into a per-service cap | **Medium** | **High** | The carve-out (F3.c) is a named acceptance item + a 2-service contract test (`budget-brake-shared assertion`). The vendored `budget_cap.py`/`cost_tracker.py` are byte-identical to source (no prefix logic in them) — the prefix is applied in `shared/valkey.py` factories, and the `ai:*` keys are constructed by the vendored modules, NOT the namespacing layer. Document the exemption explicitly in the runbook. |
| R2 | Vendored `ai_ops/` drifts from the monolith / other AI services | Medium | Medium | Single-source vendoring + recorded source-commit SHA; `test_ai_ops_vendoring_parity` byte-compares the brake code; V2 collapses to `ai-ops-svc` (D6). |
| R3 | PRIMITIVE_VALUES / envelope shape drifts post-extraction, breaking the LIVE frontend wizard | Low | **High** | schema_contract is doc-in-code, vendored read-only, byte-identical; `test_primitive_values_parity` + envelope/field conformance tests; the seed-writer (`scripts/build_template_schemas.py`) stays the single envelope author; frontend notified by memo (shape unchanged → zero FE work). |
| R4 | Schema-fetch HTTP hop blows the catalog-autosave P95 budget (the §15.E hot path; catalog calls `fetch_schema` on autofill) | Medium | Medium | category-svc full-tree + top-100-schema pre-warm at pod startup (§6.7) → ≥99% cache hit; the ~1ms in-process read becomes ~10ms cached HTTP read; pre-extraction load test (MASTER_PLAN §6 line 415: 10× traffic against dockerized catalog-svc + category-svc; halt if P95 exceeds budget by >20%). **catalog is MS-5 (after category) — so at category's cutover, catalog is still in-process; the autosave-over-HTTP path doesn't fire until catalog extracts. This de-risks R4 to the MS-5 window.** |
| R5 | The 3,772-leaf tree migration to the `category` schema corrupts row data or breaks the GIN/pg_trgm indexes (browse depends on them) | Low | High | `ALTER TABLE ... SET SCHEMA category` preserves indexes; database-builder round-trips upgrade/downgrade; integration test runs a browse query post-migration to confirm Bitmap Index Scan still fires (the §G4 pg_trgm verification pattern); 4 GLOBAL tables migrate together (categories + templates + field_enum_values + field_aliases) so cross-table reads stay intra-schema. |
| R6 | MS-G (iam) parallel extraction races category for the shared `JWT_SECRET` / Valkey DB 0 | Low | Medium | D7 local-JWT decouples them — category validates locally with the Secret-Manager `JWT_SECRET`, never calls iam-svc per-request. Shared Valkey DB 0 access (budget brake + rate-limit counters) is atomic (Lua) and prefix-disciplined. The two MS-4 services share NO request-path coupling (F2 note). |
| R7 | `customer→category` super-categories shim missing because the as-built caller import wasn't found | Medium | Low | Author the `/internal/categories/super-categories` shim DEFENSIVELY; Open Question to master session to confirm against MS-A frozen contract + MS-E (customer) sub-plan. If unneeded, the unused shim is harmless. |

---

## Rollback Log

*(Empty until execution. Per MASTER_PLAN §3.C, a rollback during MS-4 is one
Traefik route-flip back to monolith-svc + one `git revert -m 1 <merge-sha>` on
the integration branch + re-run hybrid-mode CI in pure in-process mode +
root-cause recorded here. The budget-brake keyspace + cache pre-warm need no
rollback step — they are shared/global and unaffected by a category-svc
revert.)*

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-12 | mesell-ms-category-session-1 (PHASE 1, hybrid step 1) | Initial AUTHORED draft. Sub-Plan F per MASTER_PLAN §4 row F + MS-PAR-1 parallel program + SUB_PLAN_01 shape template. F1 (ai_ops vendored) + F2 (middleware vendored, local JWT) stated LOCKED from D6/D7. F3 ai_ops vendoring plan + SHARED budget-brake wiring (Valkey DB 0 `ai:cost:daily/pending` + `ai:budget:reservation` + audit_events DB; `ai:*` keyspace carve-out from §2.E namespacing). F4 two frozen `/internal/*` shims (schema, field-enum) per MS-A correction (NO `fetch_xlsx_aliases` runtime shim). F5 PRIMITIVE_VALUES zero-drift (7 envelope keys SOURCE-corrected from "6"; seed-writer stays at repo-root, schema_contract vendored read-only). SOURCE-WINS corrections recorded: filename 0F-not-06, dependency MS-3-parallel-MS-G-not-A–E-serial, fetch_xlsx_aliases runtime-shim dropped. STATUS: AUTHORED — EXECUTION GATED ON MS-4 WAVE OPEN. |

---

**END OF SUB-PLAN F — AUTHORED, execution gated on MS-4 wave open.**

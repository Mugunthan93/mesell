# Category Seeding — Wave 1 Build Spec (`meesell-database-builder`)

| Field | Value |
|---|---|
| Document type | Task SPEC (executable by `meesell-database-builder`) — SPEC ONLY; not yet executed |
| Author | `meesell-backend-coordinator` (Backend Lead) |
| Dispatched by | `meesell-data-engineer` (Data Lead), session `mesell-category-seeding-session-1` |
| Builder session to use | `mesell-category-seeding-backend-session-1` |
| Date | 2026-06-16 |
| Worktree | `/private/tmp/mesell-wt/category-seeding` |
| Branch | `feature/category-seeding` |
| Authorising architecture | `docs/plans/architecture/CATEGORY_SEEDING_ARCHITECTURE.md` (APPROVED rev 1.0, founder-ratified 2026-06-16) |
| Wave | **Wave 1 — LOCAL-ONLY** (D1). No K8s Job, no dev/staging, no namespace touch. Commission = NULL (D2 Phase 1). Pure upsert (D3). |
| V1 feature(s) touched | Feature 2 (Smart Category Picker) + Feature 3 (Fast Catalog Form) reference data — global `categories`/`templates`/`field_enum_values`/`field_aliases` |

> **READ FIRST.** This SPEC is *not* a simple "run `make seed`" ticket. Pre-flight ground-truth (by the backend lead, 2026-06-16) found that the **5 seed scripts import stale module paths** that do **not** exist in the current modular-monolith tree. As written, `PYTHONPATH=backend python scripts/seed_all.py` will `ModuleNotFoundError` on import. §3 of this SPEC authorises the **exact, minimal** import-path corrections required — and *only* those. Read §3 in full before running anything.

---

## §0 Worktree & git discipline (MANDATORY — do this first, every command)

1. **First action, before reading or writing anything:**
   ```
   git rev-parse --show-toplevel
   ```
   It MUST print `/private/tmp/mesell-wt/category-seeding`. If it prints the master tree (`/Users/mugunthansrinivasan/Project/mesell`) or anything else, **STOP IMMEDIATELY** and report "wrong directory" — do not read, do not git-operate, do not seed.
2. **Worktree-scoped absolute paths only.** Every path you read/write/reference is under `/private/tmp/mesell-wt/category-seeding/`. Never reference any path outside it.
3. **One worktree = one branch.** Branch is `feature/category-seeding`. **NEVER** `git checkout <other-branch>` / `git switch`. No branch switching of any kind.
4. **Stage explicit paths only.** **NEVER** `git add -A`, `git add .`, or `git commit -a`. Stage by exact path (e.g. `git add Makefile scripts/seed_categories.py docs/plans/architecture/CATEGORY_SEEDING_WAVE1_RUNLOG.md`).
5. **MeeSell only.** Refuse any reference to Aletheia/Prospero/Zenivo/etc. or any path outside the worktree.
6. **You do NOT merge.** You open the PR and LEAVE IT OPEN. The founder merges `feature/category-seeding → develop`. The backend lead + data lead review first. Never self-merge.

---

## §1 Pre-flight gate — local Postgres reachable (STOP if not)

The seed performs real DB writes. Before touching anything, confirm the target DB exists and is reachable. **Do not fabricate a result; if the DB is down, STOP and report a blocker** (the data lead + backend lead will route to infra/founder).

1. **Resolve `DATABASE_URL`.** `backend/.env` does **NOT** exist in this worktree — only `backend/.env.example`. You must establish a working `DATABASE_URL` for the seed:
   - The seed scripts call `load_dotenv(BACKEND_ROOT / ".env")` then read `settings.DATABASE_URL` from `app.shared.config`. With no `.env` and no exported var, `DATABASE_URL` defaults to `""` and the seed will fail at connect time.
   - **Port conflict to resolve:** `backend/.env.example` line shows `...@localhost:5433/meesell`, but the live local-dev stack (per the most recent master-session handoff, 2026-06-16) and the `Makefile` `test` target use **`localhost:5432`**. The architecture brief says `:5432/meesell`. **Use `5432` unless a live `psql` probe proves the DB is on `5433`.** Probe both if unsure (see step 2).
   - Create a worktree-local `backend/.env` (gitignored — confirm it is in `.gitignore` and do NOT commit it) **or** export `DATABASE_URL` in the shell for the run. Recommended value (async driver, matches `seed_all.py` engine):
     ```
     DATABASE_URL=postgresql+asyncpg://meesell:password@localhost:5432/meesell
     ```
     Confirm the actual username/password against the running local Postgres (the Makefile `test` target uses `meesell:password`; the live app DB may differ — probe).
2. **Probe reachability** (sync driver for a quick liveness check is fine; do not write):
   ```
   pg_isready -h localhost -p 5432    # and -p 5433 if 5432 is dead
   ```
   or a read-only `psql "postgresql://meesell:password@localhost:5432/meesell" -c 'select 1;'`.
   - If neither port answers → **STOP, report blocker**: "local Postgres not running on :5432 or :5433 — cannot seed." Do not invent counts.
3. **Confirm the venv.** This worktree has **no `backend/.venv`**. Create/locate a Python 3.12 venv with `backend/requirements.txt` installed (the `Makefile` targets assume `backend/.venv/bin/python`). Ensure `python-dotenv`, `sqlalchemy`, `asyncpg`, `alembic`, `pydantic-settings` are present. If you must create the venv, do so inside the worktree (`backend/.venv`) — it is gitignored; do not commit it.

---

## §2 Migration confirmation (schema must be at head, with pg_trgm/GIN applied)

The seed must run against a schema that includes migration `a1b2c3d4e5f6` (pg_trgm extension + 3 GIN trigram indexes on `categories`: `idx_categories_path_trgm`, `idx_categories_leaf_name_trgm`, `idx_categories_super_name_trgm`). Without it, `/browse` cannot trigram-search (architecture §6 guard #1).

1. **Confirm the ACTUAL head — do not hard-assert a revision id.** The migration chain has advanced past the brief's referenced `a1b2c3d4e5f6`. The live chain in `backend/alembic/versions/` is:
   ```
   935e55b4852c (baseline, 13 tables)
     → a1b2c3d4e5f6 (pg_trgm + 3 GIN trigram indexes on categories)
       → f31c75438e61 (idx product_drafts saved_at)   ← ACTUAL HEAD
   ```
   Run from `backend/`:
   ```
   .venv/bin/alembic heads        # expect single head: f31c75438e61
   .venv/bin/alembic current      # what the DB is actually at
   ```
2. **If DB is not at head**, bring it up:
   ```
   make migrate          # == cd backend && .venv/bin/alembic upgrade head
   ```
   `make migrate` targets the LOCAL dev DB via `DATABASE_URL`. Run it ONLY against local (§1 resolved the URL). Never run migrations against any namespace DB — this is local-only (D1).
3. **Verify `a1b2c3d4e5f6` is in the applied chain** (not just that head is reached — confirm the trgm migration specifically applied). Either `alembic current` shows `f31c75438e61` (which transitively requires `a1b2c3d4e5f6`), or directly confirm the GIN indexes exist:
   ```sql
   SELECT indexname FROM pg_indexes
   WHERE tablename='categories' AND indexname LIKE '%trgm%';
   -- expect 3 rows
   SELECT extname FROM pg_extension WHERE extname='pg_trgm';   -- expect 1 row
   ```
   Capture this output in the run-log.
4. **Scope fence:** you may run `make migrate`. You must **NOT** author, edit, autogenerate, or delete any file under `backend/alembic/versions/`. No new revisions. The schema is owned by Alembic and is already correct.

---

## §3 AUTHORISED import-path corrections to the seed scripts (the one exception)

**Finding (backend lead pre-flight, 2026-06-16):** all 5 seed scripts import module paths that predate the modular-monolith rebuild. The live tree has **`app.shared.models.*`** and **`app.shared.config`**; there is **NO** `app.models` package and **NO** `app.config` module (confirmed: `app/models/` does not exist, no shim/alias anywhere, scripts last touched only in bulk commit `9e5302a`). The scripts will `ModuleNotFoundError` at import as written.

### 3.1 What you ARE authorised to change — import lines ONLY

Apply these **exact** path substitutions across the 5 seed scripts. These are mechanical module-path corrections, **not logic changes**. The class names and the `settings` symbol are identical in both locations (verified): `Category`, `Template`, `FieldAlias`, `FieldEnumValue`, and `settings`.

| Stale import (current) | Corrected import (apply) | Files affected |
|---|---|---|
| `from app.config import settings` | `from app.shared.config import settings` | `seed_categories.py`, `seed_field_aliases.py`, `seed_field_enum_values.py`, `build_template_schemas.py`, `seed_all.py` |
| `from app.models.category import Category` | `from app.shared.models.category import Category` | `seed_categories.py`, `seed_field_enum_values.py`, `seed_all.py` |
| `from app.models.template import Template` | `from app.shared.models.template import Template` | `seed_categories.py`, `build_template_schemas.py`, `seed_all.py` |
| `from app.models.field_alias import FieldAlias` | `from app.shared.models.field_alias import FieldAlias` | `seed_field_aliases.py`, `seed_all.py` |
| `from app.models.field_enum_value import FieldEnumValue` | `from app.shared.models.field_enum_value import FieldEnumValue` | `seed_field_enum_values.py`, `seed_all.py` |

Note: `seed_all.py` has TWO blocks importing the models (in `verify_db_counts()` and `run_verification_queries()`) — fix both. `build_template_schemas.py`'s `from app.i18n.primitive_classifier ...` and `from app.i18n.step_assignment ...` imports are **already correct** (`app.i18n` exists) — leave them untouched.

### 3.2 What you are FORBIDDEN to change (scope fences)

- **DO NOT** change `seed_categories.py` line 137 — `"commission_pct": None` stays NULL (D2 Phase 1). Commission is intentionally NULL this wave.
- **DO NOT** alter any seeding *logic*: no change to the upsert shape, conflict keys, chunk size (500), tolerances, `TARGETS` dict, FK ordering, or the `RuntimeError`-on-unresolved-hash guard.
- **DO NOT** touch `backend/alembic/versions/*`.
- **DO NOT** touch `frontend/`, `k8s/`, `terraform/`, or any infra/VM config.
- **DO NOT** seed commission, author `category_commissions.json`, or write `seed_category_commissions.py` — that is Wave 1.5, out of scope.

### 3.3 If the imports already resolve

If — contrary to the pre-flight finding — `import app.models.category` already resolves in your venv (e.g. a shim was added since), then make **no** script edits and proceed straight to §4. Record in the run-log that the imports already resolved and no edits were needed. **First try the unmodified run; only apply §3.1 if the run fails on `ModuleNotFoundError: No module named 'app.models'` / `'app.config'`.** Capture the failing traceback in the run-log before editing.

---

## §4 Add the `make seed` target & RUN the seed

### 4.1 Add a `seed` target to the `Makefile`

The `Makefile` currently has `migrate` but no `seed`. Add a `seed` target wrapping the orchestrator, consistent with the existing `migrate`/`test` style (venv-relative). Place it next to `migrate`, and add `seed` to the `.PHONY` line:

```makefile
seed:
	PYTHONPATH=backend .venv/bin/python scripts/seed_all.py
```

(`seed_all.py` itself prepends `backend/` to `sys.path`, but the explicit `PYTHONPATH=backend` matches the architecture's sanctioned run command `PYTHONPATH=backend python scripts/seed_all.py` and is harmless.) Use the worktree's resolved `python` interpreter — if your venv path differs from `backend/.venv`, match what the other Makefile targets resolve to. Confirm `make seed` runs from the repo root (the orchestrator computes `PROJECT_ROOT` from `__file__`, so cwd-independent).

Document `make migrate && make seed` in the run-log as the sanctioned local bring-up sequence.

### 4.2 Run the seed (first run)

```
make migrate && make seed
```

Expected: the 4 FK-ordered steps run (field_aliases → templates → categories → field_enum_values), each prints a count, then smoke checks + DB verification queries run. Capture the **full** stdout/stderr to the run-log. The orchestrator exits `0` on success, `1` on any count drift.

---

## §5 Count verification (the gate)

`seed_all.py` self-checks these and exits non-zero on drift. Capture its output AND, independently, paste the raw `SELECT count(*)` for each table from a `psql` session (belt-and-suspenders proof):

| Table | Required | Tolerance |
|---|---|---|
| `field_aliases` | **67** | EXACT — any drift = hard fail |
| `categories` | **3772** | EXACT — any drift = hard fail |
| `templates` | **≈ 3566** | ±0.5% → range **[3539, 3575]** (SSoT 3557; +9 explained) |
| `field_enum_values` | **≈ 49259** | ±0.5% (SSoT 49295; −36 explained) |

The orchestrator's exit code MUST be `0`. If any EXACT count misses (67 / 3772), STOP and report — do not "round" or rationalise. The architecture §5.1 tolerance rationale explains the templates +9 and enum −36 deltas; reproduce those numbers, do not invent new ones.

---

## §6 Acceptance proof (architecture §6 guard #5 — definition of done)

This is the inverse of the #239 blocker symptom (`0 schemas warmed` + empty `/suggest` + empty `/browse`). Prove all three light up. The seed alone is not "done" until these pass.

### 6.1 Prewarm warms **>0** schemas
The function is `prewarm_top_categories(n=100)` at `backend/app/core/cache.py:152`. It logs `prewarm_top_categories: %d schema entries warmed` (line 244). You must show a **count > 0** (NOT `0 schema entries warmed`). Two acceptable ways:
- Start the API locally (`make dev-local`, which runs `alembic upgrade head` then `uvicorn` — prewarm runs at worker startup) and grep the startup log for the `schema entries warmed` line; OR
- Call it directly from a short async REPL/script against the seeded DB:
  ```python
  import asyncio
  from app.core.cache import prewarm_top_categories
  asyncio.run(prewarm_top_categories(100))   # observe the ">N schema entries warmed" log
  ```
  Requires Valkey reachable (architecture cache layer) — if Valkey is down, note it; prewarm may warn-and-skip. The load-bearing assertion is the warmed count is **> 0** given seeded categories. Capture the exact log line.

### 6.2 `GET /api/v1/categories/suggest` returns a NON-empty suggestion set
**Auth + flags to know (verified in `backend/app/modules/category/router.py`):**
- The route requires `Depends(get_current_user)` — you need a valid access token. In local dev the OTP bypass `000000` is available (per the local-dev handoff) to mint a token via the auth flow; OR call the service layer directly (`category_service.suggest_categories(user_id, q, db=db)`) with a synthesized `user_id` to bypass HTTP auth for proof purposes.
- The route is gated by `FEATURE_SMART_PICKER_ENABLED` (default `True` in dev per `app.shared.config:192`) — returns 404 if false. Confirm it is on.
- `/suggest` calls the AI track (Gemini). If AI is unavailable/budget-capped locally it returns 200 with `fallback_offered=true` and possibly empty AI suggestions — **that is an AI-availability condition, not a seeding failure.** The seeding proof that matters here is that the **category corpus is queryable**. If `/suggest` returns empty solely due to AI fallback, pivot the non-emptiness proof to the deterministic path: prove `/browse` (6.3) returns matches AND that `category_service` can resolve real categories from the seeded table (e.g. a direct repo/service category lookup returns rows). Document precisely which path you used and why.

Exercise with a real description, e.g. `q="cotton kurti for women"` (URL-encode). Capture request + response.

### 6.3 `GET /api/v1/categories/browse` trigram search returns matches
This is the deterministic pg_trgm path (no AI) — the cleanest seeding proof. It also requires `get_current_user`. Call with a real query term that exists in seeded `leaf_name`/`path` (e.g. `q="kurti"` or `q="saree"`), confirm a non-empty match set comes back. Capture request + response. This exercises the GIN trigram indexes from §2 — non-empty results here prove (a) rows seeded AND (b) trgm indexes live.

> If standing up the full HTTP API locally is impractical, the service-layer equivalents are acceptable proof PROVIDED you state clearly that you exercised the service (not HTTP) path and the service returns non-empty real category data from the seeded table. Be concrete; paste the actual returned rows/payload.

---

## §7 Idempotency proof (the merge-gate's key evidence)

Run the seed a **SECOND** time and prove identical results — no errors, no drift. This is what proves the upsert-on-natural-key design (architecture §3d/§5.3).

1. `make seed` again (second run).
2. Capture full output. Required: **identical** row counts to the first run (67 / 3772 / ~3566 / ~49259), all smoke checks `OK`, exit `0`, zero errors, zero `RuntimeError`.
3. Independently re-`SELECT count(*)` all four tables; confirm byte-identical counts to the first run.
4. Paste BOTH runs' count blocks side-by-side in the run-log and the PR body.

A second run that changes any count, raises, or exits non-zero = FAIL → STOP and report; do not open the PR.

---

## §8 Run-log artifact

Author a run-log capturing all evidence (you MAY create this file; stage it explicitly):

`docs/plans/architecture/CATEGORY_SEEDING_WAVE1_RUNLOG.md`

Contents:
- The §0 worktree confirmation output.
- §1 DB reachability probe result + resolved `DATABASE_URL` (REDACT the password — show `...:****@localhost:5432/meesell`).
- §2 `alembic heads`/`alembic current` output + the 3-trgm-index + pg_trgm confirmation.
- §3 whether import edits were needed; if so, the exact list of files+lines changed (the §3.1 substitutions) and the pre-edit failing traceback.
- §5 count block (orchestrator output + raw `SELECT count(*)`).
- §6 acceptance proof (prewarm log line, `/suggest` or service-path result, `/browse` result).
- §7 BOTH idempotency run count blocks.

Do **NOT** commit `backend/.env` or the venv.

---

## §9 PR (open, leave open — founder merges)

1. Stage ONLY explicit paths. Expected staged set:
   - `Makefile` (added `seed` target)
   - the 5 seed scripts IF §3 edits were applied (`scripts/seed_all.py`, `scripts/seed_categories.py`, `scripts/seed_field_aliases.py`, `scripts/seed_field_enum_values.py`, `scripts/build_template_schemas.py`)
   - `docs/plans/architecture/CATEGORY_SEEDING_WAVE1_RUNLOG.md`
   - (this SPEC — `CATEGORY_SEEDING_WAVE1_SPEC.md` — is staged/committed by the data lead, NOT you; do not stage it unless the data lead instructs)
2. Commit message:
   ```
   chore(seed): wire `make seed` + run local category reference-data seed (Wave 1, local-only)

   - Adds Makefile `seed` target wrapping scripts/seed_all.py.
   - Corrects stale app.models/app.config imports → app.shared.models/app.shared.config
     in the 5 seed scripts (module-path only; zero logic change; commission stays NULL per D2 Phase 1).
   - Seeds local Postgres: categories=3772, field_aliases=67, templates≈3566, field_enum_values≈49259.
   - Acceptance proof: prewarm >0 schemas, /browse trgm matches, idempotent second run identical.

   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
3. Open PR `feature/category-seeding → develop`. **Use the backend PR template** at `.github/PULL_REQUEST_TEMPLATE/backend.md` and fill EVERY field — no `<>` placeholders left:
   - Feature slug: `category-seeding`; spec ref: `CATEGORY_SEEDING_ARCHITECTURE.md §5/§6`.
   - Test evidence: the §5 count block + §6 acceptance proof + §7 BOTH idempotency runs (this is the load-bearing evidence; CI gates 1/2/3 still expected green).
   - Session block: `mesell-category-seeding-backend-session-1`, branch `feature/category-seeding`.
   - Database-migration section: state "no migration authored; schema confirmed at head `f31c75438e61` (incl. `a1b2c3d4e5f6` pg_trgm/GIN); seed is data-only."
4. **LEAVE THE PR OPEN.** Do not merge. Do not `--admin`. The backend lead + data lead review at the merge gate; the **founder** merges `feature/category-seeding → develop`. Self-merge is forbidden.
5. **Board:** you do NOT write `feature_board_data.md` (data lead's sole-writer surface) or `feature_board_backend.md` (backend lead's). Report your PR number + status back to the dispatching lead; the leads flip the board rows.

---

## §10 STOP conditions (report, do not push through)

- `git rev-parse --show-toplevel` ≠ the worktree → STOP (wrong dir).
- Local Postgres unreachable on :5432 and :5433 → STOP (blocker; do not fabricate counts).
- Seed import failure that is NOT one of the §3.1 stale paths (i.e. a deeper breakage) → STOP, report the traceback; do not invent fixes beyond §3.1.
- Any EXACT count misses (field_aliases ≠ 67 or categories ≠ 3772) → STOP.
- Orchestrator exit code ≠ 0 on either run → STOP.
- Second (idempotency) run differs from the first in any count, or errors → STOP, do not open PR.
- Any change would require touching `backend/alembic/versions/*`, `frontend/`, `k8s/`, `terraform/`, or commission data → STOP, escalate (out of Wave 1 scope).
- `prewarm` reports `0 schema entries warmed` after a successful seed → STOP (seed didn't actually light up the consumer; investigate before declaring done).

---

## §11 Acceptance checklist (builder self-check before opening PR)

- [ ] `git rev-parse --show-toplevel` == `/private/tmp/mesell-wt/category-seeding`; on `feature/category-seeding`.
- [ ] Local Postgres reachable; `DATABASE_URL` resolved (port confirmed; password not committed).
- [ ] `alembic current` at head `f31c75438e61`; pg_trgm + 3 GIN trgm indexes confirmed present.
- [ ] `make seed` target added to `Makefile` (+ `.PHONY`).
- [ ] Seed imports resolve (either already, or via the §3.1 module-path corrections — logic untouched, commission line 137 = NULL untouched).
- [ ] First run: exit 0; field_aliases=67 (exact), categories=3772 (exact), templates∈[3539,3575], field_enum_values within ±0.5% of 49295.
- [ ] Acceptance proof: prewarm warms **>0** schemas; `/browse` trgm returns matches; `/suggest` (or documented service-path equivalent) returns non-empty real category data.
- [ ] Idempotency: SECOND run identical counts, exit 0, zero errors; both run blocks captured.
- [ ] Run-log authored at `docs/plans/architecture/CATEGORY_SEEDING_WAVE1_RUNLOG.md`.
- [ ] Explicit-path staging only; `.env`/venv NOT committed.
- [ ] PR `feature/category-seeding → develop` opened with the **backend** template fully filled; LEFT OPEN for founder merge.

---

*End of SPEC. SPEC-only — authored by `meesell-backend-coordinator`. The data lead decides staging/commit of this SPEC file. Execution is performed by `meesell-database-builder` under session `mesell-category-seeding-backend-session-1`.*

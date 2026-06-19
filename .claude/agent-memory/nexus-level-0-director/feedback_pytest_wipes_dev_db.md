---
name: pytest-wipes-dev-db
description: Running pytest against the local dev DATABASE_URL wipes the dev DB via conftest's non-provisioned fixture; every DB-touching dispatch must force an isolated TEST_DATABASE_URL
metadata:
  type: feedback
---

When dispatching ANY MeeSell agent that may run pytest / DB-backed tests on the laptop, the dispatch MUST require an isolated, disposable `TEST_DATABASE_URL` (e.g. `meesell_w3_test`) and forbid running pytest while `TEST_DATABASE_URL` is unset or equals the dev DB. Tell the agent to verify `current_database()` is NOT `meesell` before any test run.

**Why:** On 2026-06-19, a coordinator's Gate-4 review ran pytest against the dev `DATABASE_URL`. `backend/tests/conftest.py`'s `db_engine` fixture, in NON-provisioned mode (`TEST_DATABASE_URL` unset), does `Base.metadata.drop_all` + `create_all` at setup and `drop_all` at teardown against `DATABASE_URL`. Combined with a role-level `search_path` pointing at `public`, it **dropped the entire local dev `public` schema** — destroying the 3,772 seeded categories + all reference rows. There was no SQL backup at the time.

**Recovery (proven):** `make seed` → runs `scripts/seed_all.py` (idempotent UPSERT, ~23s) and fully restores all 4 reference tables: categories=3772, templates≈3566, field_aliases=67, field_enum_values≈49259. Source of truth = `backend/app/data/meesho_category_tree.json`. Schema is restored separately via `alembic upgrade head` (head was `f8fa7a36383f` during Razorpay waves). A daily versioned `pg_dump` safeguard (launchd, dumps in `~/mesell-db-backups/`, restore runbook `docs/runbooks/DEV_DB_BACKUP_RESTORE.md`) was added afterward to cover non-reproducible rows too.

**How to apply:** Bake the "🛑 do not wipe the dev DB / use isolated TEST_DATABASE_URL" guard into every dispatch that touches tests. Prefer non-DB unit tests when isolation can't be guaranteed. Never let an agent run `make seed`, drop/alter the dev DB, or weaken the conftest dev-DB guard as a side effect. Related: [[project_pricing_transfer_price_model]] (the 3,772-category data set this protects).

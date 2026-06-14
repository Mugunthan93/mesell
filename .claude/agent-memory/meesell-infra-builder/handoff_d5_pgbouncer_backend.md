# Handoff → meesell-backend-coordinator — D5 PgBouncer asyncpg/SQLAlchemy compatibility (R-MS-8)

**From:** meesell-infra-builder (MS-0 / D5 step 1, session `mesell-ms-pgbouncer-session-1`)
**Date opened:** 2026-06-12
**Branch:** `feature/microservices-pgbouncer/integration` (founder-gate PR to develop, left OPEN)
**Infra deliverable that triggers this:** PgBouncer in **transaction-pool mode** is authored
and validated in dev (`k8s/pgbouncer.yaml`, `pool_mode=transaction`). It is the D5 prerequisite
before any service flips `DATABASE_URL` to `pgbouncer:6432`.

## The ask (BACKEND CODE — out of infra's lane)

Transaction pooling returns a Postgres backend to the pool at COMMIT/ROLLBACK, not at client
disconnect. That breaks any session-level / cross-transaction state. Before any service's
`DATABASE_URL` is flipped to `pgbouncer.dev.svc.cluster.local:6432`, the backend async DB layer
(`backend/app/shared/database.py` engine config + every asyncpg connect path) MUST be made
transaction-pool-safe. Per infra plan §3.3 item 2 + R-MS-8:

1. **asyncpg `statement_cache_size=0`** — asyncpg prepares statements server-side by default and
   caches them per-connection; with transaction pooling the same logical connection lands on
   different backends, so a cached prepared statement OID is invalid. Set via
   `connect_args={"statement_cache_size": 0}` (and `prepared_statement_cache_size=0` for
   SQLAlchemy's own asyncpg dialect prepared-stmt cache).
2. **`pool_pre_ping=False`** (infra plan §3.3) — pre-ping issues an extra round-trip that is
   wasteful/incorrect through a transaction pooler; rely on PgBouncer + server_idle_timeout.
3. **`executemany_mode='values_only'`** (infra plan §3.3) — for asyncpg executemany under the
   pooler.
4. **No `SET LOCAL` / no session GUCs that must persist across transactions**, no
   `LISTEN/NOTIFY`, no advisory-lock-held-across-transactions, no temp tables expected to
   survive a transaction boundary. Audit the codebase for these.
5. PgBouncer side is already set defensively: `max_prepared_statements = 0`,
   `server_reset_query = DISCARD ALL`, `ignore_startup_parameters = extra_float_digits`.

## Validation the backend owes before any flip

- Run each service's integration suite (`pytest -m "integration"`) against PgBouncer (point the
  test DSN at `:6432`) — this is R-MS-8's "smoke-test full integration suite against PgBouncer".
- If transaction mode breaks something irreducible, the documented fallback is `pool_mode=session`
  (lower multiplexing but session-safe) — infra can change that one line in
  `k8s/pgbouncer.yaml` ConfigMap on request.

## What infra has done / will do

- DONE: authored + dry-run-validated PgBouncer (transaction mode) + raised
  `max_connections=200` (TF, `module.postgres_dev`). Cutover/rollback runbook:
  `docs/runbooks/pgbouncer-cutover.md`.
- ON FOUNDER GO: apply the manifests (the apply is founder-gated; the DATABASE_URL flip is a
  SEPARATE per-service founder-gated step).
- Infra owns the `pgbouncer:6432` endpoint + the userlist Secret; backend owns the engine/driver
  config above.

## Inter-lead request row (on infra board, outgoing)

`| backend-coordinator | microservices-pgbouncer | asyncpg/SQLAlchemy transaction-pool compat (statement_cache_size=0, pool_pre_ping=False, executemany_mode=values_only, no SET LOCAL/LISTEN) before any DATABASE_URL->pgbouncer:6432 flip - see handoff_d5_pgbouncer_backend.md | 2026-06-12 | OPEN |`

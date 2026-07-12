# `meesell-valkey` — self-hosted Valkey 8 on Fly.io

Config-as-code for the Fly app **`meesell-valkey`**, the self-hosted Valkey 8 cache
that **replaces Upstash Redis `meesell-cache`**.

> ## Status (2026-07-12) — DEPLOYED to `sin` (bom-capacity fallback), EPHEMERAL
> `bom` had **no machine/volume capacity** (`no capacity available in bom` across ~25
> attempts, incl. `--ha=false`). Per **coordinator-approved capacity fallback**,
> deployed to **`sin`** (Singapore — nearest APAC region): machine `683601ecd62168`
> (`silent-sun-4502`) **started**; verified `PONG` + `maxmemory-policy=noeviction` +
> `appendonly=no`; meesell-api reaches it over Fly 6PN (`meesell-valkey.internal` →
> `fdaa:…:fa06:2`, TCP OK). **Cross-region tradeoff:** ~60-100 ms per round-trip vs a
> same-region cache (category endpoints slower) — but WORKING beats the current 500s.
> **EPHEMERAL** — no volume (bom volume capacity was also unavailable), pure in-memory.
> **TODO(migrate-to-bom):** when `bom` capacity frees, set `primary_region="bom"`,
> create the `valkey_data` volume + restore `[mounts]` + re-enable AOF in
> `valkey.conf`, and redeploy. See the two `TODO(volume)` blocks in `fly.toml` +
> `valkey.conf`.

## Why this exists — the Upstash single-DB defect

MeeSell's backend uses **four logical Valkey DBs**, enforced by the LOCKED factory
`backend/app/shared/valkey.py` (BACKEND_ARCHITECTURE §1.B / §5.C — "cross-DB
forbidden", NOT env-configurable):

| DB | Purpose | Consumer |
|----|---------|----------|
| 0 | OTP, sliding-window rate-limit, sessions, refresh-token allowlist | `core/auth`, middleware |
| 1 | Celery **broker** | `workers/celery_app.py` |
| 2 | Celery **result** backend | `workers/celery_app.py` |
| 3 | application **read-through cache** (schemas, enums, category tree, seller-profile) | `core/cache.py` |

`_build_url_for_db(VALKEY_URL, n)` rewrites the URL path to `/n` for each factory.

**Upstash serverless Redis supports ONLY DB 0.** So on the Fly platform, every
DB1/2/3 operation failed with:

```
redis.exceptions.ResponseError: Only 0th database is supported! Selected DB: 3
```

**Blast radius:** every read-through-cached endpoint (category browse/suggest/list/
schema/field-enum + seller-profile) returned 500; all Celery jobs (image `rembg`,
XLSX export, AI) could not reach the broker. `/health` only pings DB 0, so it
**falsely reported healthy**. Not fixable in code (the topology is locked) or via env.

**Fix (this app):** a self-hosted Valkey 8 supports DBs 0-15 natively, so the locked
4-DB topology works byte-identical. We repoint the `VALKEY_URL` secret on
`meesell-api` and decommission Upstash.

## What this deploys

- Fly app **`meesell-valkey`**, region **`bom`** (co-located with `meesell-api` + `meesell-db`).
- **Official `valkey/valkey:8`** base image + a minimal `Dockerfile` that adds only
  `valkey.conf` (static config) and `docker-entrypoint.sh` (injects the password).
- **One `shared-cpu-1x` 256MB machine**, **always-on** (no auto-stop), **no HA**.
- **1GB volume `valkey_data`** mounted at `/data` for **AOF** persistence.
- **Private only** — no `[http_service]`/`[[services]]` ⇒ **no public IP**. Reachable
  only over Fly 6PN from `meesell-api` (same `personal` org) at
  `meesell-valkey.internal:6379`.
- **`requirepass`** auth — a 256-bit hex password stored as the Fly secret
  `VALKEY_PASSWORD` on this app and embedded in the `VALKEY_URL` secret on `meesell-api`.

### Design decisions (documented deviations)

- **Persistence = AOF** (`appendonly yes`, `appendfsync everysec`), RDB off (`save ""`).
  Mirrors `INFRASTRUCTURE_PLAYBOOK.md` §6.2. AOF gives ~1s durability for DB0
  sessions/refresh-allowlist + the DB1 broker queue across machine restarts; RDB is
  disabled to avoid a second fork-COW memory spike on the small machine.
- **Eviction = `noeviction`, NOT `allkeys-lru`.** The old K3s banner used
  `allkeys-lru`, but that assumed a cache-only instance. This is a **mixed multi-DB**
  instance: silent LRU eviction could drop a queued Celery job (DB1) or a live
  session / refresh-allowlist key (DB0). The DB3 read-through cache self-bounds via
  the app's per-entry TTLs, so `noeviction` (fail loud, never silently corrupt
  operational state) is the correct policy here.
- **`maxmemory 180mb`** on the 256MB machine — a defensive ceiling (real working set
  is a few MB) so writes are refused before the kernel OOM-kills the process.
- **Runs as root** inside the single-tenant machine (we override the image's
  privilege-dropping entrypoint). Acceptable for this private single-tenant VM; a
  prod-grade hardening pass would drop to the `valkey` user + chown `/data`.

### Not done (deferred, prod-grade decisions)

- **No HA / no replica** — one machine. This is a **dev/staging-grade** choice
  (~₹200-300/mo). A prod-grade HA topology (replica + failover, or a managed
  multi-DB cache) is a separate later decision.
- **No Fly-level health check** — a no-services app has no proxy check; Valkey's own
  crash-restart + the end-to-end app checks are the signal. A prod pass would add a
  `[checks]` exec probe.

## Runbook

All `flyctl` commands assume an isolated `HOME` if `~/.fly` has root-owned lock cruft
(`HOME=/tmp/meesell-flyhome flyctl ...` with `config.yml`+`state.yml` copied in).

### First provision (already done)

```bash
cd platform/fly/valkey
flyctl apps create meesell-valkey --org personal
# password never printed / never on argv — piped via stdin to `secrets import`:
printf 'VALKEY_PASSWORD=%s\n' "$(cat ~/.meesell-secrets/fly-valkey-password)" \
  | flyctl secrets import -a meesell-valkey
flyctl volumes create valkey_data --size 1 --region bom -a meesell-valkey --yes
flyctl deploy --remote-only -c fly.toml -a meesell-valkey
# then repoint the client:
printf 'VALKEY_URL=redis://:%s@meesell-valkey.internal:6379\n' \
  "$(cat ~/.meesell-secrets/fly-valkey-password)" | flyctl secrets import -a meesell-api
```

### Password rotation

1. Generate a new hex password → `~/.meesell-secrets/fly-valkey-password` (chmod 600).
2. `printf 'VALKEY_PASSWORD=%s\n' "$(cat ...)" | flyctl secrets import -a meesell-valkey`
   (restarts the valkey machine with the new password).
3. `printf 'VALKEY_URL=redis://:%s@meesell-valkey.internal:6379\n' "$(cat ...)" | flyctl secrets import -a meesell-api`
   (rolling-restarts `meesell-api` api + worker).
   Never echo the value; never put it on argv — always pipe via `secrets import`.

### Rollback to Upstash (instant)

The `VALKEY_URL` value is the whole switch. To revert to Upstash, set `VALKEY_URL`
on `meesell-api` back to the Upstash connection string (`flyctl redis status
meesell-cache` shows it once, if it still exists). Keep Upstash until the self-hosted
Valkey is fully verified.

## Files

```
platform/fly/valkey/
├── README.md              ← this guide
├── fly.toml               ← app config (bom, private-only, 1GB mount, 256MB always-on)
├── Dockerfile             ← FROM valkey/valkey:8 + conf + entrypoint
├── valkey.conf            ← static config (AOF, maxmemory/noeviction, bind) — NO password
└── docker-entrypoint.sh   ← injects --requirepass "$VALKEY_PASSWORD" at runtime
```

> **Terraform follow-up:** this app is provisioned imperatively (like the rest of the
> Fly estate). It should later be adopted into the `platform/flyio-ghpages` Terraform
> switch (an idempotent flyctl shim + a `meesell-valkey.internal` note in the switch
> checklist). See `platform/README.md` §2.3 / the import runbook. **Not built now** —
> flagged only.

> **Playbook note:** `docs/INFRASTRUCTURE_PLAYBOOK.md` is GCP/K3s-only and has no
> Fly.io section. Adding a Fly/Pages + self-hosted-Valkey runbook needs founder
> approval (§7.3) — flagged, not made here.

# Runbook — Local Dev DB Backup & Restore

**Owner:** `meesell-infra-builder`
**Scope:** LOCAL dev Postgres only (`meesell` on `localhost:5432`, Postgres 16 on the founder's laptop).
**Governing playbook rules:** `INFRASTRUCTURE_PLAYBOOK.md` §5.3 (Postgres `pg_dump` backup) + §10 (secret discipline).

> This runbook covers the **local dev database**. It does NOT touch the K3s cluster,
> the `dev`/`staging`/`prod` namespace Postgres, or any GCP resource. For cluster DB
> backups see `INFRASTRUCTURE_PLAYBOOK.md` §5.3 and the `backup-cronjob.yaml` path.

---

## Why this exists

The local dev DB was once wiped by a test run with **no backup**. Only reproducible
reference data survived (via `make seed`). This safeguard takes a **daily, versioned,
restorable** snapshot of BOTH schema and data so an accidental wipe is always recoverable
to the last nightly state — not just to seeded reference data.

---

## How the backup works

- **Script:** `scripts/backup_dev_db.sh`
  - Reads the DB password from `backend/.env` (`DATABASE_URL`) — the password value is
    **never echoed, logged, or committed**. It is exported only as `PGPASSWORD` for the
    duration of the dump and scrubbed on exit.
  - Runs `pg_dump` in two formats:
    - **`meesell_dev_YYYYMMDD_HHMMSS.dump`** — custom format (`-Fc`), compressed,
      **schema + data**, the authoritative restorable archive.
    - **`meesell_dev_YYYYMMDD_HHMMSS.sql`** — plain SQL, human-readable convenience copy
      (best-effort; not load-bearing).
  - Logs each run (timestamp, file, size, `categories` row count as a sanity signal) to
    `~/mesell-db-backups/backup.log`.
  - Is **idempotent** and safe to run manually at any time.

- **Schedule:** macOS **launchd** agent `com.meesell.devdb-backup` runs the script
  **daily at 02:00 local time**.
  - Plist template: `scripts/launchd/com.meesell.devdb-backup.plist`
  - Installed copy: `~/Library/LaunchAgents/com.meesell.devdb-backup.plist`

---

## Where the dumps live

```
~/mesell-db-backups/
├── meesell_dev_YYYYMMDD_HHMMSS.dump   # restorable custom-format archives (-Fc)
├── meesell_dev_YYYYMMDD_HHMMSS.sql    # plain-SQL convenience copies
├── backup.log                          # one row per run (ts | file | size | categories | rotation)
├── launchd.out.log / launchd.err.log   # launchd stdout/stderr
```

**This directory is OUTSIDE the git repo on purpose** — dumps may contain user data and
must never be committed. Nothing under `~/mesell-db-backups/` is tracked by git. The repo
only ever holds the three tooling files (script, plist template, this runbook).

---

## Retention policy

- **Daily:** keep the last **14** daily `*.dump` archives; older dailies are deleted.
- **Weekly:** any dump taken on a **Sunday** is additionally preserved for **~8 weeks
  (56 days)**, even after it falls out of the 14-day daily window.
- The matching `.sql` sibling is rotated together with its `.dump`.

Tunable at the top of `scripts/backup_dev_db.sh` (`KEEP_DAILY`, `WEEKLY_RETENTION_DAYS`).

---

## Restore — recover the dev DB from a dump

> **Restoring is destructive to current data.** It cleans and replaces the contents of
> the `meesell` database. Take a fresh manual backup first if the current state matters.

### 1. Pick a dump

```bash
ls -lt ~/mesell-db-backups/*.dump | head
```

### 2. (Optional but recommended) snapshot current state first

```bash
bash /Users/mugunthansrinivasan/Project/mesell/scripts/backup_dev_db.sh
```

### 3. Restore the custom-format archive (clean restore into `meesell`)

`pg_restore --clean --if-exists` drops existing objects before recreating them, giving a
clean replace. The password comes from `backend/.env` via `PGPASSWORD` — never typed on
the command line.

```bash
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

# Load the password into the environment WITHOUT printing it:
export PGPASSWORD="$(grep -E '^DATABASE_URL=' \
  /Users/mugunthansrinivasan/Project/mesell/backend/.env \
  | head -1 | sed -E 's|^DATABASE_URL=[^/]*//[^:]+:([^@]*)@.*$|\1|')"

# THE RESTORE COMMAND (replace <DUMP> with your chosen file):
pg_restore \
  --clean --if-exists \
  --no-owner --no-privileges \
  --dbname="postgresql://meesell@localhost:5432/meesell" \
  ~/mesell-db-backups/<DUMP>

unset PGPASSWORD
```

A few non-fatal `does not exist, skipping` notices on `--clean --if-exists` are normal on
a near-empty DB.

### 4. Verify

```bash
export PGPASSWORD="$(grep -E '^DATABASE_URL=' \
  /Users/mugunthansrinivasan/Project/mesell/backend/.env \
  | head -1 | sed -E 's|^DATABASE_URL=[^/]*//[^:]+:([^@]*)@.*$|\1|')"

psql "postgresql://meesell@localhost:5432/meesell" -tAc "SELECT count(*) FROM categories;"
unset PGPASSWORD
```

Expect a healthy `categories` count (the known-good reseeded state was **3,772**). Cross-check
against the `categories=` value recorded for that dump in `~/mesell-db-backups/backup.log`.

---

## If no dump is available — reproduce reference data

Reference/seed data (categories, field aliases, enum values, etc.) is reproducible without
any dump:

```bash
cd /Users/mugunthansrinivasan/Project/mesell
make seed
```

`make seed` runs `scripts/seed_all.py` and rebuilds the reference tables (e.g. the 3,772
categories). It does **not** restore user-created rows — for those you need a `*.dump`.
Order of preference for recovery: **(1) latest `*.dump` via `pg_restore`**, then
**(2) `make seed`** for reference data only.

---

## Operations

### Run a backup now (manual)

```bash
bash /Users/mugunthansrinivasan/Project/mesell/scripts/backup_dev_db.sh
tail -5 ~/mesell-db-backups/backup.log
```

### Install / load the daily schedule (launchd)

```bash
cp /Users/mugunthansrinivasan/Project/mesell/scripts/launchd/com.meesell.devdb-backup.plist \
   ~/Library/LaunchAgents/com.meesell.devdb-backup.plist
launchctl unload ~/Library/LaunchAgents/com.meesell.devdb-backup.plist 2>/dev/null || true
launchctl load   ~/Library/LaunchAgents/com.meesell.devdb-backup.plist
launchctl list | grep meesell        # confirm com.meesell.devdb-backup is listed
```

### Stop / uninstall the schedule

```bash
launchctl unload ~/Library/LaunchAgents/com.meesell.devdb-backup.plist
rm ~/Library/LaunchAgents/com.meesell.devdb-backup.plist
```

### Inspect the run journal

```bash
tail -20 ~/mesell-db-backups/backup.log
```

---

## Safety notes

- The DB password is **never** printed, echoed, committed, or passed on a command line —
  only exported as `PGPASSWORD` for the dump/restore process (playbook §10).
- Dumps live **outside** the repo (`~/mesell-db-backups/`) and are never git-tracked.
- This safeguard is **local dev only** — it never reaches the cluster or GCP, and incurs
  **zero cloud spend**.

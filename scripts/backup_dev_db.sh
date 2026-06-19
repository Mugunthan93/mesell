#!/usr/bin/env bash
#
# backup_dev_db.sh — Daily versioned backup of the LOCAL dev Postgres (meesell).
#
# Owner:   meesell-infra-builder
# Context: The local dev DB (`meesell` on localhost:5432, Postgres 16) was once
#          wiped by a test run with NO backup. This script makes a daily, versioned,
#          RESTORABLE backup of BOTH schema AND data so that never causes data loss again.
#
# Governing playbook rules:
#   - INFRASTRUCTURE_PLAYBOOK.md §5.3 (Postgres backup via pg_dump)
#   - INFRASTRUCTURE_PLAYBOOK.md §10  (secret discipline — never echo/commit the DB password)
#
# SCOPE: LOCAL dev DB ONLY. This script NEVER touches the K3s cluster, the prod/staging
#        DBs, or any GCP resource. No cloud spend.
#
# Dumps live OUTSIDE the repo (~/mesell-db-backups/) so they are never committed to git.
#
# Safe to run manually any time. Idempotent.
#
#   Manual run:   bash scripts/backup_dev_db.sh
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# Repo root = parent of the directory holding this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV_FILE="${MESELL_ENV_FILE:-${REPO_ROOT}/backend/.env}"

BACKUP_DIR="${MESELL_BACKUP_DIR:-${HOME}/mesell-db-backups}"
LOG_FILE="${BACKUP_DIR}/backup.log"

DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="meesell"
DB_USER="meesell"

# Retention policy:
#   - keep the last 14 DAILY dumps (delete older daily dumps)
#   - additionally preserve WEEKLY dumps (taken on Sunday) for ~8 weeks (56 days)
KEEP_DAILY=14
WEEKLY_RETENTION_DAYS=56

# Ensure Homebrew's postgresql@16 client (pg_dump/pg_restore) is on PATH even
# under launchd's minimal environment.
export PATH="/opt/homebrew/opt/postgresql@16/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"

# ---------------------------------------------------------------------------
# Logging helper (never logs secrets)
# ---------------------------------------------------------------------------
log() {
  local msg="$1"
  local line
  line="$(date '+%Y-%m-%d %H:%M:%S') | ${msg}"
  echo "${line}"
  echo "${line}" >> "${LOG_FILE}"
}

fail() {
  log "ERROR: $1"
  exit 1
}

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}" 2>/dev/null || true

command -v pg_dump >/dev/null 2>&1 || fail "pg_dump not found on PATH"

[ -f "${ENV_FILE}" ] || fail "env file not found: ${ENV_FILE}"

# Extract the DB password from DATABASE_URL WITHOUT echoing it.
# DATABASE_URL form: postgresql+asyncpg://meesell:<password>@localhost:5432/meesell
# We grab the substring between "meesell:" and "@". This value is NEVER printed.
DB_PASSWORD="$(
  grep -E '^DATABASE_URL=' "${ENV_FILE}" \
    | head -1 \
    | sed -E 's|^DATABASE_URL=[^/]*//[^:]+:([^@]*)@.*$|\1|'
)"
[ -n "${DB_PASSWORD}" ] || fail "could not parse DB password from DATABASE_URL in ${ENV_FILE}"

# libpq reads PGPASSWORD from the environment — no password on the command line,
# nothing written to shell history, nothing logged.
export PGPASSWORD="${DB_PASSWORD}"
# Defensive: scrub from this shell as soon as pg_dump has it (done at end via trap).
unset DB_PASSWORD
trap 'unset PGPASSWORD 2>/dev/null || true' EXIT

CONN="postgresql://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------
TS="$(date '+%Y%m%d_%H%M%S')"
DUMP_FILE="${BACKUP_DIR}/meesell_dev_${TS}.dump"   # custom-format, restorable (-Fc)
SQL_FILE="${BACKUP_DIR}/meesell_dev_${TS}.sql"      # plain SQL, human-readable (optional)

log "=== backup start (db=${DB_NAME} host=${DB_HOST}:${DB_PORT}) ==="

# Sanity: confirm we can reach the DB and capture the categories count (known-good signal).
CAT_COUNT="$(psql "${CONN}" -tAc 'SELECT count(*) FROM categories;' 2>/dev/null || echo 'NA')"

# 1) Custom-format archive (schema + data, restorable via pg_restore). This is the
#    authoritative backup. -Fc is compressed and supports selective/clean restore.
pg_dump "${CONN}" -Fc --no-owner --no-privileges -f "${DUMP_FILE}" \
  || fail "pg_dump (-Fc) failed"

# 2) Plain .sql (best-effort convenience copy; not load-bearing). If it fails we keep going.
pg_dump "${CONN}" --no-owner --no-privileges -f "${SQL_FILE}" 2>/dev/null \
  || log "WARN: plain .sql dump failed (non-fatal; -Fc archive is the authoritative backup)"

[ -s "${DUMP_FILE}" ] || fail "dump file is empty: ${DUMP_FILE}"

DUMP_SIZE="$(du -h "${DUMP_FILE}" | cut -f1)"
log "OK: ${DUMP_FILE##*/} size=${DUMP_SIZE} categories=${CAT_COUNT}"

# ---------------------------------------------------------------------------
# Rotation
# ---------------------------------------------------------------------------
# Daily rotation: keep the newest ${KEEP_DAILY} *.dump archives, but NEVER delete a
# Sunday (weekly) dump that is still within the weekly retention window.
#
# Weekly dumps are identified by their date stamp landing on a Sunday. We protect
# any *.dump whose date is a Sunday AND is newer than ${WEEKLY_RETENTION_DAYS} days.

is_sunday() {
  # arg: YYYYMMDD ; returns 0 if that date is a Sunday
  local d="$1"
  local dow
  # macOS/BSD date
  dow="$(date -j -f '%Y%m%d' "${d}" '+%u' 2>/dev/null || echo '')"
  [ "${dow}" = "7" ]
}

now_epoch="$(date '+%s')"
weekly_cutoff_epoch="$(( now_epoch - WEEKLY_RETENTION_DAYS * 86400 ))"

# List dump archives newest-first. (Portable to bash 3.2 — macOS /bin/bash — which
# lacks `mapfile`; we iterate the `ls -1t` output line by line instead.)
idx=0
deleted=0
protected_weeklies=0
while IFS= read -r f; do
  [ -n "${f}" ] || continue
  idx=$((idx + 1))
  base="$(basename "${f}")"
  # filename: meesell_dev_YYYYMMDD_HHMMSS.dump
  datestamp="$(echo "${base}" | sed -E 's/^meesell_dev_([0-9]{8})_.*$/\1/')"

  if [ "${idx}" -le "${KEEP_DAILY}" ]; then
    continue   # within the last 14 — keep
  fi

  # Beyond the daily window. Protect Sunday dumps within the weekly retention window.
  if is_sunday "${datestamp}"; then
    file_epoch="$(date -j -f '%Y%m%d' "${datestamp}" '+%s' 2>/dev/null || echo 0)"
    if [ "${file_epoch}" -ge "${weekly_cutoff_epoch}" ]; then
      protected_weeklies=$((protected_weeklies + 1))
      continue   # weekly dump, still in retention — keep
    fi
  fi

  rm -f "${f}"
  # Also remove the sibling .sql for the same timestamp, if present.
  rm -f "${f%.dump}.sql"
  deleted=$((deleted + 1))
done < <(ls -1t "${BACKUP_DIR}"/meesell_dev_*.dump 2>/dev/null || true)

log "rotation: kept_daily<=${KEEP_DAILY} protected_weeklies=${protected_weeklies} deleted=${deleted}"
log "=== backup done ==="

exit 0

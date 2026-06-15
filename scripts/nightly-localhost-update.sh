#!/bin/bash
#
# nightly-localhost-update.sh — auto-update the founder's localhost preview to latest develop.
#
# Owner: meesell-infra-builder (Infra Lead). Local-dev tooling only — ₹0, no cloud, no secrets.
#
# WHAT IT DOES (once a night, driven by launchd at 01:00):
#   If — and ONLY if — the master working tree is on a CLEAN `develop`, it fast-forwards
#   to origin/develop, rebuilds the frontend with the MEMORY-SAFE static path, and restarts
#   the static preview servers (4200–4206). So the founder wakes up to the merged work.
#
# WHY THE GUARDS (this runs DURING active multi-session recovery work):
#   The master checkout is frequently parked on a feature branch (e.g. feature/section-3/*)
#   or left dirty mid-edit. In that state this job MUST be a strict NO-OP: it never switches
#   branches, never stashes, never resets, never merges, never force-pulls. It only ever
#   fast-forwards a clean develop. Anything else → log a SKIP and exit 0.
#
# It NEVER touches any /tmp/mesell-wt/section-* (or any other) worktree.
#
# Manual test:   bash scripts/nightly-localhost-update.sh
# Log:           tail -f logs/nightly-localhost-update.log
#
set -uo pipefail

# ─── Fixed paths (launchd has a minimal env; never rely on cwd or login PATH) ──────────────
REPO="/Users/mugunthansrinivasan/Project/mesell"
LOG_DIR="${REPO}/logs"
LOG="${LOG_DIR}/nightly-localhost-update.log"
FRONTEND="${REPO}/frontend"
# PGID of the detached serve-static process group, so we can stop the previous run cleanly.
SERVE_PGID_FILE="${LOG_DIR}/.serve-static.pgid"
SERVE_LOG="${LOG_DIR}/serve-static.out"

# Make git / node / pnpm resolvable under launchd's minimal environment.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

mkdir -p "${LOG_DIR}"

ts() { date '+%Y-%m-%d %H:%M:%S %z'; }
log() { echo "[$(ts)] $*" >>"${LOG}"; }

log "=== nightly-localhost-update START (pid $$) ==="

# ─── Move into the master checkout. Never operate from a worktree. ─────────────────────────
cd "${REPO}" || { log "FATAL: cannot cd ${REPO} — exit 1"; exit 1; }

# ─── GUARD 1: must be on develop. If not, do NOTHING (no checkout, no switch). ─────────────
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
if [ "${BRANCH}" != "develop" ]; then
  log "SKIP: master tree on '${BRANCH}', not develop. No-op. === END ==="
  exit 0
fi

# ─── GUARD 2: tracked working tree must be clean. (Untracked files are ignored — they don't
#             block a fast-forward and are common during active dev.) ───────────────────────
DIRTY="$(git status --porcelain --untracked-files=no)"
if [ -n "${DIRTY}" ]; then
  log "SKIP: working tree dirty (tracked changes present). No-op. === END ==="
  exit 0
fi

# ─── Fetch + fast-forward ONLY. Never force, reset, or merge. ──────────────────────────────
PRE_SHA="$(git rev-parse HEAD 2>/dev/null)"
log "On clean develop @ ${PRE_SHA}. Fetching origin…"
if ! git fetch origin --quiet; then
  log "SKIP: git fetch origin failed (offline?). No-op. === END ==="
  exit 0
fi

if ! git pull --ff-only origin develop >>"${LOG}" 2>&1; then
  log "SKIP: not a clean fast-forward (develop diverged / non-ff). No-op, tree untouched. === END ==="
  exit 0
fi

POST_SHA="$(git rev-parse HEAD 2>/dev/null)"
if [ "${PRE_SHA}" = "${POST_SHA}" ]; then
  log "Already up to date @ ${POST_SHA}. No rebuild needed. === END ==="
  exit 0
fi
log "Fast-forwarded develop: ${PRE_SHA} → ${POST_SHA}. Rebuilding preview…"

# ─── Stop the previous static-serve process group (idempotent restart). ────────────────────
if [ -f "${SERVE_PGID_FILE}" ]; then
  OLD_PGID="$(cat "${SERVE_PGID_FILE}" 2>/dev/null || true)"
  if [ -n "${OLD_PGID:-}" ] && kill -0 "-${OLD_PGID}" 2>/dev/null; then
    log "Stopping previous serve-static process group (pgid ${OLD_PGID})…"
    kill -TERM "-${OLD_PGID}" 2>/dev/null || true
    sleep 3
    kill -KILL "-${OLD_PGID}" 2>/dev/null || true
  fi
  rm -f "${SERVE_PGID_FILE}"
fi

# ─── MEMORY-SAFE static build (watchdog, one app at a time). NEVER start:all / 7×ng-serve. ──
cd "${FRONTEND}" || { log "FATAL: cannot cd ${FRONTEND} — exit 1"; exit 1; }
log "Building frontend (pnpm run dev:build-static — memory-safe watchdog)…"
if ! pnpm run dev:build-static >>"${LOG}" 2>&1; then
  log "ERROR: dev:build-static failed. Preview NOT restarted (last good build still on disk). === END ==="
  exit 1
fi
log "Static build OK."

# ─── Relaunch the 7 static servers detached, in their own process group, so they survive
#     after launchd's invocation exits and we can stop them next run via the PGID. ──────────
log "Starting static preview servers (4200–4206) detached…"
: >"${SERVE_LOG}"
setsid bash -c "cd '${FRONTEND}' && exec pnpm run dev:serve-static" >>"${SERVE_LOG}" 2>&1 &
SERVE_PID=$!
# The setsid child is its own session/group leader; its PGID == its PID.
echo "${SERVE_PID}" >"${SERVE_PGID_FILE}"
sleep 4
if kill -0 "${SERVE_PID}" 2>/dev/null; then
  log "Preview servers started (pgid ${SERVE_PID}). Open http://localhost:4200 — log: ${SERVE_LOG}"
  log "=== nightly-localhost-update DONE @ ${POST_SHA} === END ==="
  exit 0
else
  log "ERROR: serve-static did not stay up (port in use? see ${SERVE_LOG}). === END ==="
  rm -f "${SERVE_PGID_FILE}"
  exit 1
fi

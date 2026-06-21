#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# warn-low-ram-build.sh  —  PreToolUse(Bash) WARN-ONLY hook
#
# Adoption Step 2B (docs/dev/LIFECYCLE_HOOKS.md / CLAUDE_FEATURE_ADOPTION.md
# §"Lifecycle hooks"). The 8GB dev box deadlocks when a heavy esbuild/ng build
# fires while memory is already tight. This hook is a MECHANICAL SPEED BUMP: it
# prints a stderr warning when a heavy build command is about to run on low RAM
# or high swap, nudging toward the serialized meesell-env single-build path.
#
# Contract (Claude Code PreToolUse hook):
#   - stdin  : JSON with .tool_input.command and .cwd
#   - stderr : human-readable warning (advisory only)
#   - stdout : {"decision":"allow"}   ALWAYS
#
# SAFETY: WARN-ONLY + FAIL-OPEN. Any parse error, missing tool, or unexpected
# input → still emit allow / exit 0. This hook MUST NEVER block, deny, or wedge a
# session. A buggy blocking hook breaks every tool call, so warn-only is mandatory.
# ──────────────────────────────────────────────────────────────────────────────

allow() { printf '{"decision":"allow"}\n'; exit 0; }

# --- read + parse input (fail-open on any error) ------------------------------
input="$(cat 2>/dev/null)" || allow
if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)" || cmd=""
else
  cmd=""
fi
[ -n "$cmd" ] || allow

# --- only react to heavy build commands ---------------------------------------
case "$cmd" in
  *"ng build"*|*"ng serve"*|*esbuild*|*"npm run build"*|*webpack*|*"baseline up"*) : ;;
  *) allow ;;
esac

# --- compute available RAM (MB) + swap usage (%) — macOS, fail-open -----------
# available = (free + inactive + speculative) * pagesize
avail_mb=""
swap_pct=""

if command -v vm_stat >/dev/null 2>&1 && command -v sysctl >/dev/null 2>&1; then
  pagesize="$(sysctl -n hw.pagesize 2>/dev/null)"
  case "$pagesize" in ''|*[!0-9]*) pagesize="" ;; esac
  if [ -n "$pagesize" ]; then
    vmout="$(vm_stat 2>/dev/null)"
    pfree="$(printf '%s' "$vmout"      | awk '/Pages free/         {gsub(/\./,"",$3); print $3}')"
    pinact="$(printf '%s' "$vmout"     | awk '/Pages inactive/     {gsub(/\./,"",$3); print $3}')"
    pspec="$(printf '%s' "$vmout"      | awk '/Pages speculative/  {gsub(/\./,"",$3); print $3}')"
    case "$pfree"  in ''|*[!0-9]*) pfree=0  ;; esac
    case "$pinact" in ''|*[!0-9]*) pinact=0 ;; esac
    case "$pspec"  in ''|*[!0-9]*) pspec=0  ;; esac
    pages=$((pfree + pinact + pspec))
    # guard against bogus zero (parse miss) — only compute if we got pages
    if [ "$pages" -gt 0 ] 2>/dev/null; then
      avail_mb=$(( pages * pagesize / 1048576 ))
    fi
  fi

  swapline="$(sysctl vm.swapusage 2>/dev/null)"
  if [ -n "$swapline" ]; then
    # vm.swapusage: total = 2048.00M  used = 1195.94M  free = 852.06M
    total="$(printf '%s' "$swapline" | sed -n 's/.*total = \([0-9.]*\)M.*/\1/p')"
    used="$(printf '%s'  "$swapline" | sed -n 's/.*used = \([0-9.]*\)M.*/\1/p')"
    if [ -n "$total" ] && [ -n "$used" ]; then
      # integer percent via awk; guard div-by-zero
      swap_pct="$(awk -v t="$total" -v u="$used" 'BEGIN{ if (t+0>0) printf "%d", (u/t)*100; else print "" }' 2>/dev/null)"
    fi
  fi
fi

# --- decide whether to warn (thresholds: <1500MB avail OR >70% swap) ----------
warn=0
if [ -n "$avail_mb" ] && [ "$avail_mb" -lt 1500 ] 2>/dev/null; then
  warn=1
fi
if [ -n "$swap_pct" ] && [ "$swap_pct" -gt 70 ] 2>/dev/null; then
  warn=1
fi

if [ "$warn" -eq 1 ]; then
  printf '⚠️  warn-low-ram-build: heavy build on low memory (available=%sMB, swap=%s%%). Prefer meesell-env serialized builds, one at a time — never run concurrent ng/esbuild on the 8GB box. See docs/dev/ENV_MANAGER.md.\n' \
    "${avail_mb:-?}" "${swap_pct:-?}" >&2
fi

allow

#!/usr/bin/env bash
# SessionStart WARN-ONLY guard: flag any agent-memory MEMORY.md that has drifted back
# to holding INLINE PROSE instead of staying a lean index (per
# docs/dev/MEMORY_INDEX_CONVENTION.md). Closes the docs/GIT_WORKFLOW.md W10 deferred
# gap (memory compaction/rotation). It is the prevention layer so the PR #493 bulk
# restructure never has to be repeated by hand.
#
# NEVER blocks, NEVER errors out a session: always exit 0, fail-open on any problem.
# Companion to heal-agent-memory-perms.sh (same SessionStart slot, same exit-0 ethos).
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
[ -n "$root" ] || exit 0
base="$root/.claude/agent-memory"
[ -d "$base" ] || exit 0

# Thresholds (overridable). prose = inline-prose lines; lines = total-lines backstop.
PROSE_MAX="${MESELL_MEM_PROSE_MAX:-120}"
LINES_MAX="${MESELL_MEM_LINES_MAX:-300}"
IDENTITY_SKIP="${MESELL_MEM_IDENTITY_SKIP:-12}"

# Targets: every meesell-* role MEMORY.md + the nexus director's.
shopt -s nullglob 2>/dev/null || true
targets=()
for d in "$base"/meesell-*/ "$base"/nexus-level-0-director/; do
  f="${d}MEMORY.md"
  [ -f "$f" ] && targets+=("$f")
done
[ "${#targets[@]}" -gt 0 ] || exit 0

# A line is INLINE PROSE iff (beyond the identity preamble) it is non-blank and is NOT
# a heading (^#), a blockquote note (^>), or an index entry (a list bullet carrying a
# markdown link "](" — an optional leading "⭐" marker is tolerated). Tables, code dumps
# and prose bullets all count as prose: they belong in mem/ detail files.
offenders=""
count=0
for f in "${targets[@]}"; do
  read -r prose total < <(
    awk -v idn="$IDENTITY_SKIP" '
      { tot=NR; line=$0; sub(/[ \t]+$/,"",line) }
      NR<=idn {next}
      line=="" {next}
      line ~ /^#/ {next}
      line ~ /^[ \t]*>/ {next}
      (line ~ /^[ \t]*[-*][ \t]/ && line ~ /\]\(/) {next}
      {c++}
      END{print c+0, tot+0}
    ' "$f" 2>/dev/null
  ) || continue
  : "${prose:=0}" "${total:=0}"
  case "$prose$total" in *[!0-9]*) continue ;; esac
  if [ "$prose" -gt "$PROSE_MAX" ] || [ "$total" -gt "$LINES_MAX" ]; then
    role="$(basename "$(dirname "$f")")"
    offenders+="  ${role}: ${prose} prose lines / ${total} total"$'\n'
    count=$((count + 1))
  fi
done

if [ "$count" -gt 0 ]; then
  {
    printf '⚠️  agent-memory: %d MEMORY.md file(s) holding inline prose — migrate per docs/dev/MEMORY_INDEX_CONVENTION.md:\n' "$count"
    printf '%s' "$offenders"
    printf 'Remediate (each agent migrates ITS OWN file): tools/agent_memory/restructure_mem.py <MEMORY.md> [--apply] then tools/agent_memory/verify_mem.py <role> — see tools/agent_memory/README.md. Thresholds: prose>%s or total>%s (override MESELL_MEM_PROSE_MAX / MESELL_MEM_LINES_MAX).\n' "$PROSE_MAX" "$LINES_MAX"
  } >&2
fi
exit 0

#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# guard-master-tree-git.sh  —  PreToolUse(Bash) guard
#
# ROOT-CAUSE FIX for the recurring "session overrode the master tree" incidents
# (2026-06-15 section-3, 2026-06-16 ui-ds-phase0). Sessions/sub-agents sometimes
# run `git checkout <branch>` / `git commit` directly in the MeeSell MASTER
# working tree instead of an isolated worktree, flipping the founder's editor
# branch and layering commits/uncommitted work onto the wrong place.
#
# Convention (SECTION_DISPATCH_PROTOCOL.md §0 R1–R5) could not stop this because
# it relies on every actor reading + obeying. This hook makes it MECHANICAL:
# the harness runs it before every Bash call and BLOCKS the dangerous git ops
# when they target the master tree.
#
# Contract (Claude Code PreToolUse hook):
#   - stdin  : JSON with .tool_input.command and .cwd
#   - stdout : {"decision":"allow"}  or  {"decision":"block","reason":"..."}
#
# DESIGN: FAIL-OPEN. Any uncertainty, parse error, missing jq, unmatched shape →
# emit allow. A guard bug must never brick sessions; the worst case is we fail to
# block (degrading to today's behavior), never that we block legitimate work.
# ──────────────────────────────────────────────────────────────────────────────

MASTER="/Users/mugunthansrinivasan/Project/mesell"

allow() { printf '{"decision":"allow"}\n'; exit 0; }

# --- read + parse input (fail-open on any error) ------------------------------
input="$(cat 2>/dev/null)" || allow
command -v jq >/dev/null 2>&1 || allow
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)" || allow
cwd="$(printf '%s' "$input" | jq -r '.cwd // ""'                2>/dev/null)" || allow
[ -n "$cmd" ] || allow

# --- explicit, deliberate override for rare Director/founder recovery ----------
case "$cmd" in
  *MESELL_ALLOW_MASTER_GIT=1*) allow ;;
esac

# --- does this command operate on the MASTER tree? -----------------------------
# Precedence: an explicit `git -C <path>` or a `cd <path>` in the command
# overrides the session cwd. A redirect into a worktree means "not master".
targets_master=0
redirected=0

# git -C <master>  → master ;  git -C <other> → not master
if printf '%s' "$cmd" | grep -Eq "git[[:space:]]+-C[[:space:]]+\"?${MASTER}/?\"?([[:space:]]|$)"; then
  targets_master=1; redirected=1
elif printf '%s' "$cmd" | grep -Eq "git[[:space:]]+-C[[:space:]]"; then
  redirected=1   # git -C somewhere-else → not the master tree
fi

# cd into a worktree → not master ;  cd into master (and not later into a wt) → master
if [ "$redirected" -eq 0 ]; then
  if printf '%s' "$cmd" | grep -Eq "cd[[:space:]]+\"?((/private)?/tmp/mesell-wt/|${MASTER}/\.claude/worktrees/)"; then
    redirected=1   # cd into a worktree
  elif printf '%s' "$cmd" | grep -Eq "cd[[:space:]]+\"?${MASTER}/?\"?([[:space:]]|;|&|$)"; then
    targets_master=1; redirected=1
  fi
fi

# no explicit redirect → fall back to the session cwd
if [ "$redirected" -eq 0 ]; then
  case "$cwd" in
    "$MASTER"|"$MASTER/") targets_master=1 ;;
  esac
fi

[ "$targets_master" -eq 1 ] || allow

# --- in the master tree: classify the git op -----------------------------------
# `gitpre` matches `git` followed by any leading GLOBAL options (-C <path>,
# -c <kv>, --no-pager, --git-dir=, --work-tree=) so that e.g.
# `git -C <master> checkout x` is classified the same as `git checkout x`.
glob='(-C[[:space:]]+[^[:space:]]+|-c[[:space:]]+[^[:space:]]+|--no-pager|-p|--git-dir=[^[:space:]]+|--work-tree=[^[:space:]]+)'
gitpre="git[[:space:]]+(${glob}[[:space:]]+)*"
reason=""

# branch CREATION in the master tree → always forbidden
if printf '%s' "$cmd" | grep -Eq "${gitpre}(checkout[[:space:]]+-b|switch[[:space:]]+(-c|--create))([[:space:]]|$)"; then
  reason="creating a branch in the master checkout"
fi

# branch SWITCH: allow only to the protected bases (develop|main); allow file-restore
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -Eq "${gitpre}(checkout|switch)([[:space:]]|$)"; then
  if printf '%s' "$cmd" | grep -Eq "${gitpre}checkout([[:space:]].*)?[[:space:]]--([[:space:]]|$)"; then
    :  # `git checkout [<ref>] -- <path>` = file restore, allowed
  elif printf '%s' "$cmd" | grep -Eq "${gitpre}(checkout|switch)[[:space:]]+(-[[:alnum:]]+[[:space:]]+)*(develop|main)([[:space:]]|$)"; then
    :  # switching the master tree onto its protected base, allowed
  else
    reason="switching the master checkout onto a feature branch"
  fi
fi

# commits / merges / history rewrites in the master tree
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -Eq "${gitpre}(commit|merge|rebase|cherry-pick|am|revert)([[:space:]]|$)"; then
  reason="committing/merging in the master checkout"
fi
# staging the index in the master tree
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -Eq "${gitpre}add([[:space:]]|$)"; then
  reason="staging changes in the master checkout"
fi
# destructive resets / force branch moves in the master tree
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -Eq "${gitpre}reset[[:space:]]+(--hard|--merge|--keep)([[:space:]]|$)"; then
  reason="hard-resetting the master checkout"
fi
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -Eq "${gitpre}branch[[:space:]]+(-[[:alnum:]]*[fDM])([[:space:]]|$)"; then
  reason="force-moving/deleting a branch from the master checkout"
fi

if [ -n "$reason" ]; then
  # Block. Keep the reason single-line JSON-safe (no embedded quotes/newlines).
  printf '{"decision":"block","reason":"BLOCKED by guard-master-tree-git: %s. The MeeSell master checkout (%s) must stay on develop/main and never take a session branch-switch or commit — that is what corrupted the founder editor on 2026-06-15 and 2026-06-16. Do the work in a worktree instead: git worktree add -b <branch> /tmp/mesell-wt/<name> origin/develop  then  cd into it. Deliberate Director/founder recovery: prefix the command with MESELL_ALLOW_MASTER_GIT=1 ."}\n' \
    "$reason" "$MASTER"
  exit 0
fi

allow

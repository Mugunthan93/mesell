#!/usr/bin/env bash
# Test matrix for guard-master-tree-git.sh. Run: bash guard-master-tree-git.test.sh
# Exits non-zero if any case fails. NO network, NO git mutation — pure stdin/stdout.

HOOK="$(dirname "$0")/guard-master-tree-git.sh"
MASTER="/Users/mugunthansrinivasan/Project/mesell"
WT="/private/tmp/mesell-wt/some-feature"
pass=0; fail=0

# run <expected: allow|block> <cwd> <command>
run() {
  local expect="$1" cwd="$2" cmd="$3"
  local input out got
  input="$(jq -nc --arg c "$cmd" --arg w "$cwd" '{tool_name:"Bash",tool_input:{command:$c},cwd:$w}')"
  out="$(printf '%s' "$input" | bash "$HOOK" 2>/dev/null)"
  case "$out" in
    *'"block"'*) got="block" ;;
    *'"allow"'*) got="allow" ;;
    *)           got="malformed:$out" ;;
  esac
  if [ "$got" = "$expect" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1)); printf 'FAIL  expected=%-5s got=%-5s  cwd=%s  cmd=%s\n' "$expect" "$got" "$cwd" "$cmd"
  fi
}

echo "── MUST BLOCK (master tree, contaminating ops) ──"
run block "$MASTER" "git checkout -b feature/x"
run block "$MASTER" "git checkout feat/ui-ds-phase0"
run block "$MASTER" "git switch some-feature"
run block "$MASTER" "git switch -c new-thing"
run block "$MASTER" "git commit -m 'wip'"
run block "$MASTER" "git commit -am 'wip'"
run block "$MASTER" "git add ."
run block "$MASTER" "git add -A"
run block "$MASTER" "git merge origin/develop"
run block "$MASTER" "git rebase develop"
run block "$MASTER" "git reset --hard HEAD"
run block "$MASTER" "git branch -D somebranch"
run block "$MASTER" "git branch -f main HEAD"
run block "$MASTER" "git cherry-pick abc123"
run block "$MASTER" "cd $MASTER && git checkout feature/y"
# explicit git -C master from elsewhere
run block "$WT"     "git -C $MASTER checkout feature/z"

echo "── MUST ALLOW (master tree, safe ops) ──"
run allow "$MASTER" "git checkout develop"
run allow "$MASTER" "git checkout main"
run allow "$MASTER" "git switch develop"
run allow "$MASTER" "git checkout -- frontend/app.ts"
run allow "$MASTER" "git checkout develop -- some/file.ts"
run allow "$MASTER" "git worktree add -b feature/x /tmp/mesell-wt/x origin/develop"
run allow "$MASTER" "git worktree remove /tmp/mesell-wt/x"
run allow "$MASTER" "git fetch origin develop"
run allow "$MASTER" "git -c pull.rebase=false pull --ff-only origin develop"
run allow "$MASTER" "git status -sb"
run allow "$MASTER" "git log --oneline -5"
run allow "$MASTER" "git stash push -u -m 'preserve'"
run allow "$MASTER" "git branch --show-current"
run allow "$MASTER" "ls -la && npm install"
run allow "$MASTER" "gh pr merge 262 --merge"
# deliberate override
run allow "$MASTER" "MESELL_ALLOW_MASTER_GIT=1 git checkout feature/recovery"

echo "── MUST ALLOW (inside a worktree — guard is master-tree-only) ──"
run allow "$WT" "git checkout -b feature/anything"
run allow "$WT" "git commit -m 'work'"
run allow "$WT" "git add ."
run allow "$WT" "git reset --hard HEAD"
# cd into a worktree from master cwd → not master
run allow "$MASTER" "cd /tmp/mesell-wt/x && git checkout -b feature/q"
run allow "$MASTER" "git -C /private/tmp/mesell-wt/x commit -m 'ok'"

echo
echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ]

# Lifecycle Hooks (adoption step 2B)

Three **warn-only** `PreToolUse(Bash)` hooks that add mechanical speed bumps to the
three highest-cost failure modes on the MeeSell dev box. See
`docs/dev/CLAUDE_FEATURE_ADOPTION.md` §"Lifecycle hooks" (item in §3.x / §4 quick
wins / §5 adoption-sequence step 2) for the rationale: an 8GB box that deadlocks on
parallel builds, a solo founder who is the only reviewer, and a 0-required-review
pipeline where PRs have landed via `--admin` unreviewed.

## Status: WARN-ONLY + currently INERT

- **WARN-ONLY** — every hook prints an advisory to **stderr** and **always** emits
  `{"decision":"allow"}` / exits `0`. None of them ever blocks, denies, or errors in
  a way that could wedge a session. They are nudges, not gates. A buggy *blocking*
  hook can break every single tool call, so warn-only is mandatory here.
- **FAIL-OPEN** — on any parse error, missing tool (`jq`, `vm_stat`, `sysctl`,
  `awk`), or unexpected input shape, each hook still emits `allow` / exits `0`.
- **INERT** — the scripts live in `.claude/hooks/` but `.claude/settings.json` was
  **NOT** modified. None of these hooks runs in any session until the founder
  deliberately wires it in (snippets below). Enable **one at a time** and reload the
  session after each.

The hooks match the existing PreToolUse contract used by
`.claude/hooks/guard-master-tree-git.sh`: stdin is JSON with `.tool_input.command`
and `.cwd`; stdout is `{"decision":"allow"}`.

## The three hooks

### 1. `warn-low-ram-build.sh`
- **Matcher:** `Bash`
- **Triggers on:** `ng build`, `ng serve`, `esbuild`, `npm run build`, `webpack`,
  `baseline up`.
- **Warns when:** available RAM `< 1500 MB` **OR** swap usage `> 70 %`.
- **Computation (macOS):** available = `(Pages free + inactive + speculative) ×
  hw.pagesize` from `vm_stat`; swap% = `used / total` from `vm.swapusage`.
- **Message:** nudges toward serialized `meesell-env` single-build path
  (`docs/dev/ENV_MANAGER.md`) — never run concurrent ng/esbuild on the 8GB box.

### 2. `warn-admin-merge.sh`
- **Matcher:** `Bash`
- **Triggers on:** `gh pr merge … --admin` (verb + `--admin` flag, any order).
- **Message:** reminder that `--admin` bypasses CI + required review; confirm the
  merge is founder-authorized and the `/meesell-code-review` gate was run
  (`docs/dev/REVIEW_GATES.md`).

### 3. `warn-infra-dryrun.sh`
- **Matcher:** `Bash`
- **Triggers on:** `kubectl apply`, `terraform apply`, `helm upgrade`,
  `helm install` **without** any `--dry-run` flag.
- **Message:** per `INFRASTRUCTURE_PLAYBOOK`, run a dry-run first
  (`kubectl apply --dry-run=server` / `kubectl diff` / `terraform plan` /
  `helm upgrade --dry-run`) and verify the diff before mutating the cluster.

## How to enable (founder, deliberate)

Add the relevant entry to the `hooks.PreToolUse` array in `.claude/settings.json`.
The `Bash` matcher already exists (it runs `guard-master-tree-git.sh`); you may add
another `command` to that same matcher's `hooks` array, **or** add a new matcher
block. Below each hook is shown as its own block for clarity. Enable **one at a
time** and reload the session after each so a typo can't take out all tool calls at
once.

```jsonc
// .claude/settings.json  →  hooks.PreToolUse  (append these blocks)

// 1. low-RAM build warning
{
  "matcher": "Bash",
  "hooks": [
    { "type": "command",
      "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/warn-low-ram-build.sh\"" }
  ]
},

// 2. admin-merge reminder
{
  "matcher": "Bash",
  "hooks": [
    { "type": "command",
      "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/warn-admin-merge.sh\"" }
  ]
},

// 3. infra dry-run warning
{
  "matcher": "Bash",
  "hooks": [
    { "type": "command",
      "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/warn-infra-dryrun.sh\"" }
  ]
}
```

If you prefer to fold them into the **existing** `Bash` matcher block alongside
`guard-master-tree-git.sh`, append the `command` objects to that block's `hooks`
array instead — all `PreToolUse` Bash hooks run and their decisions combine; since
these three always return `allow`, they never change the decision, only emit stderr.

## Self-test

Each script is pure stdin→stdout with no network or git mutation. To exercise one:

```bash
jq -nc --arg c "ng build mfe-catalog" --arg w "/tmp" \
  '{tool_input:{command:$c},cwd:$w}' \
  | bash .claude/hooks/warn-low-ram-build.sh
# stdout: {"decision":"allow"}   stderr: warning iff RAM<1500MB or swap>70%
```

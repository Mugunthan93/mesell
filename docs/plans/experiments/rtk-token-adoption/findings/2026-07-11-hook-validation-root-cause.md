# Finding — "Hook JSON output validation failed — (root): Invalid input" root cause

**Date:** 2026-07-11
**Session:** `mesell-hook-json-schema-migration-infra-session-1`
**Severity:** low (noise / broken guard behaviour, no data loss)

## Symptom

Recurring runtime error surfaced on Bash and Agent tool calls:

```
Hook JSON output validation failed — (root): Invalid input
```

The suspicion was that RTK (Rust Token Killer, the token-adoption experiment) had
re-armed its `rtk hook claude` Bash hook and was emitting a bad shape.

## RTK exoneration (verified)

- RTK is **disarmed everywhere**: `rtk init --show` reports `Hook: not found`;
  no `rtk hook` key present in any `settings.json` scope.
- All settings scopes are **valid JSON** and the pre-install snapshot at
  `~/.claude-backups/rtk-exp-2026-07-11/settings.json` restores byte-identical.
- RTK never appears in the offending output — it is not the emitter. EXONERATED.

## Real root cause

**Our own hooks emit the LEGACY hook-protocol JSON.** Per the current schema
(code.claude.com/docs/en/hooks.md) a PreToolUse hook must return:

```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow|deny|ask","permissionDecisionReason":"..."}}
```

The legacy top-level shapes we were emitting are now INVALID:
- `{"decision":"allow"}` — invalid (rejected by the validator → the error).
- `{"decision":"block","reason":"..."}` — legacy deny shape, also invalid.

Both `.claude/hooks/guard-master-tree-git.sh` and the inline `PreToolUse[Agent]`
hook in `.claude/settings.json` used these legacy shapes.

## Fix

- `guard-master-tree-git.sh`: `allow()` → **silent `exit 0`** (no stdout, neutral —
  so the normal permission flow applies; an explicit `permissionDecision:"allow"`
  would auto-approve and bypass the user's own prompts, wrong for a guard). Block
  branch → new `permissionDecision:"deny"` shape, same reason text. Contract
  comment updated.
- `settings.json` Agent hook: allow branch → no output (`:`); block branch →
  new deny shape, same reason text.

## Note

**A session restart is required** for the `settings.json` hook change to take
effect — inline hooks are read at session start. The `guard-master-tree-git.sh`
change is picked up on next invocation (the hook shells out to the file).

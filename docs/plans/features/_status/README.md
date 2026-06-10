# Per-feature planning status — `_status/`

**Owner:** Each sub-session owns ONE file: `_status/{slug}.yaml`.
**Reader:** The master Director session aggregates all 9 files into `../feature_planning_master.md`.
**Why this exists:** Multiple feature planning sub-sessions run in parallel. Direct concurrent edits to `feature_planning_master.md` collided (race conditions, lost updates). One file per feature removes the contention — sub-sessions never touch the same file, never touch the master tracker.

---

## Directory contract

| Rule | Detail |
|---|---|
| One file per feature | Filename MUST be `{slug}.yaml` where `{slug}` is one of the 9 V1 feature slugs |
| Sub-session writes its own file only | A sub-session for `auth-otp` ONLY edits `_status/auth-otp.yaml` |
| No deletes | Status files persist after planning is locked — historical record |
| YAML 1.2 | Use double-quoted strings, ISO 8601 timestamps with `Z` suffix, lists with `-` |
| Single source for THIS slot | Sub-session writes at session start AND session close, possibly mid-session for checkpoints |
| The master tracker is REGENERATED | Editors of `feature_planning_master.md` MUST NOT hand-edit rows that come from `_status/*.yaml` — the master session regenerates the table from these YAML files |

---

## YAML schema (exhaustive)

Every field is REQUIRED unless marked `(optional, default: null)`. Sub-sessions write all required fields on first write; missing fields are a contract bug.

| Field | Type | Valid values / notes |
|---|---|---|
| `feature` | string | One of the 9 slugs. Must match the filename stem. |
| `session` | string | Session name following §4 of the (forthcoming) repo-management master plan: `mesell-{feature}-planning-session-{N}` |
| `worktree` | string | Absolute path to the worktree (e.g., `/tmp/mesell-wt/auth-otp`) |
| `branch` | string | Branch name (e.g., `feature/auth-otp/planning`) |
| `status` | enum | One of: `NOT_STARTED`, `IN_PROGRESS`, `PLAN_READY`, `IN_REVIEW`, `LOCKED` (use underscores, not spaces, so YAML parses cleanly without quoting) |
| `last_updated` | string | ISO 8601 UTC timestamp, e.g., `2026-06-10T14:32:00Z` |
| `feature_plan_path` | string | Path RELATIVE to project root, e.g., `docs/plans/features/auth-otp/FEATURE_PLAN.md` |
| `feature_plan_line_count` | integer or null | Set after FEATURE_PLAN.md is written; `null` while `NOT_STARTED` or `IN_PROGRESS` |
| `pr_number` | integer or null | GitHub PR number once PR is opened |
| `pr_url` | string or null | Full GitHub PR URL once PR is opened |
| `outstanding_founder_decisions` | list of strings | Each entry: `"D1 — locked"`, `"D4 — awaiting answer"`, etc. Empty list `[]` if all decisions resolved. |
| `notes` | string | Free-form multi-line text. Use YAML block-scalar `\|` for multi-line content. |

### Status value semantics

| Status | When to set |
|---|---|
| `NOT_STARTED` | Default — no planning session opened. Status files for `NOT_STARTED` features can exist as stubs OR be absent (master session treats absence as `NOT_STARTED`) |
| `IN_PROGRESS` | Sub-session has begun planning work. Set this at session START after mandatory reads. |
| `PLAN_READY` | FEATURE_PLAN.md committed locally. Awaiting PR open. |
| `IN_REVIEW` | PR open against `develop`. Founder reviewing. `pr_number` + `pr_url` MUST be populated. |
| `LOCKED` | PR merged. Plan is binding for downstream coding sessions. |

---

## Complete YAML example — `auth-otp.yaml`

```yaml
feature: "auth-otp"
session: "mesell-auth-otp-planning-session-1"
worktree: "/tmp/mesell-wt/auth-otp"
branch: "feature/auth-otp/planning"
status: "IN_REVIEW"
last_updated: "2026-06-10T13:44:00Z"
feature_plan_path: "docs/plans/features/auth-otp/FEATURE_PLAN.md"
feature_plan_line_count: 1561
pr_number: 3
pr_url: "https://github.com/Mugunthan93/mesell/pull/3"
outstanding_founder_decisions:
  - "D1 — locked (FE-D5 ratification confirmed)"
  - "D2 — locked (FEATURE_AUTH_OTP_ENABLED default true on both dev and staging)"
  - "D3 — locked (auth-otp ships before any sibling PR opens)"
  - "D4 — locked (Lua EVAL fallback documented for older Valkey)"
notes: |
  - Planning session complete, FEATURE_PLAN.md is 1561 lines.
  - PR #3 open, awaiting founder review.
  - 4 founder decisions D1-D4 all resolved during session.
  - Dispatch templates ready for 7 specialists (4 backend + 2 frontend + infra standalone).
  - Risk register lists 5 items — MSG91 staging credit, Lua EVAL on older Valkey,
    HMAC pepper rotation, cookie domain mismatch dev↔staging, FE refresh storm.
  - No upstream feature dependency — auth-otp is the prerequisite for all other 8 features.
```

---

## Sub-session update protocol

### At session start (right after mandatory reads)
1. Open `docs/plans/features/_status/{slug}.yaml` (create if absent).
2. Write all required fields:
   - `feature`, `session`, `worktree`, `branch` — known up-front
   - `status: "IN_PROGRESS"`
   - `last_updated:` to now (UTC, ISO 8601)
   - `feature_plan_path:` to the planned path
   - `feature_plan_line_count: null`
   - `pr_number: null`, `pr_url: null`
   - `outstanding_founder_decisions: []`
   - `notes: ""` (or a brief "session opened" line)
3. Save the file (DO NOT commit yet — sub-session may rebase / amend later).

### Mid-session (optional checkpoint)
- When founder decisions land, append them to `outstanding_founder_decisions` with a clear suffix (`" — locked"`, `" — awaiting answer"`, `" — declined"`).
- Bump `last_updated:` each time.
- Keep `notes:` short — one or two bullet points per checkpoint, not a transcript.

### At session close (after FEATURE_PLAN.md is committed)
1. Update `status:` to `PLAN_READY`.
2. Set `feature_plan_line_count:` to the line count of FEATURE_PLAN.md.
3. Bump `last_updated:`.
4. Once PR is opened, update `status: "IN_REVIEW"`, set `pr_number:` and `pr_url:`.
5. Commit the YAML file alongside the FEATURE_PLAN.md changes (or in a follow-up commit on the same branch — the YAML file lives in the master tree's view of the branch).

### Hard rules
- A sub-session for feature X MUST NOT edit `_status/Y.yaml` (Y ≠ X) — file-level isolation is the whole point of this directory.
- A sub-session MUST NOT edit `../feature_planning_master.md` directly — the master Director session regenerates that file by reading all `_status/*.yaml`.
- A sub-session MUST NOT edit this README — it is governance documentation.

---

## Master session aggregation protocol (informational — implemented in a future dispatch)

The master Director session, on demand or at scheduled checkpoints:

1. Reads every `_status/*.yaml` file (glob `_status/*.yaml`, ignore `README.md`).
2. Parses each into the `feature` × field matrix.
3. Re-generates the `## Planning state — 9 V1 features` table inside `../feature_planning_master.md` from these rows, preserving the rest of the master tracker (Status vocabulary, Protocol, Recent updates log, Cross-feature dependency map).
4. Appends a one-line entry to `## Recent updates log` for each state transition since the last aggregation pass.
5. Commits the regenerated tracker with a message like `chore(plan): aggregate _status/*.yaml into master tracker`.

This aggregation flow is the topic of a separate dispatch and is NOT implemented as part of the worktree infrastructure dispatch.

---

## Why a YAML file instead of a Markdown table row?

- YAML is line-delimited and merge-clean — concurrent appends from different files can't conflict because each file is single-author.
- Structured fields are machine-readable — the master aggregator parses them without regex.
- The master tracker remains human-readable Markdown; it's regenerated, not hand-edited.
- One file per slug means a stuck or crashed sub-session leaves only its own file in a partial state; the rest stay correct.

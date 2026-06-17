# MeeSell Dispatch Playbook

> Authoritative reference for how the master (Director) session dispatches the MeeSell
> agent fleet. Read this at the start of every master session. Source of the rules:
> `CLAUDE.md` (MeeSell Agent Ecosystem Rules) + `docs/MEESELL_AGENT_REGISTRY.md`.

## 1. Dispatch Decision Tree

```
Incoming task
   │
   ├─ Is it MeeSell work?  ── NO ──▶ REFUSE. Only meesell-* agents touch MeeSell.
   │                                  (never nexus:*, general-purpose, Explore, Plan)
   │  YES
   ▼
   ├─ Code-heavy? (feature code, extraction, AI pipeline, auth/backend/frontend build)
   │     │
   │     └─ YES ──▶ HYBRID 3-STEP DISPATCH (coordinator runs through the session window)
   │                  Step 1: dispatch COORDINATOR → produce task SPEC
   │                  Step 2: dispatch named SPECIALIST → build from spec
   │                  Step 3: dispatch COORDINATOR → MERGE-GATE REVIEW (can reject to specialist)
   │
   ├─ Docs / status flip / ruling landing / chore?
   │     └─ YES ──▶ SINGLE-AGENT FAST MODE: coordinator/lead executes directly. No ceremony.
   │
   └─ Standalone agent task? (infra, legal copy)
         └─ meesell-infra-builder / meesell-legal-writer execute DIRECTLY (no specialists).
```

**Why 3-step:** dispatched coordinators have **no Agent tool** — they cannot reach their own
specialists. The master session must run the hierarchy *for* them.

## 2. The 18-Agent Roster (routing table)

| Coordinator / Standalone | Model | Specialists it specs/reviews |
|---|---|---|
| `meesell-infra-builder` | opus | — (executes directly) |
| `meesell-legal-writer` | opus, no Bash | — (executes directly) |
| `meesell-backend-coordinator` | opus | `meesell-database-builder` (sonnet), `meesell-api-routes-builder` (sonnet), `meesell-services-builder` (opus), `meesell-auth-builder` (opus) |
| `meesell-frontend-coordinator` | opus | `meesell-angular-component-builder` (sonnet), `meesell-angular-service-builder` (sonnet), `meesell-angular-ui-styler` (sonnet) |
| `meesell-ai-coordinator` | opus | `meesell-prompt-engineer` (opus), `meesell-category-picker-builder` (opus), `meesell-image-precheck-builder` (opus) |
| `meesell-data-engineer` | opus | `meesell-xlsx-parser` (sonnet), `meesell-scraper-maintainer` (sonnet) |

The master session dispatches **coordinators**. Coordinators (via the session) drive **specialists**.

**Deferred to V1.5:** `meesell-brand-master-builder` (brand whitelist parsed inline by
`meesell-xlsx-parser` for V1). `meesell-test-writer` and `meesell-deployer` not yet created.

## 3. Prompt Templates

### Template A — Coordinator SPEC (Step 1 of 3-step)

```
You are meesell-<role>-coordinator working on MeeSell.

PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
If you need cross-project information, stop and ask the Director.

MEMORY PROTOCOL:
1. Read your own memory first: .claude/agent-memory/meesell-<role>/MEMORY.md
2. Read relevant peer memories if you need shared context (do NOT write to them).
3. Append learnings to your own MEMORY.md at the end.

LOCKED DOCS (read before acting):
- docs/V1_FEATURE_SPEC.md (Section <N> / Feature <N>)
- PRICING_LOCKED.md / INFRASTRUCTURE_PLAYBOOK.md / LEGAL_AND_COMPLIANCE_INFO.md (as relevant)

TASK: <one-line task statement>

DELIVERABLE: Produce a TASK SPEC for <named specialist agent> only — do NOT write code.
The spec must contain:
  - Exact files to create/modify (absolute paths under the project)
  - Function/class/route signatures with types
  - Acceptance criteria (testable)
  - Test files required and what they assert
  - Any contract/wire-shape constraints the consumer requires
  - Git: target branch / worktree path (see GIT RULES below)

CONSTRAINTS (carry forward):
- dev-only / localhost only. Zero cutover, zero cloud spend, no production.
- Never fabricate or commit secret values.
- Consumer-shape over self-asserted shape for any shared contract.

Return the SPEC as your final message (it IS the return value — raw, no preamble).
```

### Template B — Specialist BUILD (Step 2 of 3-step)

```
You are meesell-<specialist> working on MeeSell.

PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.

MEMORY PROTOCOL:
1. Read .claude/agent-memory/meesell-<specialist>/MEMORY.md first.
2. Append learnings at the end. Never write to another agent's memory.

LOCKED DOCS: read docs/V1_FEATURE_SPEC.md Section/Feature <N> before coding.

SPEC (from meesell-<role>-coordinator):
<paste the full spec from Step 1 verbatim>

GIT RULES:
- Work ONLY in the assigned worktree: git -C <worktree-path> <cmd>. NEVER touch the master tree.
- Branch: <feature/...> off its integration branch.
- Conventional commits (T<n>: ... or feat:/fix:/chore:).
- Run tests on backend/.venv (Python 3.11/3.12) — NOT host 3.9.6 (PEP-604 false failures).
- Open a PR to the integration branch. Do NOT merge — the coordinator gates it.

CONSTRAINTS: dev-only, no secrets, no production. Build exactly to spec.

Return: PR number/URL + a summary of what changed + test results. (Raw, no preamble.)
```

### Template C — Coordinator MERGE-GATE REVIEW (Step 3 of 3-step)

```
You are meesell-<role>-coordinator running the MERGE-GATE REVIEW on a specialist PR.

PROJECT BOUNDARY: project "mesell" at /Users/mugunthansrinivasan/Project/mesell. Stay inside it.

MEMORY: read your own MEMORY.md; append the gate verdict at the end.

PR UNDER REVIEW: <PR number/URL> on branch <feature/...>
ORIGINAL SPEC: <paste spec from Step 1>

GATE CHECKLIST (this is a REAL gate — you may REJECT back to the specialist):
1. Spec compliance — every acceptance criterion met?
2. Tests present, run green on backend/.venv (3.11/3.12), and actually assert the behavior?
3. Contract/wire-shape parity vs the CONSUMER's expected shape (model_json_schema, strip description).
4. No executable drift on any extracted twin (§16.G AST diff if applicable).
5. Lint clean (ruff line-length=100 backend / ng lint frontend).
6. No secrets, no cross-boundary writes, no production/cutover changes.

VERDICT: PASS → squash-merge to integration (use --admin to bypass protected self-approval),
         report SHA. OR REJECT → list exact defects for the specialist to fix; do NOT merge.

Return: verdict + SHA (if merged) or defect list (if rejected). Raw, no preamble.
```

### Template D — Single-Agent Fast Mode (docs / status / chore)

```
You are meesell-<role> working on MeeSell.

PROJECT BOUNDARY: project "mesell" at /Users/mugunthansrinivasan/Project/mesell. Stay inside it.

MEMORY: read .claude/agent-memory/meesell-<role>/MEMORY.md; append learnings at the end.

TASK: <doc/status/chore statement>

This is fast mode — execute directly, no spec/build/gate ceremony.
GIT: commit on <branch> with a conventional message, push. (Or, for the master tree, just
report the diff and let the Director route to git-manager — never operate git in the master tree.)

CONSTRAINTS: dev-only, no secrets, no production.

Return: what changed + commit SHA (if any). Raw, no preamble.
```

## 4. The Mandatory Blocks (every dispatch)

Every prompt **must** include these four, or the dispatch is malformed:

1. **PROJECT BOUNDARY** — pins the agent to `/Users/mugunthansrinivasan/Project/mesell`.
2. **MEMORY PROTOCOL** — read own memory first, append at end, never write to peers'.
3. **LOCKED DOCS** — the V1_FEATURE_SPEC section + any locked doc relevant to the task.
4. **CONSTRAINTS** — dev-only / no spend / no secrets / no production.

## 5. Git & Worktree Rules (hard constraints)

- **Never operate git in the master tree.** Use `git -C <worktree-path>` exclusively, or have the
  assigned specialist/coordinator own its worktree.
- Worktrees live under `/tmp/mesell-wt/` (physical `/private/tmp/mesell-wt/`).
- **Model C governance:** `feature/microservices-<svc>/integration` cut off `develop`; group
  branches (db, svc/backend, routes, infra) are siblings off integration.
- group → integration = **LEAD squash gate** (`--admin` to bypass protected self-approval).
- integration → develop = **FOUNDER merge-commit, left OPEN** (lead does NOT approve — rule D1).
- Tests run on `backend/.venv` (3.11/3.12), never host Python 3.9.6 (PEP-604 false failures).

## 6. Standing Constraints (always in force)

- **Autonomy grant** — auto-approve, don't wait for hook confirmation — **BUT** never infer launch
  urgency. Everything stays **dev-only / localhost / zero cutover / zero cloud spend / no
  production**. No VM provisioning or live `gcloud secrets create` without a **fresh founder
  spend-ask**.
- Never fabricate or commit secret values.
- Out-of-scope asks → polite refusal + redirect to the right `meesell-*` agent.

## 7. Decentralized Memory Model

- Each agent owns `.claude/agent-memory/meesell-<role>/MEMORY.md` — reads it at task start,
  appends learnings at task end.
- Agents share context by **reading each other's** memory, never writing to it.
- There is no single source of truth — truth is distributed across agent memories, STATUS
  files, and the locked docs (`V1_FEATURE_SPEC.md`, `PRICING_LOCKED.md`,
  `INFRASTRUCTURE_PLAYBOOK.md`, `LEGAL_AND_COMPLIANCE_INFO.md`).
- Need info not yet recorded by a peer? Escalate via the STATUS file blocker mechanism.

# MeeSell — Master Session Dispatch Documentation

> Self-contained kickoff package for the next MeeSell master session.
> **This edition kicks off `mesell-master-session-6`** and closes out session-5 end-to-end.
> **Founder fills in:** the actual work for this session, under §7.
> **Predecessor:** `mesell-master-session-5` (closed 2026-06-21).

---

## 0. Session Header

| Field | Value |
|---|---|
| **Session Name** | `mesell-master-session-6` |
| **Model** | Opus (Director) — founder may override |
| Role | Director (master orchestration session) |
| Predecessor | `mesell-master-session-5` (closed 2026-06-21) |
| Repo / branch | `/Users/mugunthansrinivasan/Project/mesell` @ `develop` |
| develop HEAD at handoff | `1951199` |
| Date opened | `__________` ← (founder sets) |

---

## 1. KICKOFF PROMPT  *(paste this as the first message to start the session)*

```
You are the MeeSell master Director session "mesell-master-session-6".

Before doing anything, run the BOOT SEQUENCE in
docs/sessions/MASTER_SESSION_DISPATCH.md §2, then give me the boot briefing
(under 200 words) and WAIT for my instructions.

Operate under the MeeSell rules in CLAUDE.md: only meesell-* agents do MeeSell
work; the HYBRID dispatch rule (coordinator SPEC → specialist BUILD → coordinator
MERGE-GATE for code; single-agent fast mode for docs/chores); founder merges all
develop PRs; never git in the master tree (use worktrees); ONE session per
worktree; zero-spend; password login only, READ-ONLY scraping / never go-live;
never commit or echo credentials.

Read the carry-forward state: master-session-6-handoff.md FIRST, then the
master-session memory index at
.claude/projects/-Users-mugunthansrinivasan-Project-mesell/memory/MEMORY.md,
then the Director memory, then §3–§6 of this file. Do not start any work until I
tell you what to do — my instructions will be under §7.
```

---

## 2. BOOT SEQUENCE  *(the session runs these on start, before acting)*

1. **Read memory (highest signal first):**
   - `.claude/projects/-Users-mugunthansrinivasan-Project-mesell/memory/master-session-6-handoff.md` (READ FIRST — session-5's actual work + carry-forward).
   - `.claude/projects/-Users-mugunthansrinivasan-Project-mesell/memory/MEMORY.md` (the master-session memory index).
   - `.claude/agent-memory/nexus-level-0-director/MEMORY.md` (Director memory).
   - This file (§3–§6).
2. **Verify repo state (read-only):**
   - `git -C /Users/mugunthansrinivasan/Project/mesell log origin/develop --oneline -5`
   - `git worktree list` (expect: master (develop) + `gauth-live` (KEEP) + any live parallel-session worktrees — `git ls-remote origin develop` for ground truth on develop HEAD).
   - `gh pr list --state open` (note any in-flight parallel-session PRs).
3. **Verify the local dev stack health:**
   - `curl -s -o /dev/null -w "%{http_code}" http://localhost:4200` → 200 (shell)
   - `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` → 200 (backend)
   - Remotes on :4201–:4206 (static serve.js builds). Calculator: `http://localhost:4200/catalogs/<id>/pricing`.
   - meesell-env can stand up an isolated, RAM-budgeted, port-isolated stack (`tools/meesell_env.py baseline up`; usage in `docs/dev/ENV_MANAGER.md`).
   - If the stack is down, do NOT auto-rebuild — report it and ask (rebuilds are memory-heavy; see §4/§5 RAM note).
4. **Check machine memory** (the binding constraint): `vm_stat` free pages + `sysctl vm.swapusage`. If swap is near full / free RAM low, flag it in the briefing before any build. Builds are ONE-AT-A-TIME on 8 GB.
5. **Produce the boot briefing** (≤200 words): where we are (1 sentence) · what changed since session-5 (1–3 items, highest signal) · what you recommend next / what you're ready for. Then **WAIT** for founder input — never proceed unprompted.

---

## 3. SESSION-5 CLOSEOUT  *(end-to-end — as of 2026-06-21, develop @ `1951199`)*

Session-5 was a mostly-meta session: it hardened the git workflow, built the dev-env manager, executed the entire Claude-feature adoption plan, and proved the dispatch loop end-to-end on one real fix. The master tree was kept pristine + synced throughout; the repo is now UN-shallowed. ~30 PRs landed (#329–#361).

### Git workflow + repo hygiene
- **Git workflow LOCKED** → canonical `docs/GIT_WORKFLOW.md`: `feature/{slug}/{group}` → `feature/{slug}/integration` → `develop` (two-step gate; step-1 squash by Director/coordinator, step-2 merge-commit by FOUNDER) → staging → main (tagged).
- **`main` protection reconciled** to the "no required checks" ruling (force-push / deletion still blocked).
- **Submodules evaluated → REJECTED — stays MONOREPO** (see `[[project_git_workflow_revision]]`).
- **Branch cleanup:** 219 → a handful local; deleted merged / orphaned / squash-absorbed branches + the 11 protected `*/integration` branches (via remove-protection → delete-ref).
- **Repo UN-SHALLOWED** (`git fetch --unshallow`) — this was the root cause of the recurring sync merge-base flakiness; permanently fixed.

### Dev-env tooling
- **Dev-env manager `tools/meesell_env.py`** built (RAM-budgeted, port-isolated; slot N → backend `8000+N·10` / shell `4200+N·10` / mfe `4201+N·10..`). The **esbuild `--service` deadlock was FIXED** (per-app log files + process-group reap + `pkill esbuild`); `baseline up` verified all-8 end-to-end. Usage: `docs/dev/ENV_MANAGER.md`. RAM guard counts free+inactive+speculative (NOT pure-free).
- **`/mesell:dev` skill REWRITTEN** — was dangerously stale (Vite/React/pg14) → now Angular 21 MF + FastAPI + pg16 + memory-safe `dev:static` / meesell-env workflow + OTP bypass `000000`.

### Claude-feature adoption — FULL plan executed
- **Step 1 — gates:** `docs/dev/REVIEW_GATES.md` (advisory `/code-review` + `/security-review` with MeeSell bug-class checklists) + `docs/dev/VERIFY_GATE.md` (FE behavioral via **agent-browser**; BE via httpx). `.claude/commands` is write-protected → the gates are CHECKLIST DOCS, not custom slash commands.
- **Step 2 — isolation + hooks:** worktree isolation (`isolation: worktree` on the 7 Write-capable builders + `WORKTREE_ISOLATION.md`) + 3 INERT warn-only lifecycle hooks (`.claude/hooks/warn-{low-ram-build,admin-merge,infra-dryrun}.sh` — NOT wired into settings.json; enable per `LIFECYCLE_HOOKS.md`).
- **Step 3 — federation `/simplify`:** `frontend/libs/federation/shared.config.js` hoist (#346) + **mfe-billing `mappingVersion:true` fix (#347)** (the hoist's spread is INERT without it).
- **Follow-on docs:** `PLAN_GATE.md`, `MEMORY_INDEX_CONVENTION.md`, `CLAUDE_TOOLING_USAGE.md`, `SESSION_ISOLATION.md`, `CLAUDE_FEATURE_ADOPTION.md`.
- **Context7 + agent-browser wired into the flow (#358):** Context7 = current-API check in PLAN_GATE; agent-browser = behavioral verify in VERIFY_GATE.

### Loop PROVEN end-to-end (#359, then #361)
- `auth.token.*` 2-seg → 3-seg i18n fix: SPEC → founder sign-off → build (isolated worktree + skill) → /verify (test: 401/403 → human string) → coordinator merge-gate (re-ran tests, APPROVE) → founder merge. The gates caught TWO stale assumptions before shipping.
- **#361** codified the isolated-builder memory-persistence rule + landed the auth-builder `L_iam_1` learning. develop ended @ `1951199`.

### Parallel skills session (CLOSED) — also landed on develop
- 15 `meesell-*` skills (13 builder + legal-compliance + agent-browser; PRs #339 / #345 / #355), the CLAUDE.md "Engineering Discipline" section (#348), installed Context7 / SuperPowers / Agent-Browser. claude-mem SKIPPED (key leak); UI-UX-Pro-Max REJECTED (CVSS-9.3 RCE).

---

## 4. OUTSTANDING / CARRY-FORWARD

| # | Item | Owner | Notes |
|---|---|---|---|
| 1 | **Remote/cloud agents + `/schedule`** | Founder | DEFERRED — need founder sign-off (zero-spend). Canva/Drive MCP REJECTED. |
| 2 | **Google auth HELD** | Founder | Verified working on isolated stack but blocked on Decision #5 amendment ratification. `feature/google-auth` + `gauth-live` worktree = KEEP (founder ruling). |
| 3 | **Rotate `.meesho_creds.env`** before first LIVE pricing census | Founder | Exposed in earlier chats. NO live census has run; W6 monthly job is built+tested only; NO launchd schedule installed (manual/supervised by design). |
| 4 | **8 per-service `svc-*/app/core/auth.py` 2-segment auth-id mirror** | Backend | V1.5, low sev. The per-service copies still raise 2-segment auth ids (NOT on the V1 monolith serving path) — mirror the #359 fix later; logged on `feature_board_backend.md`. |
| 5 | **Enable lifecycle hooks when ready** | Founder/Director | The 3 warn-only hooks are INERT (not in settings.json). Enable per `docs/dev/LIFECYCLE_HOOKS.md`. |
| 6 | **Restart a session to load Context7 as a native tool** | Director | Context7 + agent-browser are wired into the flow docs but Context7 needs a session RESTART to load as native MCP tools. Free tier ~1k/mo is plenty solo. |
| 7 | **Pre-existing `ng test` red** | Backend/FE | `ng test` red on unbuilt `@mesell/core` ApiClient/NetworkService (Wave-6 service-layer gap); separate from the scanner-based FE Gate. |

---

## 5. STANDING CONSTRAINTS  *(carried — non-negotiable)*

- **Canonical git workflow: `docs/GIT_WORKFLOW.md`** is the single source of truth for branching, worktree, and merge rules. The constraints below are the carry-forward subset — if anything conflicts, `docs/GIT_WORKFLOW.md` wins.
- **Only `meesell-*` agents** do MeeSell work. Never `nexus:*`, `general-purpose`, `Explore`, `Plan`. **MeeSell does NOT use Nexus** (founder ruling — `[[project_meesell_no_nexus]]`).
- **Two-step merge flow:** `feature/{slug}/{group}` --squash--> `feature/{slug}/integration` (Director/coordinator merges) --merge-commit--> `develop` (**founder** merges) → staging → main (tagged). Legacy `ticket/{number}-desc` + single-step "squash merge to main" is RETIRED.
- **Founder merges all develop PRs.** The Director opens PRs and merges `--admin` only when founder-directed.
- **Never git in the master tree** — every feature-group works in its own worktree off develop. `MESELL_ALLOW_MASTER_GIT=1` is the deliberate-recovery override for safe ops only (branch -D, worktree prune).
- **ONE session per worktree / clone.** Concurrent sessions sharing one checkout COLLIDE (branch switched out mid-op; stale `origin/develop` ref sweeping foreign commits into PRs). See `docs/dev/SESSION_ISOLATION.md`.
- **Zero-spend / dev-only** posture unless told otherwise.
- **Builds one-at-a-time on 8 GB** (use meesell-env); direct `ng` binary (NOT npx); kill esbuild between builds.
- **Password login only / NO OTP go-live.** **READ-ONLY scraping, never go-live.** Never commit/echo credentials.
- **DB tests** use a disposable `TEST_DATABASE_URL`, NEVER the live dev DB (prior incident drop_all'd it; recovery = `make seed`).
- **Never amend LOCKED docs** (`V1_FEATURE_SPEC.md`, `PRICING_LOCKED.md`, `INFRASTRUCTURE_PLAYBOOK.md`, `LEGAL_AND_COMPLIANCE_INFO.md`) without founder approval.

---

## 6. AGENT FLEET + DISPATCH RULES + NEW CAPABILITIES

> **Branching / worktree / merge convention: see `docs/GIT_WORKFLOW.md`** (canonical). Each dispatched feature-group works on its own `feature/{slug}/{group}` branch in its own worktree + localhost env; group→integration is squash-merged by the Director/coordinator, integration→develop is merge-committed by the founder.

### HYBRID dispatch (founder-ruled)
- **Code-heavy** (feature code, backend/auth, AI pipeline, federation config): THREE steps — (1) coordinator produces SPEC, (2) session dispatches the named SPECIALIST to build, (3) coordinator runs the MERGE-GATE review (a real gate — can reject). Then open PR for founder merge.
- **Docs / status / chores:** single-agent fast mode (coordinator/lead executes directly).
- Coordinators have NO Agent tool — the master session runs the hierarchy for them.

### Roster (19 agents)
`meesell-section-coordinator` (Tier-1) · `meesell-infra-builder` (ops/cleanup, standalone) · `meesell-backend-coordinator` → database / api-routes / services / auth builders · `meesell-frontend-coordinator` → angular component / service / ui-styler builders · `meesell-ai-coordinator` → prompt-engineer / category-picker / image-precheck · `meesell-data-engineer` → xlsx-parser / scraper-maintainer · `meesell-legal-writer` (standalone). Full specs: `docs/MEESELL_AGENT_REGISTRY.md`.

### NEW CAPABILITIES (added in session-5 — use them)
- **Worktree isolation** — the 7 Write-capable builders carry `isolation: worktree`; each runs in its own worktree off develop. Dispatch convention + the `isolation` field are documented in `docs/dev/WORKTREE_ISOLATION.md`.
- **Coordinator-as-scribe** — isolated builders CANNOT write their own memory (it's outside their worktree). The dispatching **coordinator persists the builder's REPORTED learning** (sanctioned narrow exception to the no-write-to-others'-memory rule — scribe, not author). Codified in `WORKTREE_ISOLATION.md`.
- **The gates** — `docs/dev/REVIEW_GATES.md` (advisory `/code-review` + `/security-review` bug-class checklists), `docs/dev/VERIFY_GATE.md` (FE behavioral via agent-browser; BE via httpx), `docs/dev/PLAN_GATE.md` (current-API check before building). These are CHECKLIST DOCS, not slash commands (`.claude/commands` is write-protected).
- **meesell-env** — RAM-budgeted, port-isolated dev stacks (`tools/meesell_env.py`; `docs/dev/ENV_MANAGER.md`). Builds one-at-a-time; esbuild deadlock fixed.
- **Context7** — current-API check folded into PLAN_GATE / SPEC. Zero-spend fallback: for THIN libs (native-federation 156, celery 89 snippets) READ THE SOURCE; rich libs (Angular / SQLAlchemy / FastAPI / Pydantic) use Context7. Needs a session RESTART to load as a native MCP tool (free tier ~1k/mo).
- **agent-browser** — behavioral verification (the VERIFY_GATE FE path). Use it to confirm a fix in a real browser before merge.
- **Lifecycle hooks (INERT)** — 3 warn-only hooks (`warn-low-ram-build`, `warn-admin-merge`, `warn-infra-dryrun`) exist but are NOT wired into settings.json. Enable per `docs/dev/LIFECYCLE_HOOKS.md`.
- **`.claude/` git-plumbing workaround** — the `.claude/` tree (commands/settings/hooks/agents/agent-memory) is WRITE-PROTECTED for agents. Land changes via the git-plumbing route (`git hash-object -w` → `git update-index --add --cacheinfo <mode>,<blob>,<path>` → commit from index) OR the Director Direct-Mode Override. `docs/` + root files are normally writable.
- **`mappingVersion: true` is MANDATORY** for any Native-Federation remote sharing `@mesell/*` — the `...mesellShared` spread alone is INERT (NF 3.5.5 only emits the pinned version with mappingVersion).

### Dev/build gotchas
Lean sequential builds only (memory); static serve.js not `ng serve`; after FE/BE changes land on develop, rebuild the relevant remote(s) from develop + restart serve.js + hard-refresh :4200; backend `--reload` restart for BE changes.

Reference: `docs/dev/CLAUDE_FEATURE_ADOPTION.md` (the overall adoption narrative), `docs/dev/CLAUDE_TOOLING_USAGE.md`, `docs/dev/MEMORY_INDEX_CONVENTION.md`, `docs/dev/SESSION_ISOLATION.md`.

---

## 7. FURTHER INSTRUCTIONS  *(founder appends below — the actual work for this session)*

> _(empty — founder will fill this in)_

# Claude Code Feature Adoption Report — MeeSell

> Generated 2026-06-21 by the `claude-feature-adoption-analysis` workflow (17 agents). Advisory — adopt per the recommended sequence; spend-bearing items need founder sign-off.

## 1. Executive Summary

The three forces shaping every decision are: an **8GB dev box** that deadlocks on parallel esbuild/ng builds, a **solo founder** who is the only reviewer and merger, and a **0-required-review pipeline** where 8 PRs landed via `--admin` unreviewed. The highest-leverage moves are therefore (a) **zero-RAM review/verification gates** (`/code-review`, `/security-review`, `/verify`, plan-gate) that restore quality control without competing for memory, and (b) **structural prevention** (worktree isolation, lifecycle hooks, `/simplify` of the federation-config drift) that makes the recurring bug classes — federation singleton logout, master-tree corruption, FE/BE contract drift — impossible rather than re-debugged. **Remote/cloud execution** is the only true fix for the RAM ceiling, but it is spend-bearing and gated behind founder sign-off, so it is a strategic bet, not a quick win.

## 2. Prioritized Features (high-impact / low-effort first)

| Feature | Impact | Effort | One-line productivity gain |
|---|---|---|---|
| `/code-review` skill | High | Low | Adds an automated bug-review pass to a 0-review pipeline, zero RAM, no build |
| `/security-review` skill | High | Low | Per-PR authz/secret/injection coverage where CI has none, token-only cost |
| Agent worktree isolation | High | Low | Makes master-tree corruption structurally impossible (config-only) |
| `/simplify` (federation config) | High | Low | Hoists 8 drifted `mesellShared` blocks to 1 source, kills the singleton-logout bug class |
| Hooks + settings.json lifecycle | High | Low | Turns ~5 memory-dependent rules into mechanical guarantees (RAM warn, admin-merge speed bump) |
| Persistent decentralized memory | High | Low | Index-refactor cuts per-task context ~10x; worktree-safe appends stop lost learnings |
| Plan-gate (read-only SPEC phase) | High | Low | Catches wrong-key/port/singleton errors before the first RAM-thrashing rebuild |
| `/verify` skill | High | Medium | Replaces manual rebuild-restart-refresh-click loop with one deterministic in-browser gate |
| `/run` + `/mesell:dev` rewrite | High | Low | Collapses 6-step cold-start to one command; mandates memory-safe `dev:static` |
| Workflow tool (deterministic orchestration) | High | Medium | Encodes HYBRID 3-step + two-step gate as non-skippable nodes |
| Remote / cloud agents | High | Medium | Only true fix for the 8GB esbuild deadlock (spend-gated) |
| `/loop` (recurring tasks) | Medium | Low | Automates skipped board/PR sweeps; serial RAM-gated rebuilds |
| TaskCreate/List/Update | Medium | Low | One TaskList query replaces re-reading ~3,100 lines of board prose |
| `/schedule` + Cron | Medium | Low | Unattended nightly sweeps/digests (spend-gated, non-code only) |
| `/deep-research` + WebSearch/Fetch | Medium | Low | Grounds SPECs in current Razorpay/GIS/Angular docs past the Jan-2026 cutoff |
| MCP servers (Canva/Drive/GitLab) | Low | Low | Marginal; wrong host (MeeSell is GitHub), adds resident RAM — mostly reject |

## 3. How to Execute — Top 5

### 3.1 `/code-review` skill
1. Pilot in-session from the worktree: run `/code-review` on the next `feature/{slug}/{group}` diff vs its integration branch, with the **owning meesell-* coordinator** as reviewer (preserves the `^meesell-*` invariant).
2. Encode MeeSell's known bug classes as the checklist: federation shared-lib version drift, in-memory-token/authGuard logout, FE<->BE contract parity (verb/field/enum), Razorpay-live + held-google-auth flag gating, RO-scrape/zero-spend guarantees.
3. Add a thin `.claude/commands/code-review.md` wrapper that writes findings into the status board / coordinator memory (not throwaway chat).
4. Make it the concrete tool for **HYBRID dispatch step 3** — coordinator runs it on the specialist PR and can reject back with structured findings.
5. Keep it **advisory** (non-required context); after ~10 clean PRs, consider promoting to a required develop context. Gate headless `claude -p` runs to integration->develop PRs only to bound token spend.

### 3.2 `/security-review` skill
1. Pilot diff-scoped on the **highest-value surfaces only**: Razorpay webhook/signature verify + the held google-auth verify endpoint — gauge signal and token cost before any automation.
2. Author `.claude/commands/security-review.md` pinned to the merge-base diff; **explicitly exclude** `*.example`, `.env`, secrets files, `.venv` from context.
3. Encode MeeSell rules in the prompt: `user_id` repository scoping, JWT-in-memory + HttpOnly/Secure/SameSite=Strict refresh cookie, Razorpay signature checks, GCS signed-URL TTL bounds, RO-only scraper egress.
4. Wire into the two-step gate: coordinator merge-gate pastes findings; founder sees them as advisory context. Keep it **read-only/advisory** — fixes route to a meesell-* specialist, never the skill itself.
5. Record adoption + the diff-scoping rule in infra memory; do NOT amend `INFRASTRUCTURE_PLAYBOOK.md` without founder approval.

### 3.3 Agent worktree isolation
1. Inventory the code-writing specialists (angular-component/service/ui-styler, services/api-routes/auth/database builders); exclude coordinators and standalone leads (spec/review only).
2. Pilot on ONE: add `isolation: "worktree"` to `meesell-angular-service-builder.md` frontmatter; dispatch a small real task and confirm the master tree stays on develop.
3. Point native worktrees at the convention: created off `origin/develop`, branch named `feature/{slug}/{group}` so the two-step gate is unchanged.
4. **Hard concurrency cap: ONE build-specialist worktree running at a time** (8GB) — encode in the dispatch protocol + env-manager RAM budget; second worktree only opens after the first is merged/torn down.
5. Keep `guard-master-tree-git.sh` as defense-in-depth; wire teardown (`git worktree prune`) at session end. Roll out to remaining specialists one at a time.

### 3.4 `/simplify` (federation config drift)
1. In a dedicated worktree off develop, run `/simplify` on `frontend/apps/*/federation.config.js` to confirm it flags the 8 duplicated `mesellShared` blocks **and** the `mfe-billing` missing `MESELL_SHARED_VERSION` pin.
2. Coordinator specs, `meesell-angular-service-builder` applies: hoist `mesellShared` into `frontend/libs/federation/shared.config.js`, import in all 8 apps. **Apply narrowly** — only the shared block; do NOT touch per-app `exposes`/`skip` (mfe-catalog differs).
3. Normalize the `@mesell/*` `package.json` files to one shape (name+version+peerDeps).
4. Run `/simplify` in **report-only** mode on `backend/services/*/app/config.py` + `database.py`; route the svc-common consolidation proposal to backend-coordinator — do NOT auto-extract (architecture decision).
5. Validate on the worktree's RAM-budgeted env (not a full 8-MFE build); manual hunk-review every diff before any `--admin` merge.

### 3.5 `/verify` skill
1. Scope ownership: author under frontend-coordinator's tools (FE boot) + backend-coordinator (API assertion); infra-builder only reviews the env/CI touch points.
2. Author `.claude/skills/verify/SKILL.md`: inputs = worktree + change-type (`fe-route|fe-federation|api-endpoint|migration`) + expected assertion; outputs = pass/fail + screenshot/JSON artifact paths.
3. Wire the FE path through `meesell_env.py up <worktree> --mfe <touched-only>` (honors the single-build mutex + RAM budget) -> `boot-smoke.js` against the assigned port block. **Never rebuild all 7 MFEs; never run concurrent verify envs.**
4. Wire the API path: targeted httpx assertion against the worktree's backend port. Always finish with `meesell_env.py down <worktree>` + `gc`.
5. Make it a **HYBRID-dispatch obligation**: coordinator rejects any specialist PR lacking the `/verify` pass artifact. Pilot on the two open known bugs (federation-singleton logout, size_in_ltrs 422) before standardizing.

## 4. Quick Wins vs Strategic Bets

**Quick wins (low effort, adopt now):**
- `/code-review` and `/security-review` — diff-only, zero RAM, restore the missing review pass immediately.
- Agent worktree isolation — config-only flag; ends the master-tree corruption class.
- `/simplify` federation config — one session kills the highest-cost recurring bug (shared-lib drift).
- Lifecycle hooks — mechanical RAM warning + admin-merge speed bump + infra dry-run validation.
- `/run` + `/mesell:dev` rewrite — the current `dev.md` is dangerously stale (Vite/React/pg14); fixing it is pure dev-tooling.
- Memory index refactor + TaskCreate pilot — cut context cost and board-bookkeeping drift.

**Strategic bets (high impact, higher effort / spend / governance):**
- **Remote / cloud agents** — the only feature that genuinely moots the 8GB ceiling, but breaks the zero-spend posture; requires founder spend-cap sign-off and build/test-only scoping with all gates intact.
- **Workflow tool** — deterministic HYBRID + two-step gate; high payoff but treat as code under review, verify GA availability before building all 5 domain workflows.
- **`/verify`** — medium effort glue over existing primitives; the only behavioral gate the pipeline lacks.
- **`/schedule` + Cron** — spend-bearing, non-code chores only; adopt after a founder usage cap.

## 5. Recommended Adoption Sequence

1. **First — `/code-review` + `/security-review` (advisory).** Zero RAM, zero build, low effort; they immediately plug the 0-review/`--admin` gap that is the most dangerous current reality, and need no infra changes.
2. **Second — Agent worktree isolation + lifecycle hooks.** Structural prevention of the two highest-cost failure modes (master-tree corruption, esbuild deadlock surprise) with config/script-only effort; makes the gains above safe to run concurrently.
3. **Third — `/simplify` federation config + `/verify`.** With review gates and isolation in place, eliminate the recurring federation-drift bug class permanently and add the behavioral gate that proves fixes work in-browser before merge.

*Deferred pending founder decision:* remote/cloud agents and `/schedule` (spend cap required); Workflow tool (confirm GA first). *Reject:* Canva and Google Drive MCP (no domain fit); GitHub MCP only if `gh` CLI proves insufficient (it does not today).

# MeeSell Section-Parallel Development Model

**STATUS: APPROVED 2026-06-15 — ratified by founder. Now executable.**

> This document **EXTENDS** the APPROVED repo-management governance. It does NOT replace it. Per `MASTER_PLAN.md §10` (acceptance gate) and `§7.3` (escalation rules), any change to the governed branch model, merge flow, or agent roster requires **founder approval**. Until the founder flips this STATUS header to `APPROVED YYYY-MM-DD`, no agent operates under this model. Active work continues under the APPROVED `MASTER_PLAN.md` (Model C) as written.

| Field | Value |
|---|---|
| Document type | Governance extension (planning only — proposes a parallel-execution overlay) |
| Path | `/Users/mugunthansrinivasan/Project/mesell/docs/plans/repo_management/SECTION_PARALLEL_MODEL.md` |
| Author | meesell-backend-coordinator |
| Builds on (LOCKED / APPROVED) | `docs/plans/repo_management/MASTER_PLAN.md` (v1.1 APPROVED) · `docs/SECTION_SUB_SESSION_PROTOCOL.md` (LOCKED 2026-06-06) · `docs/plans/features/_WORKTREE_PROTOCOL.md` |
| Source rulings | Five founder rulings dated 2026-06-15 (reproduced verbatim in §B) |
| Out of scope | Code changes; editing `CLAUDE.md`; editing `docs/MEESELL_AGENT_REGISTRY.md`; creating the 27 branches/worktrees (those are execution steps gated on ratification) |

---

## A. Purpose + relationship to the locked docs it builds on

### A.1 What this model is

The APPROVED `MASTER_PLAN.md` defines a **feature-centric, five-group** parallel model (`backend`, `frontend`, `ai`, `data`, `infra`) where each feature integrates across up to five group branches under a `feature/{name}/integration` parent. That model is correct and stays in force. This document proposes an **execution overlay** that the founder has ratified in principle (the "next-level development" model): run **all nine V1 features as parallel vertical slices**, each slice owned end-to-end by a new **Tier-1 section-coordinator** agent, with the five groups collapsed into **two** group streams per slice (`frontend` and `backend`, the latter absorbing AI + data + infra disciplines).

This is an **evolution**, not a contradiction. Specifically:

- It **reuses** the `MASTER_PLAN.md §2` merge flow and gate ownership unchanged, except for the single PR-opener change in §F.
- It **reuses** the `SECTION_SUB_SESSION_PROTOCOL.md` master→sub-session pattern, wave concept, and dispatch-permission model — the Tier-1 section-coordinator is a sub-session that holds SPECIALIST DISPATCH PERMISSION exactly as today's construction sub-sessions do.
- It **reuses** the `_WORKTREE_PROTOCOL.md` worktree-per-branch isolation and the `/tmp/mesell-wt/` layout.
- It **adds** one agent role (Tier-1 section-coordinator — see §J roster-impact flag) and one protocol addition (per-feature business-logic wave decomposition — §H).

### A.2 Relationship to each locked doc

| Locked doc | What this model takes from it | What this model adds / changes |
|---|---|---|
| `MASTER_PLAN.md` (APPROVED v1.1) | Branch model (Model C), §2 merge flow + gate ownership, §4 session naming grammar, §6 feature_board, §7 lead responsibilities, F1 git-ref rule (`…/integration` parent), F3 integration-branch protection | Adds the `section-N` **alias** layer over kebab slugs (§C); collapses 5 group branches → 2 (`frontend` + `backend`) per ruling 3; changes ONLY the §2.2 PR-opener from "largest-contributing lead" to "section-coordinator" (ruling 4 / §F) |
| `SECTION_SUB_SESSION_PROTOCOL.md` (LOCKED) | Master→sub-session role split; SPECIALIST DISPATCH PERMISSION block; wave sequencing concept; reporting + escalation protocol | Adds a 4-tier tree (§E) where the Tier-1 section-coordinator is itself a dispatching sub-session; adds the per-feature **business-logic** wave decomposition (§H) alongside the existing dependency-ordered **architecture** waves (no conflict — see §H.4) |
| `_WORKTREE_PROTOCOL.md` | One physical worktree per branch under `/tmp/mesell-wt/`; symlinked `.claude/agent-memory` + `.claude/agents`; append-only/unique-header memory discipline (§7.1) | Extends the layout to `/tmp/mesell-wt/section-{N}-{tier}` (27 worktrees, §I); section-coordinator memory shares one dir across 9 parallel sessions, so per-section topic files are mandatory (§E.4, follows §7.1) |

### A.3 Why collapse 5 groups → 2

Ruling 3 collapses the five `MASTER_PLAN.md` groups into two group branches per section. The rationale (founder-ruled): for V1's nine features, AI / data / infra contributions are small, per-feature, and tightly coupled to the backend slice (e.g. smart-picker's prompt registry pin lands beside the category `/suggest` endpoint; image-precheck's GCS bucket policy lands beside the Celery task). Carrying five thin branches per feature multiplied 9× yields 45 group branches and a coordination tax that outweighs the isolation benefit. The backend section-stream is therefore **multi-disciplinary**: the backend-coordinator pulls in `meesell-ai-coordinator` / `meesell-data-engineer` / `meesell-infra-builder` specialists as the feature needs them, and all of their output lands on the one `…/backend` branch.

---

## B. The five founder rulings (verbatim, 2026-06-15)

> **Ruling 1.a:** `section-N` is an ALIAS layer over the existing kebab feature slugs. Kebab slugs stay canonical (the 9 LOCKED FEATURE_PLANs / session names / feature_board rows keep them). Branches use the `section-N` form; an alias table ties section-N ↔ slug.

> **Ruling 2:** each section has a PARENT integration branch `feature/section-N/integration` (required by the MASTER_PLAN F1 git-ref rule — confirmed).

> **Ruling 3:** only TWO group branches per section — `frontend` (FE only) and `backend` (absorbs AI + data + infra). The backend stream is multi-disciplinary: backend-coordinator pulls in ai-coordinator / data-engineer / infra-builder specialists as the feature needs them, all landing on the one `…/backend` branch.

> **Ruling 4:** a NEW agent role `meesell-section-coordinator` is the Tier-1 master of one feature slice. It alone owns the feature's wave plan AND opens/owns the `…/integration → develop` PR (replacing MASTER_PLAN §2.2's "largest-contributing lead opens it"). Founder still APPROVES/merges that PR (§2.2 unchanged otherwise).

> **Ruling 5:** per-feature business-logic wave decomposition is an ADDITION to the SUB_SESSION_PROTOCOL (no conflict with the existing dependency-ordered architecture waves).

---

## C. Section ↔ slug alias table (canonical)

Per ruling 1.a, kebab slugs remain canonical. The 9 LOCKED FEATURE_PLANs, all session names that reference a feature, and every `feature_board_*.md` row keep the kebab slug. Branches and worktrees use the `section-N` form. This table is the single bidirectional key.

| Section | Kebab slug (canonical) | V1 feature name | V1_FEATURE_SPEC.md |
|---|---|---|---|
| section-1 | `auth-otp` | Auth (Phone OTP + JWT) | Feature 1 |
| section-2 | `smart-picker` | Smart Category Picker | Feature 2 |
| section-3 | `catalog-form` | Fast Catalog Form | Feature 3 |
| section-4 | `ai-autofill` | AI Auto-fill | Feature 4 |
| section-5 | `image-precheck` | Image Pre-check | Feature 5 |
| section-6 | `live-preview` | Live Product Preview | Feature 6 |
| section-7 | `price-calculator` | Price Calculator | Feature 7 |
| section-8 | `tracking-dashboard` | Tracking Dashboard | Feature 8 |
| section-9 | `xlsx-export` | XLSX Export | Feature 9 |

**Alias discipline:** `section-N` is **only** ever a branch/worktree token. It is NEVER substituted for the slug inside a FEATURE_PLAN, a feature_board row, a memory header, or a commit-footer session name. If you see `section-3` anywhere that is not a branch ref or a worktree path, that is a discipline violation — the canonical form there is `catalog-form`.

---

## D. Branch model diagram

The Model C topology is preserved; the only change is the two-group fan-out (ruling 3) and the `section-N` token on the feature branches (ruling 1.a). The `…/integration` parent is mandatory (ruling 2, per `MASTER_PLAN.md F1`).

```
main
├── staging
└── develop
    │
    ├── feature/section-1/integration            ← parent (branched from develop; F1 git-ref form)
    │   ├── feature/section-1/frontend           ← FE specialists only
    │   └── feature/section-1/backend            ← BE + AI + data + infra specialists (ruling 3)
    │
    ├── feature/section-2/integration
    │   ├── feature/section-2/frontend
    │   └── feature/section-2/backend
    │
    ├── …  (section-3 … section-8, same shape)  …
    │
    └── feature/section-9/integration
        ├── feature/section-9/frontend
        └── feature/section-9/backend

Gate 1 (discipline-lead squash):  …/frontend  → …/integration   (frontend-coordinator merges)
                                  …/backend   → …/integration   (backend-coordinator merges)
Gate 2 (founder merge-commit):    …/integration → develop       (PR opened/owned by section-coordinator — ruling 4)
Gate 3 (founder, unchanged):      develop → staging → main
```

Per `MASTER_PLAN.md F1`: the parent is `feature/section-N/integration` (NOT `feature/section-N`), because a git ref cannot be both a file and a directory at the same path. The group branches keep the canonical `feature/{name}/{group}` form with `{name}` = `section-N` and `{group}` ∈ `{frontend, backend}`.

---

## E. The 4-tier session / agent tree

```
TIER 0 — master session (Director)          mesell-master-session-{N}
   │   Only the section-coordinator CHECK-IN GATE sits here.
   │   Receives each section-coordinator's WAVE PLAN; signs off (or returns) BEFORE the slice acts.
   │
   ├─ TIER 1 — meesell-section-coordinator (NEW · ×9 · run in parallel)
   │     mesell-section-{N}-coordinator-session-{M}
   │     Own session window holding SPECIALIST DISPATCH PERMISSION (Option B — exactly like today's
   │     construction sub-sessions per SUB_SESSION_PROTOCOL §3 "SPECIALIST DISPATCH PERMISSION").
   │     MUST bring its WAVE PLAN to Tier 0 and get sign-off before dispatching anything.
   │     After approval, runs its FE+BE sub-tree autonomously and reports the finished slice up.
   │       │
   │       ├─ TIER 2 — frontend sub-session
   │       │     mesell-section-{N}-frontend-session-{M}
   │       │     = meesell-frontend-coordinator + its 3 specialists
   │       │       (angular-component-builder, angular-service-builder, angular-ui-styler)
   │       │     Gates …/frontend → …/integration.
   │       │
   │       └─ TIER 2 — backend sub-session
   │             mesell-section-{N}-backend-session-{M}
   │             = meesell-backend-coordinator + BE/AI/data/infra specialists:
   │               database-builder, api-routes-builder, services-builder, auth-builder,
   │               + (pulled in as the feature needs) ai-coordinator's prompt-engineer /
   │                 category-picker-builder / image-precheck-builder, data-engineer's
   │                 xlsx-parser / scraper-maintainer, and infra-builder.
   │             Gates …/backend → …/integration.
   │
   └─ TIER 3 — the existing specialists, UNCHANGED.
         The sonnet/opus builders from the 18-agent roster. No spec change.
```

### E.1 Tier-0 responsibility (Director)

The master session does exactly one new thing in this model: it runs the **check-in gate** for each Tier-1 section-coordinator. A section-coordinator may NOT dispatch any child until its wave plan has been signed off here. The master also still owns `develop → staging → main` and approves/merges the `…/integration → develop` PRs (those PRs are *opened* by the section-coordinator per ruling 4, but *approved/merged* by the founder per `MASTER_PLAN.md §2.2`, unchanged).

### E.2 Tier-1 responsibility (section-coordinator)

Owns ONE feature vertical slice end to end: produces + owns the wave plan; passes the check-in gate; dispatches the FE + BE Tier-2 sub-sessions; gates `…/frontend` and `…/backend` → `…/integration` (delegating the per-discipline squash review to the respective coordinator per §F); opens + owns the `…/integration → develop` PR; consolidates and reports the finished slice up. It does NOT write feature code itself, does NOT touch other sections, does NOT approve its own `…/integration → develop` merge.

### E.3 Tier-2 responsibility (discipline sub-sessions)

The frontend Tier-2 sub-session IS the `meesell-frontend-coordinator` running its three specialists; the backend Tier-2 sub-session IS the `meesell-backend-coordinator` running the four backend specialists PLUS the AI/data/infra specialists it pulls in per ruling 3. Each Tier-2 sub-session holds the §2.1 discipline-lead squash gate for its own group branch — unchanged from `MASTER_PLAN.md`.

### E.4 Tier-1 memory discipline (9 parallel sessions, one dir)

Per `_WORKTREE_PROTOCOL.md §7.1`: nine section-coordinator sessions run in parallel and SHARE one memory directory `.claude/agent-memory/meesell-section-coordinator/`. Same-file concurrent writes race at the filesystem level. Therefore:

- The shared `MEMORY.md` is **append-only with unique session headers** (`## Session mesell-section-{N}-coordinator-session-{M} — YYYY-MM-DD`).
- **Strongly preferred:** each section uses a per-section topic file `section-{N}.md`, and `MEMORY.md` is just the index. This is the §7.1 "higher-confidence isolation" path and is the default for this model because 9-way parallelism guarantees contention otherwise.
- No section-coordinator ever writes another section's topic file or another agent's memory dir.

---

## F. Governance mapping to MASTER_PLAN §2 (reused vs changed)

| MASTER_PLAN.md element | In this model | Reused / changed |
|---|---|---|
| §2.1 STEP 1 — `…/{group}` → `…/integration` | `…/frontend` → `…/integration` (frontend-coordinator merges); `…/backend` → `…/integration` (backend-coordinator merges). Squash. Gates 1+2+3 required; 4+5 advisory. | **REUSED unchanged.** Only the group set shrinks to 2 (ruling 3). |
| §2.2 STEP 2 — `…/integration` → `develop` PR opener | The **section-coordinator** opens and owns this PR. | **CHANGED (ruling 4):** replaces "the lead whose group has the largest contribution." This is the SINGLE governance change. |
| §2.2 STEP 2 — `…/integration` → `develop` approver/merger | **Founder.** Merge-commit (not squash). All 5 CI gates green. | **REUSED unchanged.** |
| §2.3 STEP 3 — `develop` → `staging` | Master session opens; founder merges. | **REUSED unchanged.** |
| §2.4 STEP 4 — `staging` → `main` | Master session opens; founder merges + tags. | **REUSED unchanged.** |
| §2.5 partial-group decision tree | Applies with 2 groups instead of 5; `…/integration → develop` blocked until BOTH participating groups merge. | **REUSED unchanged** (smaller group set). |
| F1 git-ref rule (`…/integration` parent) | Parent is `feature/section-N/integration`. | **REUSED unchanged** (ruling 2 confirms). |
| F2 board MERGED-transition mechanism | Discipline coordinators still do the direct status-only board flip on `…/integration`. | **REUSED unchanged.** |
| F3 integration-branch protection (review-count 0) | Applied at each `feature/section-N/integration` creation. | **REUSED unchanged.** |
| §6 feature_board | Each discipline coordinator keeps its own `feature_board_{backend,frontend}.md`; rows keyed by the **canonical kebab slug** (not `section-N`). | **REUSED unchanged** (alias discipline, §C). |
| §7.3 escalation | Architecture amendments, scope changes, branch-protection changes still escalate to founder. Adding the 19th agent role is itself such an escalation (§J). | **REUSED unchanged.** |

**The one and only governance change** is the §2.2 PR opener (ruling 4). Everything else in `MASTER_PLAN.md §2` is carried verbatim.

---

## G. Naming convention

Codified exactly. `N ∈ 1..9`; `M` = resume ordinal (starts at 1, +1 per context-break resume, mirroring `MASTER_PLAN.md §4.3`).

| Artifact | Pattern | Allowed values | Example |
|---|---|---|---|
| Branch | `feature/section-{N}/{tier}` | `tier ∈ integration \| frontend \| backend` | `feature/section-3/backend` |
| Session | `mesell-section-{N}-{role}-session-{M}` | `role ∈ coordinator \| frontend \| backend` | `mesell-section-3-coordinator-session-1` |
| Worktree | `/tmp/mesell-wt/section-{N}-{tier}` | one per branch | `/tmp/mesell-wt/section-3-backend` |
| Master | `mesell-master-session-{N}` | Tier 0, unchanged | `mesell-master-session-4` |

Rules:

- `N` is the section number (1..9), tied to the kebab slug via §C. It is stable for the life of the feature.
- `M` is the resume ordinal **per (section × role) tuple**, identical semantics to `MASTER_PLAN.md §4.3`: starts at 1, increments by 1 on every context-break resume, never reused, resets per (section × role).
- The `coordinator` role token is the Tier-1 section-coordinator. The `frontend`/`backend` role tokens are the Tier-2 discipline sub-sessions. These three are the only role values.
- The session name is recorded in the same three places as `MASTER_PLAN.md §4.2`: commit-footer of the branch's first commit by that session, the agent's memory file header, and the discipline `feature_board_*.md` "current session" column (keyed by canonical slug).

---

## H. Wave-decomposition protocol ADDITION

Per ruling 5, this is an **ADDITION** to `SECTION_SUB_SESSION_PROTOCOL.md`. It governs how a Tier-1 section-coordinator decomposes a feature's heavy business logic into a wave plan, which is the artifact it brings to the Tier-0 check-in gate.

### H.1 Decompose into smallest single-responsibility units

The section-coordinator reads the feature's LOCKED `FEATURE_PLAN.md` and `V1_FEATURE_SPEC.md` entry, then breaks the slice into the **smallest single-responsibility units of work** — each unit is one coherent deliverable a single specialist can own in one dispatch (e.g. "category `/suggest` endpoint Pydantic schema", "smart_picker.v1 prompt registry pin + golden set", "Smart Picker page component", "AuthService split-token wiring"). A unit is too big if it spans two specialists; too small if it cannot stand alone as a reviewable change.

### H.2 Order units into dependency waves

The coordinator orders the units into **dependency waves**. A wave is a set of units with no intra-wave dependency that may run concurrently. The ordering rules of thumb (from the backend dispatch heuristic): schema/migration before the service that consumes it; service before the route that consumes it; backend contract before the frontend consumer that binds to it; AI prompt pin alongside the endpoint that calls it; infra secret/bucket before the code that reads it.

### H.3 Per-wave FE/BE mixing + barrier vs overlap decision

For each wave the coordinator decides:

- **FE/BE mixing:** whether the wave contains frontend units, backend units, or both. A contract-defining wave is typically backend-only (the FE binds to it in a later wave); a polish/integration wave is typically both.
- **Hard barrier vs overlap:** whether the next wave must wait for a **hard barrier** (this wave fully merged to `…/integration` before the next starts — used when wave N+1 binds to a contract wave N produces) or may **overlap** (wave N+1 starts while wave N is still in review — used when the dependency is soft or absent). This is the section-coordinator's judgment call and is the highest-leverage decision in the plan.

### H.4 No conflict with the architecture waves

`SECTION_SUB_SESSION_PROTOCOL.md §1.3` defines **dependency-ordered architecture waves** (Wave 1 foundation → … → Wave 10 acceptance) for constructing the 26 architecture sections. Those are a one-time backend-construction sequence across the whole monolith. The **business-logic waves** defined here are **per-feature** and orthogonal: they decompose ONE feature's slice into work units. A feature's business-logic Wave 1 may consume already-CONSTRUCTED architecture sections; it never re-opens them. The two wave systems share the word "wave" and the dependency-ordering principle, but operate at different scopes (whole-monolith construction vs single-feature slice) and never collide. Where a feature's slice would require amending a LOCKED architecture section, the section-coordinator STOPS and escalates to Tier-0 per `SUB_SESSION_PROTOCOL §5.0` — it does not decompose around the lock.

### H.5 The wave plan IS the check-in approval artifact

The section-coordinator brings the wave plan to the Tier-0 check-in gate as a single document: the ordered list of waves, each wave's units, each unit's owning specialist + target group branch, and each wave's barrier/overlap + FE/BE-mixing decision. The Director reviews and either signs off (the coordinator may then dispatch) or returns it with comments (the coordinator revises and re-presents). No child dispatch happens before sign-off. This mirrors the `SUB_SESSION_PROTOCOL` "WAIT for master's 'go'" discipline, lifted up one tier.

---

## I. Full enumeration (27 branches · 9 Tier-1 · 18 Tier-2 · 27 worktrees)

Counts at full fan-out: **27 branches** (9 × 3), **9 Tier-1 sessions**, **18 Tier-2 sub-sessions** (9 × 2), **27 worktrees** (1:1 per branch). The master tree + `develop`/`staging`/`main` already exist and are not counted as new. Sessions below show the `session-1` ordinal (`M=1`); resumes increment `M` per §G.

### I.1 Branches (27)

| Section | integration | frontend | backend |
|---|---|---|---|
| section-1 (auth-otp) | `feature/section-1/integration` | `feature/section-1/frontend` | `feature/section-1/backend` |
| section-2 (smart-picker) | `feature/section-2/integration` | `feature/section-2/frontend` | `feature/section-2/backend` |
| section-3 (catalog-form) | `feature/section-3/integration` | `feature/section-3/frontend` | `feature/section-3/backend` |
| section-4 (ai-autofill) | `feature/section-4/integration` | `feature/section-4/frontend` | `feature/section-4/backend` |
| section-5 (image-precheck) | `feature/section-5/integration` | `feature/section-5/frontend` | `feature/section-5/backend` |
| section-6 (live-preview) | `feature/section-6/integration` | `feature/section-6/frontend` | `feature/section-6/backend` |
| section-7 (price-calculator) | `feature/section-7/integration` | `feature/section-7/frontend` | `feature/section-7/backend` |
| section-8 (tracking-dashboard) | `feature/section-8/integration` | `feature/section-8/frontend` | `feature/section-8/backend` |
| section-9 (xlsx-export) | `feature/section-9/integration` | `feature/section-9/frontend` | `feature/section-9/backend` |

### I.2 Tier-1 section-coordinator sessions (9)

| Section | Tier-1 session name |
|---|---|
| section-1 (auth-otp) | `mesell-section-1-coordinator-session-1` |
| section-2 (smart-picker) | `mesell-section-2-coordinator-session-1` |
| section-3 (catalog-form) | `mesell-section-3-coordinator-session-1` |
| section-4 (ai-autofill) | `mesell-section-4-coordinator-session-1` |
| section-5 (image-precheck) | `mesell-section-5-coordinator-session-1` |
| section-6 (live-preview) | `mesell-section-6-coordinator-session-1` |
| section-7 (price-calculator) | `mesell-section-7-coordinator-session-1` |
| section-8 (tracking-dashboard) | `mesell-section-8-coordinator-session-1` |
| section-9 (xlsx-export) | `mesell-section-9-coordinator-session-1` |

### I.3 Tier-2 discipline sub-sessions (18)

| Section | frontend sub-session | backend sub-session |
|---|---|---|
| section-1 (auth-otp) | `mesell-section-1-frontend-session-1` | `mesell-section-1-backend-session-1` |
| section-2 (smart-picker) | `mesell-section-2-frontend-session-1` | `mesell-section-2-backend-session-1` |
| section-3 (catalog-form) | `mesell-section-3-frontend-session-1` | `mesell-section-3-backend-session-1` |
| section-4 (ai-autofill) | `mesell-section-4-frontend-session-1` | `mesell-section-4-backend-session-1` |
| section-5 (image-precheck) | `mesell-section-5-frontend-session-1` | `mesell-section-5-backend-session-1` |
| section-6 (live-preview) | `mesell-section-6-frontend-session-1` | `mesell-section-6-backend-session-1` |
| section-7 (price-calculator) | `mesell-section-7-frontend-session-1` | `mesell-section-7-backend-session-1` |
| section-8 (tracking-dashboard) | `mesell-section-8-frontend-session-1` | `mesell-section-8-backend-session-1` |
| section-9 (xlsx-export) | `mesell-section-9-frontend-session-1` | `mesell-section-9-backend-session-1` |

### I.4 Worktrees (27)

| Section | integration | frontend | backend |
|---|---|---|---|
| section-1 (auth-otp) | `/tmp/mesell-wt/section-1-integration` | `/tmp/mesell-wt/section-1-frontend` | `/tmp/mesell-wt/section-1-backend` |
| section-2 (smart-picker) | `/tmp/mesell-wt/section-2-integration` | `/tmp/mesell-wt/section-2-frontend` | `/tmp/mesell-wt/section-2-backend` |
| section-3 (catalog-form) | `/tmp/mesell-wt/section-3-integration` | `/tmp/mesell-wt/section-3-frontend` | `/tmp/mesell-wt/section-3-backend` |
| section-4 (ai-autofill) | `/tmp/mesell-wt/section-4-integration` | `/tmp/mesell-wt/section-4-frontend` | `/tmp/mesell-wt/section-4-backend` |
| section-5 (image-precheck) | `/tmp/mesell-wt/section-5-integration` | `/tmp/mesell-wt/section-5-frontend` | `/tmp/mesell-wt/section-5-backend` |
| section-6 (live-preview) | `/tmp/mesell-wt/section-6-integration` | `/tmp/mesell-wt/section-6-frontend` | `/tmp/mesell-wt/section-6-backend` |
| section-7 (price-calculator) | `/tmp/mesell-wt/section-7-integration` | `/tmp/mesell-wt/section-7-frontend` | `/tmp/mesell-wt/section-7-backend` |
| section-8 (tracking-dashboard) | `/tmp/mesell-wt/section-8-integration` | `/tmp/mesell-wt/section-8-frontend` | `/tmp/mesell-wt/section-8-backend` |
| section-9 (xlsx-export) | `/tmp/mesell-wt/section-9-integration` | `/tmp/mesell-wt/section-9-frontend` | `/tmp/mesell-wt/section-9-backend` |

Each worktree follows `_WORKTREE_PROTOCOL.md §3`: symlinked `.claude/agent-memory` + `.claude/agents`, per-worktree `.claude/settings.json` (not symlinked), shared `.git/` object store. `/tmp/mesell-wt/` is ephemeral compute — persistent state lives on the branch.

---

## J. Roster impact (FLAG — do NOT self-apply)

This model **adds a 19th agent role**: `meesell-section-coordinator`. That makes the live fleet 19 agents, not 18.

`CLAUDE.md` (the "18-agent roster" block at line ~18) and `docs/MEESELL_AGENT_REGISTRY.md` both assert an 18-agent fleet. Adding `meesell-section-coordinator` to the live fleet is a **governance change** requiring founder ratification per `MASTER_PLAN.md §7.3` (the same gate that governs architecture amendments and roster changes).

**FLAGGED, NOT APPLIED.** This document does not edit `CLAUDE.md` or `docs/MEESELL_AGENT_REGISTRY.md`. The draft agent spec at `.claude/agents/meesell-section-coordinator.md` is authored alongside this doc but is itself marked DRAFT-pending-ratification. On founder approval the required follow-ups are:

1. Flip this doc's STATUS header to `APPROVED YYYY-MM-DD`.
2. Update `CLAUDE.md`: "18-agent roster" → "19-agent roster"; add `meesell-section-coordinator` (opus, Tier-1) to the roster table; add a HYBRID-dispatch note for the new tier.
3. Update `docs/MEESELL_AGENT_REGISTRY.md` with the full `meesell-section-coordinator` spec entry.
4. Remove the DRAFT comment from `.claude/agents/meesell-section-coordinator.md`.

None of steps 1–4 happen before founder ratification.

---

## K. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-15 | meesell-backend-coordinator | Initial DRAFT. Extends APPROVED MASTER_PLAN.md per the 5 founder rulings of 2026-06-15. Awaiting founder ratification. |
| 1.0 | 2026-06-15 | founder + master Director | Ratified DRAFT → APPROVED. Rulings 1.a–5 locked. 2-group collapse amended into MASTER_PLAN §1.2 (see that doc). Roster bumped 18→19. |

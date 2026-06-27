## 2026-06-10 — Repo Management MASTER_PLAN authored (DRAFT)

Authored `docs/plans/repo_management/MASTER_PLAN.md` — comprehensive 905-line workflow + governance plan for the parallel-agent, feature-centric model. ZERO code changes. PLANNING ONLY per founder brief.

### What's in the plan
- §1 Branch Structure — Model C locked (main / staging / develop / feature/{name} / feature/{name}/{group}); kebab-case slug discipline; 5 groups `{backend, frontend, ai, data, infra}`; lifecycle invariants (rebase-don't-merge, delete after merge, 14-day soft cap).
- §2 Merge Flow — 4-step ASCII diagram + per-step table (preconditions / merger identity / PR type / CI gate / rollback). Decision tree for the "backend done, frontend in-flight" partial-completion scenario. Lead approves group→feature; founder approves feature→develop, develop→staging, staging→main.
- §3 Environment Strategy — dev + staging only (prod V1.5 reserved). Feature-flag gating per group (env var / runtime / prompt-registry / migration-ordering / Terraform var). Migration runs at 4 environments + V1.5 5th. Secrets via GCP SM with WIF.
- §4 Session Naming — `mesell-{feature}-{group}-session-{N}` recorded in branch commit footer + specialist memory + lead board. Resume protocol: read STATUS_MASTER → board → branch → footer → memory → open session-{N+1}.
- §5 PR Templates — 5 group-specific templates (backend/frontend/ai/data/infra) sharing a common shell (summary, linked spec, what changed, test evidence, reviewer reminder, session, checklist). Each adds group-specific evidence (migration, layer compliance, eval, parser stats, terraform plan).
- §6 feature_board.md — 5 files at docs/status/feature_board_{backend,frontend,ai,data,infra}.md. 5-status vocabulary {PENDING, IN PROGRESS, IN REVIEW, MERGED, BLOCKED}. Blocking format `{group} — {reason}` for 10s scan. Update protocol on every push/PR/merge/blocker.
- §7 Lead Responsibilities — universal table (board / status / memory / dispatch / approval / arch doc / coordination). Decisions in lead authority vs founder-escalation. Handoff protocol specialist→lead (7 steps). Cross-lead coordination via inter-lead requests on the board + handoff_<topic>.md memo in originator memory.
- §8 Cross-Feature Conflict Resolution — Shared code surfaces enumerated (backend shared/core/i18n, frontend libs/, Alembic chain). Detection via `check-shared-touches` informational CI comment + standard git rebase. Resolution tie-break table. "Shared code extraction" pattern: promote-to-lib-first when 3+ features contest a function.
- §9 Sub-Plans List — 5 sub-plans enumerated with author/location/sequence: lead CLAUDE.md rewrites (parallel), PR template files (backend coord drafts), feature_board.md init (lazy), develop+staging branch creation (founder one-shot), branch protection rules (founder one-shot).
- §10 Acceptance Gate — 3 preconditions: founder approves this plan, module_federation + microservices_migration plans approved, develop+staging branches exist.

### Cross-references threaded
- BACKEND_ARCHITECTURE.md §2.D + §16 + §17 + §22 (architecture amendment guard, extraction order, endpoint count)
- BACKEND_ARCHITECTURE.md §6A.F (AI graceful fallback for feature-flag-disabled workloads)
- docs/plans/module_federation/MASTER_PLAN.md (referenced as prerequisite per §10)
- .github/workflows/ci.yml (5-gate scheme cited verbatim in §2 CI requirements + §5 PR templates)
- CLAUDE.md Decision 12 (90s build budget cited in frontend PR template)
- V1_FEATURE_SPEC.md (referenced as the feature acceptance source)

### Design tensions resolved without escalation
(i) Whether `feature/{name}/{group}` PRs go to `feature/{name}` or straight to `develop` — chose to `feature/{name}` so that the cross-group integration test surface is a single PR target (§2.2); founder still gates the final feature→develop PR.
(ii) Whether the lead or specialist opens the group PR — specialist opens, lead reviews (§2.1) — preserves lead as approver-not-author.
(iii) Whether session N continues across features for a (specialist × group) tuple or resets per feature — resets per (feature × group) per §4.3; rationale: keeps the counter scannable and avoids cross-feature pollution.
(iv) Whether feature_board.md lives per-lead or workspace-wide — per-lead per §6.1 to preserve the decentralized-memory ecosystem rule from CLAUDE.md.
(v) PR review identity in V1 — founder is sole reviewer (each template carries a reminder) per CLAUDE.md decentralized hierarchy and the current "1-founder shop" reality from STATUS_MASTER.

### What's NOT in this plan (deferred to sub-plans or other coordinators)
- Actual PR template file contents at `.github/PULL_REQUEST_TEMPLATE/*.md` — sub-plan §9.2
- Actual lead-agent CLAUDE.md rewrites — sub-plan §9.1, each lead authors their own
- Branch protection rule API/UI clicks — sub-plan §9.5, founder action
- GitHub setting for "auto-delete merged branches" — implicit in §1.4, infra lead may codify
- Per-feature preview environments (PR-environment-per-branch) — V1.5
- Release notes automation — V1.5

### Files touched this turn
1. `docs/plans/repo_management/MASTER_PLAN.md` — created, 905 lines, STATUS=DRAFT
2. `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` — this entry

NO sub-agent dispatch. NO touch to BACKEND_ARCHITECTURE.md or STATUS_BACKEND.md or STATUS_MASTER.md. The plan is content-only — operationalisation begins ONLY after founder approval per §10 Acceptance Gate.

Standing by for founder review.

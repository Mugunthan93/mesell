# feature_catalog-form.md — per-feature memo (meesell-backend-coordinator)

Per-feature memo for `catalog-form` (O3 working agreement). Tied to the index entry in `MEMORY.md`.

## Session 1 — 2026-06-10 — Planning session 2 (FEATURE_PLAN.md DRAFT)

**Working on feature:** catalog-form. Memo file: feature_catalog-form.md.

### Outcomes
- Authored `docs/plans/features/catalog-form/FEATURE_PLAN.md` (1,014 lines, 12 top-level sections plus document metadata).
- Branched `feature/catalog-form/planning` off `develop` (HEAD `9a2b25c`).
- Commit `9850e9d` — `docs(plan): lock catalog-form feature blueprint`.
- PR #7 opened to `develop` with backend PR template format: https://github.com/Mugunthan93/mesell/pull/7
- Status DRAFT — awaiting founder review per master plan §2.2 (founder is sole reviewer of `feature/{name}` → `develop`).

### Six decisions locked (verbatim in FEATURE_PLAN.md §2)
- **D1 — Scope:** F3 verbatim + autofill OUT (owned by `ai-autofill` feature)
- **D2 — Feature flag:** `FEATURE_CATALOG_FORM_ENABLED`; dev=true, staging=false until soak passes (5 conditions)
- **D3 — Sprint order:** Lands 3rd — after auth-otp + smart-picker, before any catalog-dependent sibling
- **O1 — Agent lineup:** backend 3 + frontend 3 + data conditional; AI/auth/infra/legal NONE
- **O2 — Branch playbook:** backend lead creates `feature/catalog-form` at first specialist dispatch (lazy)
- **O3 — Per-feature memory hook:** this memo IS the operationalisation; index in `MEMORY.md`

### Locked `assert_product_ownership` signature — TO PUBLISH AT FIRST DISPATCH

This is the contract every sibling feature (`ai-autofill`, `image-precheck`, `live-preview`, `xlsx-export`) will consume per `BACKEND_ARCHITECTURE.md §10.A` + §10.C. I will publish it in the `feature_board_backend.md` Notes column **the moment** `meesell-services-builder` opens its PR, per Risk R5 mitigation.

```python
# app/modules/catalog/service.py — PUBLIC cross-module surface
async def assert_product_ownership(product_id: UUID, user_id: UUID) -> None:
    """Raises ProductNotFoundError (404, code='catalog.product_not_found')
    if the product is not owned by user_id OR if deleted_at IS NOT NULL.

    Consumers per §2.D matrix:
      - app.modules.image.service (catalog → image call)
      - app.modules.pricing.service (catalog → pricing call)
      - app.modules.dashboard.service (catalog → dashboard call)
      - app.modules.export.service (catalog → export call)

    The structural enforcement point for philosophy M6 (ownership-assertion
    seam). NO rename, NO signature variation per §10.C.
    """
```

### Dispatch order plan (when founder greenlights coding stage)
1. **`meesell-database-builder`** first — extends `products`, creates `product_drafts` (UNIQUE on `(user_id, product_id)`), Alembic migration is reversible. Linchpin for all sibling features.
2. **`meesell-api-routes-builder`** + **`meesell-services-builder`** in parallel — once database migration head is locked. Services-builder is the longer-pole task because of the 5-min audit coalescing extension to `core/middleware/audit_mw.py`.
3. **Integration tests** authored by coordinator (me) once all 3 backend PRs merged to `feature/catalog-form` — TestFullProductLifecycle / TestDraftRecoveryAfterSimulatedClose / TestCrossModuleOwnershipAssertion per §10.J.
4. **Frontend dispatches** can begin in parallel with the backend wave; component-builder works against stubbed signatures from §10.B until OpenAPI regenerates.

### Risks tracked (FEATURE_PLAN.md §12)
- R1 — Migration head divergence dev↔staging — P0, mitigated via pre-dispatch `alembic heads` check
- R2 — Autosave hammering Postgres — P1, mitigated via 5-attempt cap + 30s backoff cap + 600/h per-IP RL
- R3 — Change-category UX loses seller data — P1, explicit "Discard fields and switch category" button + silent product_drafts snapshot
- R4 — FieldRenderer fails on unmapped primitive — P2, typed `UnknownPrimitiveError` throw (not silent skip)
- R5 — Downstream siblings race the merge — P1, publish locked signature in board Notes at first dispatch
- R6 — "planning" group token violates master plan §1.2 — P3 governance debt, candidate for §1.2 amendment

### Next session (when founder approves FEATURE_PLAN.md)
- Add `IN PROGRESS` row to `feature_board_backend.md` per master plan §6.5 trigger (at first specialist dispatch, NOT before).
- Create `feature/catalog-form` integration branch off `develop` per O2.
- Create `feature/catalog-form/backend` off `feature/catalog-form` at first specialist dispatch (database-builder).
- Dispatch `meesell-database-builder` using Template 1 from FEATURE_PLAN.md §9.

### File paths touched this session
- `docs/plans/features/catalog-form/FEATURE_PLAN.md` (NEW, 1,014 lines, committed)
- `.claude/agent-memory/meesell-backend-coordinator/feature_catalog-form.md` (NEW, this file)
- `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (MODIFIED — index entry added)
- `docs/status/STATUS_BACKEND.md` (MODIFIED — UPDATE block appended)

### What I did NOT touch (per dispatch hard constraints)
- `feature_board_backend.md` — no row added; deferred to first specialist dispatch per O2 + master plan §6.5
- `docs/plans/features/feature_planning_master.md` — the dispatch did not require me to update it (the original PLANNING_DISPATCH.md Step 0.5 + Step 8 did, but the operative session instructions override and only specify FEATURE_PLAN.md + STATUS_BACKEND.md + memory)
- Any other agent's memory directory (per CLAUDE.md rule #4)
- Any production code path (`backend/app/modules/catalog/`, `frontend/src/app/features/catalog-form/`, alembic versions)
- `feature/catalog-form` integration branch (NOT yet created per O2)

### Deviations from the 6 locked decisions
NONE. Every decision recorded verbatim in FEATURE_PLAN.md §2.

### Outstanding founder action
Review and merge PR #7 to `develop` (founder is sole reviewer per master plan §2.2). After merge, status transitions to LOCKED and the backend lead may dispatch the first specialist per the §9 templates.

## Session mesell-catalog-form-amendment-session-1 — completed

**Date:** 2026-06-10
**Working on feature:** catalog-form. Memo file: feature_catalog-form.md.

### Amendments applied
Brought `docs/plans/features/catalog-form/FEATURE_PLAN.md` into compliance with `docs/plans/features/_CANONICAL_PATTERN.md` v2 (LOCKED 2026-06-10). Renamed two headings (`Branch creation playbook` → `Branch setup`; `Per-feature memory protocol` → `Memory protocol`), relocated the ad-hoc `## Why this feature plan exists` h2 to preamble paragraphs above `## Decisions` (cross-refs updated §9→§7, §10→§8, §12→§10), restructured Risk register with the canonical 6-column summary table at top (R1-R6 detail subsections preserved below), expanded Acceptance gate with V1_FEATURE_SPEC.md §F3.AC1-AC5 verbatim bullets plus pytest/ng-test commands plus explicit CI gate 1-5 rollup plus documentation-deliverable rollup, appended v2 row to Revision history.

### Final FEATURE_PLAN.md line count
1064 (was 1014 — net +50; +106 insertions / -28 deletions / -28 from the relocation dedup).

### Section inventory after amendment
Exactly 11 canonical sections in locked order:
`## Decisions` (line 34) · `## Agent lineup` (124) · `## Code surfaces` (144) · `## Documentation deliverables` (210) · `## Branch setup` (252) · `## Memory protocol` (273) · `## Dispatch templates` (330) · `## Review + iteration protocol` (804) · `## Acceptance gate` (919) · `## Risk register` (980) · `## Revision history` (1059).

### PR state after push
PR #7 was MERGED in the interim (before this session opened); the amendment was pushed on top of `feature/catalog-form/planning` (commits `7ad3ac3` + `b4a641b`) and a NEW PR #15 was opened to `develop` per dispatch Step 7 conditional. PR #15 status: OPEN, awaiting founder review.

### Status file
`docs/plans/features/_status/catalog-form.yaml` created with status `IN_REVIEW`, pr_number `15`, pr_url `https://github.com/Mugunthan93/mesell/pull/15`, feature_plan_line_count `1064`.

### Locked content preserved verbatim (audit)
- The 6 founder decisions (D1/D2/D3/O1/O2/O3) — VERBATIM.
- The `assert_product_ownership(product_id: UUID, user_id: UUID) -> None` cross-module signature — VERBATIM (the contract every sibling feature consumes).
- The 7 dispatch template prompt bodies (3 backend + 3 frontend + 1 conditional data) — VERBATIM.
- All agent-lineup rows in `## Agent lineup` — VERBATIM.
- All code-surface rows in `## Code surfaces` — VERBATIM.
- The R1-R6 risk detail subsections preserved alongside the new summary table.

### Learnings (carry to future amendment sessions)
- Amendment dispatches must check whether the prior session's PR is OPEN, MERGED, or CLOSED before deciding push-on-top vs open-new-PR. PR #7 had merged in the same calendar day, so a new PR #15 was required.
- The dispatch's claim that "Document metadata" was a `##` heading was incorrect — it was the metadata table at the document head (no heading). Audit the file as it actually is, not as the dispatch describes it.
- The Risk register's canonical table form coexists nicely with detailed `### R{N}` subsections (allowed under "subsection depth variance inside any canonical section"). Future amendments can use this pattern for any section that already has rich h3 subsections.
- Inside dispatch-template code fences, lines starting `## ` are NOT real headings — they're paste-able prompt text. `grep -E "^## "` finds them too; filter them out by name when auditing canonical conformance.

### Outstanding founder action
Review and merge PR #15 to `develop`. After merge, the canonical pattern v2 conformance is locked into the catalog-form FEATURE_PLAN.md.

# Sub-Plan 02 — `mfe-export` Extraction (F12)

**STATUS: DRAFT 2026-06-10 — authored under master-session night-run dispatch (S3, session `mesell-module-federation-frontend-session-2`). Awaits founder approval to EXECUTE.**

| Field | Value |
|---|---|
| Document type | Module-federation sub-plan (planning only — zero application-code changes in THIS authoring session) |
| Parent plan | `docs/plans/module_federation/MASTER_PLAN.md` (APPROVED 2026-06-10) §4.2 ordering "2nd" + §5 row 2 |
| Predecessors | `SUB_PLAN_00_workspace_foundation.md` (EXECUTED) + `SUB_PLAN_01_pricing_pilot.md` (the pilot — toolchain MUST be PROVEN per its §9.A before THIS sub-plan starts) |
| Canonical pattern | `docs/plans/features/_CANONICAL_PATTERN.md` v2.1 — 11 sections, locked order |
| Author | meesell-frontend-coordinator (Frontend Lead) |
| Feature slug | `mfe-export` |
| Remote ID | R6 (MASTER_PLAN §2.2) |
| Owned feature | F12 export (CSV/job-polling + download) |
| Owned route | `/catalogs/:id/export` |
| Complexity | **S** (single page, standalone job polling, no AuthService dependency, no neighbour flow) |
| Scope | Extract `features/export/` into a standalone Native-Federation remote; wire the shell route to `loadRemoteWithFallback`; reuse the pilot's validated recipe. Frontend-only. |
| Out of scope | Any other remote; backend; AI; mobile; real-API wiring (Wave 6); CSP cutover (Sub-plan 7) |
| Execution gates | SP01 merged + **SP01 §9.A pilot validation ALL green** (toolchain proven) + founder approval of THIS sub-plan + infra C-CI-1 ready |

`mfe-export` is the **second extraction**, chosen for the same isolation profile as the pilot (MASTER_PLAN §4.2: "Same isolation profile as pricing; reinforces toolchain confidence"). It is the first to **reinforce** rather than discover the toolchain: it copies the pilot's recipe (`sub_plan_01_pricing.md`) verbatim, varying only the component moved and one new wrinkle — the **job-polling timer** (`setInterval` cleaned up in `ngOnDestroy`). The MASTER_PLAN notes export "introduces job-polling pattern which will recur in remote-side data services" — so SP02's risk register adds the timer-lifecycle concern absent from the pilot.

---

## Decisions

D-numbers append-only and monotonic, continuing from SUB_PLAN_01 (which ended at D14). FOUNDER-FLAG marks founder-level calls.

### Adaptations from the canonical V1-feature pattern

Same structural-extraction-zero-behaviour-change shape as SP01. Adaptations: one lead + one specialist (`meesell-angular-component-builder`, MASTER_PLAN §5 row 2); §3 dominated by `MOVE` + the now-established federation scaffolding `NEW` set + one route-swap `MODIFY`; §9 reuses the SP01 acceptance shape minus §9.A (the toolchain is already proven — SP02 only re-confirms it holds).

### D15 — SP02 COPIES the pilot recipe; it does NOT re-derive the toolchain

**Decision.** The `apps/mfe-export/` project shape, `federation.config.js` tokens, `public-api.ts` pattern, the `loadRemoteWithFallback` shell helper, the test-discovery `include` extension, and the Tailwind `content` glob are all COPIED from the as-built `apps/mfe-pricing/` (the pilot) per `sub_plan_01_pricing.md`. SP02 does NOT author a new fallback component or a new helper — both already exist in the shell from SP01 (D12).

**Rationale.** The pilot's entire purpose (§9.A) was to produce a reusable recipe. Re-deriving it in SP02 would waste the pilot's investment and risk divergence between remotes. The strangler-fig cadence (MASTER_PLAN §4.1) explicitly front-loads the learning into the pilot.

**Consequence.** SP02's NEW files are a strict subset of SP01's: `apps/mfe-export/{federation.config.js, src/main.ts, src/app/public-api.ts, tsconfig.app.json}` + the moved component. NO new shell infrastructure (the `RemoteFailureComponent` + `loadRemoteWithFallback` are reused as-is). The shell route swap calls the EXISTING helper: `loadRemoteWithFallback('mfe-export', './ExportComponent')`.

### D16 — The export remote exposes a single component (`./ExportComponent`); `:id` flows via the router exactly like pricing

**Decision.** `mfe-export`'s `federation.config.js` `exposes` exactly one entry: `'./ExportComponent': './apps/mfe-export/src/app/export.component.ts'`. The shell route `catalogs/:id/export` swaps `loadComponent` → `loadRemoteWithFallback('mfe-export', './ExportComponent')`. The `:id` param is read from `ActivatedRoute` inside the remote.

**Rationale.** Identical to D10 (pricing) — export is a single leaf page with no sub-routes (MASTER_PLAN §2.4 single-component expose). Verified: `export.component.ts` injects only `Router` (+ uses `ActivatedRoute` indirectly); no flow guard, no neighbour.

**Consequence.** Uniform with the pilot. Validates that the single-component-expose recipe is reusable (a goal of doing two S-complexity remotes back-to-back before the M/L ones).

### D17 — `export.model.ts` (status types + check builders + mock constants) moves WITH the component; NOT promoted to `libs/core`

**Decision.** The export-private model — `ExportStatus`, `ValidationChecks`, `ValidationCheckItem`, `SIMULATED_PASSING_CHECKS`, `MOCK_DOWNLOAD_URL`, `buildCheckItems`, `allChecksPassed`, `canGenerate` (all in `export.model.ts`, verified on the integration branch) — moves into `apps/mfe-export/src/app/` alongside the component. NOT promoted to `@mesell/core` (no other remote consumes these; grep confirms zero external importers).

**Rationale.** Same as D11 (pricing): MASTER_PLAN §6.5 only promotes cross-boundary types. The export model is internal. **NOTE:** when Wave 6 wires the real export job-status API, the `ExportStatus` enum MAY become a backend-contract type — at THAT point it is a candidate for `@mesell/core/models` (and a frontend↔backend contract memo). For V1 (simulated data, `MOCK_DOWNLOAD_URL`), it stays remote-private. Recorded as a forward note, not a SP02 action.

**Consequence.** `apps/mfe-export/` is self-contained except its shared-lib imports. Confirmed import surface (integration branch):
```
@mesell/ui-kit      → MeeBadgeComponent, MeeButtonComponent, MeeCardComponent, MeeProgressBarComponent
@mesell/composites  → PageHeaderComponent, StatusBadgeComponent
./export.model      → ExportStatus, ValidationChecks/Item, SIMULATED_PASSING_CHECKS, MOCK_DOWNLOAD_URL, buildCheckItems, allChecksPassed, canGenerate  (moves with component)
@angular/router     → Router (framework singleton via shareAll)
```

### D18 — The job-polling timer (`setInterval` / `OnDestroy`) is preserved EXACTLY across the boundary; no rewrite to RxJS

**Decision.** `export.component.ts` implements `OnDestroy` and runs a tick-based progress timer (the `~10 per 500ms → 100% in ~5s` simulation, verified). This timer logic moves UNCHANGED into the remote. SP02 does NOT refactor it to an RxJS `interval()` or a signal-based timer — relocation is behaviour-preserving (D2 lineage).

**Rationale.** The remote is mounted into the shell's router outlet; when the user navigates away, Angular destroys the remote component and `ngOnDestroy` fires exactly as in the monolith — the federation boundary does NOT change component lifecycle. Rewriting the timer would be a logic change that breaks the zero-behaviour-change guarantee and risks a memory leak if mis-done.

**Consequence.** **Risk R-SP2-2 (timer leak across boundary)** is added: the lead must verify in the remote-loads-in-shell test that navigating AWAY from `/catalogs/:id/export` actually destroys the remote component and clears the interval (no orphaned timer). This is the new validation item SP02 adds beyond the pilot's set — and it pre-validates the "remote-side data services" job-polling pattern the MASTER_PLAN flags will recur.

### D19 — Option-C deploy mirrors the pilot: `mfe-export` → `gs://meesell-frontend/{env}/mfe-export/{version}/` at `remotes.mesell.xyz`

**Decision.** Per `GATE4_CONFIRMATION.md` C-RES-2 / C-ROUTE-1, the built `mfe-export` `remoteEntry.json` + chunks upload to the same GCS/CDN surface established by the pilot, under the `mfe-export/{version}/` prefix. The shell manifest gains a second entry. No new infra primitive — the bucket, CDN, `remotes.mesell.xyz` host, GCP cert, and `cloudbuild.remote.yaml` matrix were all stood up by the pilot (SP01 D13 + the infra C-CI-1 deliverable). SP02 is the first to prove the manifest holds MORE THAN ONE remote.

**Rationale.** Reuse. The pilot validated the single-remote deploy; SP02 validates the multi-remote manifest (two entries) — a small but real new surface (does the shell correctly resolve two distinct `remoteEntry.json` URLs?).

**Consequence.** Infra's `cloudbuild.remote.yaml` matrix (C-CI-1, `dorny/paths-filter`) must already fan out per-remote so a change under `apps/mfe-export/` rebuilds ONLY `mfe-export`, not the shell or `mfe-pricing`. SP02's infra memo confirms the matrix covers the new project path. The dev-validation uses localhost-served remotes (no GCS dependency to merge).

### Founder decisions required

**None new.** SP01's FOUNDER-FLAGs D9 (shell stays at `src/`) and D14 (dev-pilot without CSP, CSP deferred to Sub-plan 7) are inherited and apply identically. If the founder resolved them at SP01, SP02 needs no new founder call. No LOCKED-doc amendment.

---

## Agent lineup

| Lead | Specialist dispatched | What the specialist builds |
|---|---|---|
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-component-builder` (sonnet) | Creates `apps/mfe-export/` (copying the pilot's `apps/mfe-pricing/` shape); `git mv`s `features/export/**` into it; rewrites the `app.routes.ts` export entry to the EXISTING `loadRemoteWithFallback` helper; patches the manifest with a second entry; verifies remote builds, shell builds, export tests green, route resolves, remote loads in shell, AND the job-polling timer is cleaned up on navigate-away (D18). |

One lead, one specialist (MASTER_PLAN §5 row 2). No service-builder (export injects only `Router`; its "service" is the local `export.model.ts` simulation). Infra is a cross-lead dependency (D19 memo), not a dispatched specialist.

### Dispatch order (single specialist, serialized phases)

```
PHASE A — scaffold the remote (copy pilot recipe)   meesell-angular-component-builder
   A1. Copy apps/mfe-pricing/ project shape -> apps/mfe-export/ in angular.json (native-federation:build, remote)
   A2. git mv features/export/export/{export.component.ts,export.component.spec.ts,export.model.ts} -> apps/mfe-export/src/app/
   A3. NEW apps/mfe-export/src/app/public-api.ts re-exporting ExportComponent
   A4. NEW apps/mfe-export/federation.config.js name 'mfe-export' exposing './ExportComponent'
   A5. test-discovery include already covers apps/**/*.spec.ts (from SP01) — RE-CONFIRM, do not duplicate
   A6. BUILD CHECKPOINT — `ng build mfe-export` produces remoteEntry.json — record seconds ; HARD GATE

PHASE B — wire the shell (reuse pilot helper)        meesell-angular-component-builder
   B1. app.routes.ts: catalogs/:id/export -> loadRemoteWithFallback('mfe-export','./ExportComponent')
       (NO new helper, NO new fallback component — reuse SP01's)
   B2. public/federation.manifest.json: add "mfe-export" -> "<localhost remoteEntry.json>" (now TWO entries)
   B3. FULL VERIFY — shell build ≤90 s ; export tests green ; total count preserved ;
       boundary clean ; route resolves ; remote LOADS in shell ; TWO remotes coexist in the manifest ;
       navigate-away from export DESTROYS the remote + clears the polling interval (D18 / R-SP2-2)

PHASE C — lead, no specialist                         meesell-frontend-coordinator
   C1. Re-confirm SP01 toolchain still holds (no §9.A re-derivation; just no-regression)
   C2. 360/1280 screenshots of /catalogs/:id/export (no visual change) + timer-cleanup proof
   C3. Infra deploy memo (D19 second-remote GCS prefix + matrix fan-out) + merge-gate review + PR
```

---

## Code surfaces

Exhaustive. Tags: `MOVE` / `MODIFY` / `NEW`. Source paths verified on `feature/mf-workspace-foundation/integration`.

### Relocation — `features/export/` → `apps/mfe-export/src/app/` (3 files incl. spec)

| # | Source (post-SP0) | Target | Tag | Notes |
|---|---|---|---|---|
| 1 | `frontend/src/app/features/export/export/export.component.ts` | `frontend/apps/mfe-export/src/app/export.component.ts` | MOVE | Exposed component. `@mesell/ui-kit` + `@mesell/composites` imports UNCHANGED. `./export.model` stays relative. `OnDestroy` timer logic UNCHANGED (D18). |
| 2 | `frontend/src/app/features/export/export/export.model.ts` | `frontend/apps/mfe-export/src/app/export.model.ts` | MOVE | Status types + check builders + mock constants — remote-private (D17). |
| 3 | `frontend/src/app/features/export/export/export.component.spec.ts` | `frontend/apps/mfe-export/src/app/export.component.spec.ts` | MOVE | Moves with component; MUST stay discovered (R-SP2-3). |

After the move, `frontend/src/app/features/export/` is empty and removed.

### Federation scaffolding — `apps/mfe-export/` (NEW, copies the pilot)

| # | Path | Tag | Description |
|---|---|---|---|
| 4 | `frontend/apps/mfe-export/src/app/public-api.ts` | NEW | Re-exports `ExportComponent` (§6.5 typed boundary). |
| 5 | `frontend/apps/mfe-export/federation.config.js` | NEW | `name: 'mfe-export'`, `exposes: { './ExportComponent': './apps/mfe-export/src/app/export.component.ts' }`, `shareAll` singletons. Copied token-for-token from `mfe-pricing` (only `name` + `exposes` differ). |
| 6 | `frontend/apps/mfe-export/src/main.ts` | NEW | Dev-serve bootstrap (`bootstrapApplication(ExportComponent, {providers:[provideRouter([])]})`). |
| 7 | `frontend/apps/mfe-export/tsconfig.app.json` | NEW | Extends workspace base; references `@mesell/*` paths. |

### Shell wiring (MODIFY only — NO new shell infra)

| # | Path | Tag | Description |
|---|---|---|---|
| 8 | `frontend/src/app/app.routes.ts` | MODIFY | `catalogs/:id/export`: `loadComponent` → `loadRemoteWithFallback('mfe-export', './ExportComponent')` (the EXISTING SP01 helper). All other routes UNCHANGED. |
| 9 | `frontend/public/federation.manifest.json` | MODIFY | Add `"mfe-export"` entry (now `{ "mfe-pricing": "...", "mfe-export": "..." }`). |
| 10 | `frontend/angular.json` | MODIFY | Add `projects.mfe-export` (copy of the `mfe-pricing` target). |
| 11 | `frontend/tsconfig.spec.json` (or shell test `include`) | RE-CONFIRM | `apps/**/*.spec.ts` already added by SP01 — verify it covers `apps/mfe-export/`; do NOT duplicate the glob. |
| 12 | `frontend/postcss.config.mjs` / Tailwind `content` | RE-CONFIRM | `apps/**` glob already added by SP01 — covers `apps/mfe-export/` automatically. No edit expected. |

> **NO** `RemoteFailureComponent` / `load-remote.ts` changes — those are SP01 artefacts, reused as-is (D15).

### Documentation / status / memory

| # | Path | Tag | Description |
|---|---|---|---|
| 13 | `docs/status/feature_board_frontend.md` | MODIFY | `mfe-export` row lifecycle + infra inter-lead row (D19). |
| 14 | `docs/status/STATUS_FRONTEND.md` | MODIFY | Updates Log chunk — build/test numbers, two-remote manifest proof, timer-cleanup proof. |
| 15 | `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_02_export.md` | NEW | Records the job-polling/timer-cleanup learning + the multi-remote manifest proof (forward note for SP03+ and the recurring remote-data-service pattern). |

No backend/AI/data surface. No LOCKED-doc amendment.

---

## Documentation deliverables

Gate conditions in §9. The PR cannot merge to integration without:

1. **`SUB_PLAN_02_export_extraction.md`** (this document) — referenced from MASTER_PLAN §5 row 2.
2. **`sub_plan_02_export.md` memo** — the timer-lifecycle-across-boundary learning + the two-remote manifest proof. The job-polling pattern is flagged as the precedent for any future remote-side data service (MASTER_PLAN §4.2 note).
3. **Infra deploy memo** (`handoff_mf_export_deploy.md`) — second-remote GCS prefix + confirmation the `dorny/paths-filter` matrix fans out per-remote (C-CI-1).
4. **`feature_board_frontend.md` + `STATUS_FRONTEND.md`** current through the lifecycle.
5. **No MASTER_PLAN edit** beyond a §5 row-2 status note in §11.

---

## Branch setup

Feature slug `mfe-export`. Per F1.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/mfe-export/integration` | `develop` (AFTER SP01 merged to develop) | Integration branch; merge commits + §6.5 board flips | Frontend Lead |
| `feature/mfe-export/frontend` | `feature/mfe-export/integration` | ALL export extraction + wiring | `meesell-angular-component-builder` |

No infra group branch cut by this sub-plan (infra hosting is a parallel C-CI-1 effort; the matrix was set up at the pilot). Dev-validation uses localhost-served remotes, so the frontend merge does not block on the GCS upload.

### F1 branch-setup commands (EXECUTION stage)

```bash
git fetch origin develop
git checkout develop && git pull --ff-only          # must include SP01's merge

git checkout -b feature/mfe-export/integration develop
git push -u origin feature/mfe-export/integration

git checkout -b feature/mfe-export/frontend feature/mfe-export/integration
git push -u origin feature/mfe-export/frontend

git worktree add /tmp/mesell-wt/mfe-export feature/mfe-export/frontend
```

### PR flow

```
feature/mfe-export/frontend
        │  PR — Frontend Lead reviews+merges (squash)   [D1]
        ▼
feature/mfe-export/integration
        │  PR — FOUNDER reviews+merges (merge-commit)    [D1]
        ▼
develop
```

Group → integration: Frontend Lead. Integration → develop: Founder (lead must NOT approve). F3 protection on the integration branch; re-probe empirically.

---

## Memory protocol

### Memories the coding-session leads MUST read at start

- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` (own memory)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md` (**THE recipe** — copy it)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_00_workspace.md` (alias map)
- `docs/plans/module_federation/SUB_PLAN_01_pricing_pilot.md` (the proven pilot — esp. §9.A)
- `docs/plans/module_federation/MASTER_PLAN.md` §2.4 (routing), §6.4 (error boundary — reused)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (GATE4 Option-C; C-CI-1 matrix)

### Cross-feature memos

- **Outgoing → infra:** `handoff_mf_export_deploy.md` — second-remote GCS prefix + matrix fan-out confirmation (C-CI-1). 48h SLA. Board inter-lead row added.
- **Forward-reference:** `sub_plan_02_export.md` — timer-lifecycle + two-remote-manifest proof.

### Session-close memory entries

Session header (`## Session mesell-mfe-export-frontend-session-{N}`), D15–D19 outcomes, files-touched count, remote + shell build seconds, test pass count (== SP01-merged baseline), boundary result, the timer-cleanup-on-navigate-away proof (D18), the two-remote manifest proof, blockers, next-step (Sub-plan 3 onboarding — the AuthService singleton sub-plan).

---

## Dispatch templates

### meesell-angular-component-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-export-frontend-session-1

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_02_export_extraction.md (this plan — D15-D19, §3, §9)
- .claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md (THE recipe to copy)
- docs/plans/module_federation/SUB_PLAN_01_pricing_pilot.md (the proven pilot)
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (apps/**/*.spec.ts test-discovery fix; pnpm rebuild fix; deep-import bundle landmine)
- docs/plans/module_federation/MASTER_PLAN.md §6.4 (error boundary — REUSE SP01's RemoteFailureComponent, do NOT re-author)

## Your mission
PHASE A: COPY the apps/mfe-pricing/ project shape -> apps/mfe-export/ (angular.json native-federation:build remote). `git mv` features/export/export/{export.component.ts,export.component.spec.ts,export.model.ts} -> apps/mfe-export/src/app/ (history preserved; @mesell/* + ./export.model imports UNCHANGED; OnDestroy timer UNCHANGED). NEW apps/mfe-export/src/app/public-api.ts (re-export ExportComponent). NEW apps/mfe-export/federation.config.js name 'mfe-export' exposing { './ExportComponent': './apps/mfe-export/src/app/export.component.ts' }. NEW apps/mfe-export/src/main.ts dev bootstrap. BUILD CHECKPOINT: `ng build mfe-export` -> remoteEntry.json (record seconds). HARD GATE.
PHASE B: app.routes.ts catalogs/:id/export -> loadRemoteWithFallback('mfe-export','./ExportComponent') — REUSE the existing SP01 helper, do NOT create a new one. public/federation.manifest.json: ADD "mfe-export" (now TWO entries). FULL VERIFY (see acceptance) including: navigate AWAY from the export route and prove the remote component is destroyed + the polling interval is cleared (no orphan timer).

## Acceptance criteria
- [ ] apps/mfe-export/ holds the 3 moved files + public-api + federation.config + main.ts; features/export/ removed
- [ ] `ng build mfe-export` GREEN -> remoteEntry.json (record seconds)
- [ ] shell `pnpm build` GREEN ≤ 90 s (record seconds + initial bundle delta)
- [ ] `pnpm test` total == SP01-merged baseline, 0 failing, 0 skipped (a count DROP = export spec not discovered = HARD REJECT)
- [ ] boundary grep clean (no new primeng leak from apps/mfe-export/)
- [ ] route /catalogs/:id/export resolves; remote ExportComponent RENDERS in shell; :id read correctly
- [ ] manifest has BOTH mfe-pricing AND mfe-export; both resolve when served
- [ ] navigate-away DESTROYS the remote + CLEARS the polling interval (D18 — no orphan setInterval); demonstrate
- [ ] deliberate-broken manifest -> the existing RemoteFailureComponent renders (reused, not re-authored)

## Hard constraints
- ZERO logic/template edits to export.component/model — relocation only (incl. the timer; do NOT rewrite to RxJS — D18)
- Do NOT promote export.model to libs/core (D17 — remote-private for V1)
- Do NOT author a new RemoteFailureComponent or loadRemoteWithFallback (D15 — reuse SP01's)
- Do NOT move the shell into apps/shell/ (D9 inherited); do NOT author CSP (D14 inherited)
- Do NOT touch backend/, k8s/, infra/, OR any other feature/remote

## Files you MAY touch
- frontend/apps/mfe-export/** (new), frontend/angular.json (add mfe-export project), frontend/public/federation.manifest.json
- frontend/src/app/app.routes.ts (export entry only)
- (RE-CONFIRM only, no edit expected: tsconfig.spec include + Tailwind content already cover apps/**)

## Files you must NOT touch
- frontend/apps/mfe-pricing/** (the pilot — done); frontend/src/app/core/{remote-failure.component.ts,load-remote.ts} (reuse, don't edit); libs/**; SHELL federation.config.js; backend/k8s/infra

## Final report format
Files moved/new counts, remote build seconds, shell build seconds + bundle delta, test count (== baseline), boundary output, route + remote-loads proof, two-remote-manifest proof, timer-cleanup proof. Then STOP for lead review + PR.
```

---

## Review + iteration protocol

### meesell-angular-component-builder

- **Pre-approval checklist (lead inspects):** (a) `git log --follow` shows preserved history on the 3 moved files; (b) `export.component.ts` diff is empty except path context — timer/template/compute UNCHANGED (D18); (c) `apps/mfe-export/federation.config.js` `name:'mfe-export'` + one `exposes`; (d) NO new `RemoteFailureComponent` / helper (D15 — `git status` shows shell core/ unchanged); (e) manifest has exactly TWO entries; (f) test count == SP01-merged baseline (drop = hard reject, R-SP2-3); (g) shell build ≤90 s; (h) the timer-cleanup-on-navigate-away was demonstrated (D18 / R-SP2-2).
- **PR-template gate:** `.github/PULL_REQUEST_TEMPLATE/frontend.md` complete, no `<>`. Build evidence, bundle delta, 360/1280 screenshots (no visual change), a11y, boundary output, remote-loads + two-remote-manifest + timer-cleanup proofs.
- **Re-dispatch triggers:** "rewrote the timer to RxJS / edited export logic" → re-dispatch quoting D18; "re-authored fallback or helper" → re-dispatch quoting D15; "test count dropped" → re-dispatch with the count + the `apps/**/*.spec.ts` include note; "promoted export.model to libs/core" → re-dispatch quoting D17; "orphan timer after navigate-away" → re-dispatch quoting D18/R-SP2-2; "shell federation.config.js mutated" → re-dispatch (remotes go in the manifest).
- **Re-dispatch prompt shape:** original prompt + "Previous run failed on X (paste output); fix only that; re-run build + test + boundary + remote-loads + timer-cleanup proof."
- **Iteration cap: 3.** Third re-dispatch auto-escalates to founder.

---

## Acceptance gate

When every box is `[x]`, `feature/mfe-export/integration` is ready for the founder's develop PR.

- [ ] PR (`feature/mfe-export/frontend` → integration) merged by Frontend Lead (squash)
- [ ] `ng build mfe-export` GREEN — produces `remoteEntry.json` + chunks (record seconds)
- [ ] Shell `pnpm build` GREEN and **≤ 90 s** (Stop Condition) — seconds + bundle delta in PR + STATUS
- [ ] `pnpm test` total == **SP01-merged baseline, 0 failing, 0 skipped** — new failure OR count drop blocks merge (R-SP2-3)
- [ ] **Boundary grep clean** — no new PrimeNG leak from `apps/mfe-export/`
- [ ] **Route resolves:** `/catalogs/:id/export` activates; the remote `ExportComponent` renders in the shell outlet; `:id` read correctly
- [ ] **Remote loads in shell** (served shell + served remote) — proven
- [ ] **Two remotes coexist:** the manifest has `mfe-pricing` + `mfe-export`; navigating to each loads the correct remote (the first multi-remote-manifest proof)
- [ ] **Timer cleanup proven (D18 / R-SP2-2):** navigating away from `/catalogs/:id/export` destroys the remote component and clears the `setInterval` — no orphan timer (the precedent for remote-side data services)
- [ ] **Fallback reused (D15):** the SP01 `RemoteFailureComponent` handles a broken manifest URL — NOT a re-authored component
- [ ] FOUNDER-FLAGs D9 + D14 inherited from SP01 (no new founder call)
- [ ] Infra deploy memo filed (D19 — second GCS prefix + matrix fan-out); board inter-lead row added
- [ ] `feature_board_frontend.md` row = MERGED; STATUS_FRONTEND.md appended; `sub_plan_02_export.md` memo written
- [ ] **Founder approval** on `feature/mfe-export/integration` → `develop` (founder's gate, NOT the lead's)

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-SP2-1 | **Recipe divergence from the pilot** — the specialist hand-rolls a slightly different `apps/mfe-export/` shape instead of copying `apps/mfe-pricing/`, introducing config drift between remotes. | Medium | Medium | D15 mandates copying the pilot. Lead diffs `apps/mfe-export/federation.config.js` against `apps/mfe-pricing/federation.config.js` — only `name` + `exposes` may differ. Any other delta is a re-dispatch. |
| R-SP2-2 | **Job-polling timer leaks across the federation boundary** — `setInterval` not cleared when the remote unmounts; orphan timer keeps ticking after navigate-away, leaking memory + (in Wave 6) firing API polls for a closed page. | Medium | High | D18: `ngOnDestroy` clears the interval; the federation boundary does NOT alter component lifecycle (the host destroys the remote on navigation). §9 mandates a demonstrated navigate-away-clears-timer proof. This pre-validates the remote-side data-service polling pattern the MASTER_PLAN §4.2 says will recur. |
| R-SP2-3 | **Spec-discovery regression** — moving `export.component.spec.ts` into `apps/mfe-export/` is fine ONLY because SP01 already extended the test glob to `apps/**/*.spec.ts`. If the specialist forgets to RE-CONFIRM (or a per-project tsconfig overrides it), the spec silently stops running. | Medium | High | RE-CONFIRM (not re-add) the `apps/**/*.spec.ts` glob covers the new project; assert the EXACT total count == SP01-merged baseline; a drop is a hard reject. (Same recipe as SP01 §9.A item 6 / SP0 R6.) |
| R-SP2-4 | **Multi-remote manifest resolution bug** — the shell resolves the FIRST manifest entry but not the second (a Native Federation init ordering quirk). | Low | High | §9 mandates a TWO-remote proof: both `/catalogs/:id/pricing` AND `/catalogs/:id/export` must load their respective remotes in the same session. This is the new surface SP02 adds vs the single-remote pilot. If it fails, halt + escalate (it would block ALL further extractions). |
| R-SP2-5 | **`ExportStatus` premature promotion** — a future Wave-6 backend contract tempts the specialist to promote `export.model.ts` to `libs/core` now. | Low | Medium | D17: V1 export uses simulated data (`MOCK_DOWNLOAD_URL`); the model stays remote-private. Promotion is a Wave-6 + frontend↔backend-contract decision, NOT a SP02 action. Recorded as a forward note in `sub_plan_02_export.md`, not executed. |
| R-SP2-6 | **CSP blocks the second remote in staging/prod.** | Low (dev) / High (prod) | High | Inherited from SP01 R-SP1-4 / D14: dev has no CSP; CSP authoring is deferred to Sub-plan 7 before staging/prod. Do NOT ship `mfe-export` to staging/prod before CSP covers `remotes.mesell.xyz`. |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 (DRAFT) | 2026-06-10 | `mesell-module-federation-frontend-session-2` (night-run master-session dispatch) | Initial authoring of Sub-Plan 02 — `mfe-export`. Grounded in the POST-SP0 integration-branch reality (`e51761b`): export is 3 self-contained files (component+spec+model) consuming `@mesell/ui-kit`+`@mesell/composites`, NO AuthService, with an `OnDestroy` job-polling timer. D15 (copy the pilot recipe — no toolchain re-derivation), D16 (single-component expose), D17 (remote-private model, Wave-6 promotion forward note), D18 (preserve the timer EXACTLY — no RxJS rewrite + the navigate-away cleanup proof), D19 (second-remote Option-C GCS prefix + matrix fan-out). No new FOUNDER-FLAGs (D9/D14 inherited). 6 risks incl. the timer-leak-across-boundary (R-SP2-2, the precedent for remote-side polling) + the multi-remote manifest proof (R-SP2-4, the new surface beyond the pilot). Awaits founder approval; gated on SP01 merge + SP01 §9.A toolchain-proven. |

# Sub-Plan 00 — Workspace Foundation

**STATUS: DRAFT 2026-06-10 — authored under master-session dispatch (S3). Awaits founder approval to EXECUTE.**

| Field | Value |
|---|---|
| Document type | Module-federation sub-plan (planning only — zero application-code changes in THIS authoring session) |
| Parent plan | `docs/plans/module_federation/MASTER_PLAN.md` (APPROVED 2026-06-10, FEDERATION FIRST) §5 row 0 |
| Canonical pattern | `docs/plans/features/_CANONICAL_PATTERN.md` v2.1 — 11 sections, locked order |
| Author | meesell-frontend-coordinator (Frontend Lead) · session `mesell-module-federation-frontend-session-1` |
| Feature slug | `mf-workspace-foundation` |
| Scope | Frontend workspace reorganisation only — `frontend/` at `/Users/mugunthansrinivasan/Project/mesell/frontend/` |
| Out of scope | Any remote extraction (Sub-plans 1–7); backend; AI prompts; mobile/Ionic; real-API wiring (Wave 6) |
| Execution gates | Gate 3 (TestBed-38 triage — SATISFIED, `TESTBED_TRIAGE.md`, N=0) + Gate 4 (infra hosting — CONFIRMED-WITH-CONDITIONS, `GATE4_CONFIRMATION.md`) + founder approval of THIS sub-plan |

This sub-plan is the **prerequisite for all six remote extractions**. It changes zero feature behaviour: it relocates the shared layers into `libs/`, rewrites import paths to package aliases, installs Native Federation, and scaffolds the empty shell project — leaving every route, every component, and all 392 tests behaving exactly as on develop tip `a391671`.

---

## Decisions

This section captures the lead-level decisions (D-numbered) made while authoring Sub-Plan 0, plus the founder-level calls that must be answered before execution. Per `_CANONICAL_PATTERN.md` §1, D-numbers are append-only and monotonic.

### Adaptations from the canonical V1-feature pattern

`_CANONICAL_PATTERN.md` v2.1 was written for a **V1 product feature** (a user-facing slice that touches backend + frontend + maybe ai/data/infra). Sub-Plan 0 is a **frontend-only structural refactor with zero behaviour change**. The 11 sections are all present in the locked order, with these adaptations noted up front:

- **§2 Agent lineup** — only one lead (frontend) and at most two specialists. No cross-track lineup.
- **§3 Code surfaces** — the inventory is dominated by *moves* (git `mv`) and *path rewrites*, not net-new logic. A `MOVE` tag is introduced alongside `NEW`/`MODIFY` because a relocation is neither a clean create nor an in-place edit.
- **§4 Documentation deliverables** — there is no OpenAPI / prompt-registry / V1_FEATURE_SPEC §F-stamp here. The deliverables are an architecture amendment (boundary allowlist) + STATUS + board + memory.
- **§5 Branch setup** — uses the F1 integration-branch form (`feature/mf-workspace-foundation/integration`) and decides on the infra group's involvement (see D5).
- **§9 Acceptance gate** — the founder gate is on the integration→develop PR per D1, but the substance is "no regression": build green ≤90 s, 392/392 tests still green, 4-layer boundary grep still clean.

### D1 — `libs/` is a `tsconfig` path-alias workspace, NOT a separate-build Angular library project (for THIS sub-plan)

**Decision.** The four `libs/` packages (`ui-kit`, `composites`, `core`, `design-tokens`) are created as **source folders under `frontend/libs/` exposed via `tsconfig.json` `paths` aliases** (`@mesell/ui-kit`, `@mesell/composites`, `@mesell/core`, `@mesell/design-tokens`). They are NOT yet `ng-packagr`/`@angular/build:ng-packagr` library projects with their own `ng build` target.

**Rationale.**
- Sub-Plan 0's only job is to *relocate and re-alias* — the federation singleton mechanism (import-maps via Native Federation) does not require the shared code to be a separately-compiled npm package. It requires a stable import specifier (`@mesell/core`) that the federation manifest can declare `singleton: true`.
- Keeping `libs/` as path-aliased source preserves the single esbuild pass (`@angular/build:application`) and therefore the 2.7 s baseline — turning each lib into a separately-built package would add N `ng-packagr` builds and risk the 90 s budget on day one.
- Promotion to true buildable libraries (if ever needed for independent versioning) is a clean later step that does not change consumer import specifiers — `@mesell/core` stays `@mesell/core`.

**Consequence.** The MASTER_PLAN §2.3 phrase "npm-style workspace packages" is satisfied by the alias form for V1. The federation `singleton` declaration (Sub-Plan 1+) points at the alias. No `package.json` per lib in Sub-Plan 0.

### D2 — Relocation is pure `git mv` + alias rewrite; ZERO content edits to component logic

**Decision.** Every one of the 34 relocations is performed with `git mv` so history is preserved, and the ONLY content change permitted to a moved file is the rewrite of its *own* relative imports (e.g. a composite that imports `../../ui` becomes `@mesell/ui-kit`). No refactor, no rename of a class, no template change, no API change.

**Rationale.** N=0 regression baseline (`TESTBED_TRIAGE.md`): any test failure after relocation is a NEW regression. The smallest-possible-diff rule makes a regression trivially bisectable to a single mis-rewritten import.

**Consequence.** PR diff is mechanical and reviewable line-by-line. The `## Review + iteration protocol` (§8) hard-rejects any logic change smuggled into a relocation commit.

### D3 — `core/` (Layer 0) relocates to `libs/core` NOW, even though the §4 service layer is not built

**Decision.** Move the three existing `core/` files (`services/auth.service.ts`, `guards/auth.guard.ts`, `theme/meesell-preset.ts`) into `libs/core/` and alias as `@mesell/core` in Sub-Plan 0. The not-yet-built §4 services (ApiClient, interceptors, ErrorService, NetworkService — absent per knowledge-sync) will be born directly in `libs/core` during Wave 6, which now runs *after* federation per the federation-first ruling.

**Rationale.** MASTER_PLAN §6.1 makes `AuthService` the singleton that the federation manifest declares. It must live at `@mesell/core` before any remote can `inject(AuthService)` and resolve the shell's instance. Relocating it now (while it is a tiny in-memory signal store with no HTTP) is far cheaper than relocating it later once interceptors hang off it. Federation-first ordering is precisely what makes this the right time.

**Consequence.** `app.config.ts` import of `./core/theme/meesell-preset` and `app.routes.ts` import of `./core/guards/auth.guard` become `@mesell/core` imports. `core/theme/meesell-preset.ts` is config-layer styling and is legitimately consumed by `app.config.ts` (the documented root-config exception — see D6).

### D4 — `design-system/_tokens.css` relocates to `libs/design-tokens`; it stays a single global CSS import (NOT a federation singleton)

**Decision.** Move `design-system/_tokens.css` → `libs/design-tokens/_tokens.css`, alias the folder as `@mesell/design-tokens` for any future `@use`, and update `src/styles.css`'s `@import "./app/design-system/_tokens.css"` to point at the new path. Per MASTER_PLAN §2.3 design-tokens is NOT a runtime singleton — it is pure CSS variables on `:root`, loaded once by the shell's global stylesheet.

**Rationale.** Layer 1 is "pure CSS/SCSS, survives any library swap" (FRONTEND_ARCHITECTURE §Layer 1). It needs no federation treatment — remotes inherit the `--mee-*` / `--p-*` variables because the shell injects them into `:root`. Relocating it keeps all four shared layers under one `libs/` roof for a coherent boundary-grep.

**Consequence.** Single line change in `src/styles.css`. No component imports design-system directly today (verified: only `src/styles.css` references it).

### D5 — The infra group is NOT in scope for Sub-Plan 0; CI changes are PREPARED-FOR but not authored here

**Decision.** Sub-Plan 0 creates **only** `feature/mf-workspace-foundation/frontend` (+ the integration branch). **No `feature/mf-workspace-foundation/infra` branch is cut.** The CI matrix / paths-filter / cloudbuild split (GATE4 condition C-CI-1) is owned by `meesell-infra-builder` and lands as a *separate* infra effort (infra plan sub-plans MF-CI-1…4), triggered when the multi-project workspace shape actually requires per-project builds — which is Sub-Plan 1 (first remote), NOT Sub-Plan 0.

**Rationale.**
- Sub-Plan 0 produces a workspace that still builds as **one** `ng build` target (the shell consuming `libs/` via aliases). There are no independently-built units yet, so there is nothing for a paths-filter matrix to fan out to. The existing single-frontend CI (gate-1 unit, gate-3 lint, build-frontend) continues to work unchanged against the reorganised tree.
- GATE4 C-CI-1 says the single-frontend conditional "must be replaced, not extended, **when the multi-project Angular workspace lands**". The multi-project *build* topology lands at the first remote extraction (Sub-Plan 1), not at the libs-relocation (Sub-Plan 0). Forcing the CI rewrite into Sub-Plan 0 would couple a frontend refactor to an infra rewrite and violate the smallest-diff rule.
- Per repo-management §1.2, "a group only gets a branch if and when that group has work to do for that feature." Infra has no work in Sub-Plan 0.

**Consequence.** A cross-lead memo is filed to `meesell-infra-builder` (see §6) flagging that the CI rewrite (C-CI-1) must be ready *before* Sub-Plan 1 opens, and that the reorganised tree changes `frontend/src/app/**` paths the existing build config globs over — infra must confirm the existing `build-frontend` job still resolves the new layout. This is a 48h-SLA inter-lead request, NOT a blocker for Sub-Plan 0 authoring.

### D6 — The two known boundary leaks are PARTIALLY fixed in scope; the §2 architecture carve-out is documented, the shell wrappers are DEFERRED to Sub-Plan 6 (auth/shell)

**Decision.** Of the two real PrimeNG-outside-`ui/` leaks found in the knowledge-sync:

1. **`app.config.ts` importing `providePrimeNG` / `MessageService` / `ConfirmationService`** — this is the legitimate root-config exception. Sub-Plan 0 **documents** it by amending FRONTEND_ARCHITECTURE §2 with an explicit allowlist (root app-config + theme-preset config layer may import PrimeNG providers). This amendment requires founder approval (doc is LOCKED) — see Founder decisions required, FD1.
2. **`layouts/shell/shell.component.ts` importing `Drawer` / `Menu` / `MenuItem` directly from primeng** — this is a genuine Layer-3 leak with no `mee-*` wrapper to delegate to. Sub-Plan 0 **does NOT fix this** (it would mean authoring new `MeeDrawer` + `MeeMenu` wrappers in `libs/ui-kit`, which is net-new component work that violates D2's zero-logic-change rule and risks the N=0 baseline). It is **deferred to Sub-Plan 6** (mfe-auth/shell extraction), where the shell chrome is touched anyway. Sub-Plan 0 records the leak as a tracked risk (R2) and adds a temporary documented exception to §2 (shell-chrome carve-out) so the boundary-grep gate in §9 has a known, enumerated allowlist rather than a silent violation.

**Rationale.** Relocating the leak is orthogonal to fixing it. Forcing the wrapper work into Sub-Plan 0 conflates a refactor with a feature and breaks the smallest-diff guarantee. But leaving the leak *undocumented* would make the §9 boundary-grep gate ambiguous ("is shell's primeng import a regression or pre-existing?"). The carve-out makes the gate deterministic.

**Consequence.** The §9 boundary gate is phrased as: "PrimeNG imports appear ONLY under `libs/ui-kit/`, EXCEPT the two enumerated carve-outs (root app-config providers; shell-chrome Drawer/Menu — tracked for Sub-Plan 6 remediation)." Any *third* leak is a regression.

### D7 — Native Federation is INSTALLED + a federation manifest scaffold is committed, but NO remote is wired and NO `loadRemoteModule` call is added

**Decision.** Sub-Plan 0 adds `@angular-architects/native-federation@^21` to `package.json`, runs its `ng add`/init to produce the `federation.config.js` (or `federation.manifest.json` scaffold) + the `esbuild`-compatible bootstrap split (`main.ts` → `bootstrap.ts` via `initFederation()`), and verifies the build still produces a working shell. It does NOT register any remote, does NOT add any `loadRemoteModule(...)` route, and does NOT split the shell into host+remote topology. All routes remain `loadComponent`/`loadChildren` exactly as today.

**Rationale.** MASTER_PLAN §3 locked Native Federation precisely to preserve the `@angular/build:application` esbuild builder. Installing + initialising it (the bootstrap split + manifest scaffold) is the foundation; wiring remotes is Sub-Plan 1's pilot. Doing the install in Sub-Plan 0 de-risks the toolchain on a zero-remote surface so Sub-Plan 1 starts from a known-good federation init.

**Consequence.** CLAUDE.md Decision 12 gate: "Add Module Federation runtime code before founder approves the master plan — gated." The master plan is APPROVED, so federation *install + init* is now permitted. But Sub-Plan 0 deliberately stops short of *runtime remote loading* — that is Sub-Plan 1, gated on Sub-Plan 0 merging. Build-time budget (Stop Condition) is re-measured after the federation init lands; if the init pushes the shell build past 90 s, HALT and escalate (Risk R5).

### Founder decisions required

Kept to the genuine minimum. Two items; both are founder-level because they touch a LOCKED doc or a cost/scope boundary.

**FD1 — Amend the LOCKED `FRONTEND_ARCHITECTURE.md` §2 with a PrimeNG-import allowlist (root app-config + shell-chrome carve-out).**
The doc is LOCKED end-to-end (2026-06-05); §7.3 of repo-management requires founder approval for any amendment to a LOCKED section. The amendment adds a documented carve-out: PrimeNG may be imported (a) by the root `app.config.ts` for provider wiring (`providePrimeNG`, `MessageService`, `ConfirmationService`) and the `meesell-preset` theme config, and (b) temporarily by `layouts/shell/` for Drawer/Menu chrome pending `MeeDrawer`/`MeeMenu` wrappers in Sub-Plan 6. Without this approval the §9 boundary-grep gate cannot be made deterministic. **One-line ask:** approve adding the two-item PrimeNG-import allowlist to FRONTEND_ARCHITECTURE §2.

**FD2 — Confirm the `mf-workspace-foundation` integration→develop PR is the founder's gate (per D1), and that Sub-Plan 0 EXECUTION is authorised once FD1 + Gates 3+4 are green.**
Authoring is unblocked (this document). Execution is gated. The founder confirms: (a) FD1 approved, (b) the founder personally merges `feature/mf-workspace-foundation/integration` → `develop` per repo-management §2.2. **One-line ask:** authorise execution and confirm founder ownership of the integration→develop gate.

---

## Agent lineup

| Lead | Specialists dispatched | What each specialist builds |
|---|---|---|
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-component-builder` (sonnet) | Relocates `ui/` (28 files) → `libs/ui-kit` and `shared/` (6 files) → `libs/composites`; rewrites the 34 `../ui` + 8 `../shared` import lines across consumers to `@mesell/ui-kit` / `@mesell/composites`; relocates `design-system/_tokens.css` → `libs/design-tokens` + the `styles.css` import line; verifies 392/392 tests + boundary grep. |
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-service-builder` (sonnet) | Relocates `core/` (3 files) → `libs/core`; rewrites the `@mesell/core` consumer imports (`app.config.ts`, `app.routes.ts`, `shell.component.ts`, `otp-verify`, `profile`); installs `@angular-architects/native-federation@^21`, runs the federation init (bootstrap split + manifest scaffold), wires the `tsconfig.json` `paths` aliases + the federation `esbuild` builder config; verifies build ≤90 s. |

Only the Frontend Lead has work (D5: infra deferred). No backend/ai/data lineup.

### Dispatch order (critical path)

```
PHASE A (serialize — alias scaffold first)        meesell-angular-service-builder
   A1. Create libs/{ui-kit,composites,core,design-tokens} folders + tsconfig paths aliases
   A2. git mv core/ -> libs/core; rewrite @mesell/core consumer imports
   A3. Install native-federation@^21; ng add init; bootstrap split; manifest scaffold; builder config
   A4. Build green checkpoint (shell builds, ≤90 s) — HARD GATE before Phase B

PHASE B (after A merges to integration OR on the same branch, sequenced)   meesell-angular-component-builder
   B1. git mv ui/ -> libs/ui-kit (28 files); rewrite 34 ../ui import lines -> @mesell/ui-kit
   B2. git mv shared/ -> libs/composites (6 files); rewrite 8 ../shared import lines -> @mesell/composites
   B3. git mv design-system/_tokens.css -> libs/design-tokens; rewrite styles.css import
   B4. Full verification: pnpm build ≤90 s; pnpm test 392/392; boundary grep clean

PHASE C (lead, no specialist)                     meesell-frontend-coordinator
   C1. Boundary-grep gate + route-resolution smoke + 360/1280 screenshots (no visual change expected)
   C2. FRONTEND_ARCHITECTURE §2 allowlist amendment (pending FD1)
   C3. Merge-gate review + integration PR
```

Phase A and Phase B both touch `tsconfig.json` and could collide; A owns the aliases file, B only reads it. To avoid a rebase collision the lead may run both specialists on the SAME `feature/mf-workspace-foundation/frontend` branch sequentially (A then B) rather than two parallel group branches — there is only one frontend group branch per repo-management §1.2, so this is the natural shape.

---

## Code surfaces

Exhaustive inventory. Tags: `MOVE` (git mv, history-preserving, no logic change), `MODIFY` (in-place edit — import rewrite or config), `NEW` (net-new file).

### Frontend — Layer 2 relocation (`ui/` → `libs/ui-kit`, 28 source files)

| # | Path (target) | Tag | Description | Owner |
|---|---|---|---|---|
| 1 | `libs/ui-kit/index.ts` (from `src/app/ui/index.ts`) | MOVE | Barrel — re-exports all 17 `mee-*` primitives + 2 services | component-builder |
| 2–4 | `libs/ui-kit/button/{button.component.ts,button.types.ts}` (+ 1 more if present) | MOVE | MeeButton + variant/size types | component-builder |
| 5–6 | `libs/ui-kit/input/input.component.ts` | MOVE | MeeInput | component-builder |
| 7 | `libs/ui-kit/otp-input/otp-input.component.ts` | MOVE | MeeOtpInput | component-builder |
| 8 | `libs/ui-kit/textarea/textarea.component.ts` | MOVE | MeeTextarea | component-builder |
| 9 | `libs/ui-kit/password-input/password-input.component.ts` | MOVE | MeePasswordInput | component-builder |
| 10–11 | `libs/ui-kit/badge/{badge.component.ts,badge.types.ts}` | MOVE | MeeBadge + severity type | component-builder |
| 12 | `libs/ui-kit/card/card.component.ts` | MOVE | MeeCard | component-builder |
| 13–14 | `libs/ui-kit/table/{table.component.ts,table.types.ts}` | MOVE | MeeTable + column/page/sort types | component-builder |
| 15 | `libs/ui-kit/dialog/dialog.component.ts` | MOVE | MeeDialog | component-builder |
| 16–17 | `libs/ui-kit/file-upload/{file-upload.component.ts,file-upload.types.ts}` | MOVE | MeeFileUpload + event type | component-builder |
| 18–19 | `libs/ui-kit/steps/{steps.component.ts,steps.types.ts}` | MOVE | MeeSteps + step type | component-builder |
| 20–21 | `libs/ui-kit/select/{select.component.ts,select.types.ts}` | MOVE | MeeSelect + option type | component-builder |
| 22 | `libs/ui-kit/tree-select/tree-select.component.ts` | MOVE | MeeTreeSelect + MeeTreeNode type (inline) | component-builder |
| 23–24 | `libs/ui-kit/skeleton/{skeleton.component.ts,skeleton.types.ts}` | MOVE | MeeSkeleton + variant type | component-builder |
| 25 | `libs/ui-kit/progress-bar/progress-bar.component.ts` | MOVE | MeeProgressBar | component-builder |
| 26 | `libs/ui-kit/toast/toast.component.ts` + `toast/toast.service.ts` | MOVE | MeeToast + MeeToastService | component-builder |
| 27 | `libs/ui-kit/confirm-dialog/confirm-dialog.component.ts` | MOVE | MeeConfirmDialog + MeeConfirmService + MeeConfirmConfig | component-builder |
| 28 | (PrimeNG-internal import lines inside the moved primitives are UNCHANGED — PrimeNG legitimately lives in Layer 2) | MOVE | All 28 source files move with `git mv`; the 17 corresponding `.spec.ts` files move alongside (not counted in the 28 — they are spec siblings) | component-builder |

> **Reconciliation of the "28" count.** `find src/app/ui -type f ! -name '*.spec.ts'` = **28** source files (17 component dirs; several have a `.types.ts` companion + the barrel `index.ts` + the 2 `.service.ts`). The 17 `.spec.ts` files move with their components but are not part of the 28-source figure. Verified on develop tip `a391671`.

### Frontend — Layer 3 composites relocation (`shared/` → `libs/composites`, 6 source files)

| # | Path (target) | Tag | Description | Owner |
|---|---|---|---|---|
| 29 | `libs/composites/index.ts` (from `src/app/shared/index.ts`) | MOVE | Composites barrel | component-builder |
| 30 | `libs/composites/stat-card/stat-card.component.ts` | MOVE | MeeStatCard | component-builder |
| 31 | `libs/composites/status-badge/status-badge.component.ts` | MOVE | MeeStatusBadge | component-builder |
| 32 | `libs/composites/empty-state/empty-state.component.ts` | MOVE | MeeEmptyState | component-builder |
| 33 | `libs/composites/page-header/page-header.component.ts` | MOVE | MeePageHeader | component-builder |
| 34 | `libs/composites/loading-skeleton/loading-skeleton.component.ts` | MOVE | MeeLoadingSkeleton | component-builder |

> 34 relocations total = 28 (ui-kit) + 6 (composites). The 5 composite `.spec.ts` files move alongside their components. Each composite's own `../ui`→`@mesell/ui-kit` import is rewritten in B2 (composites consume ui-kit primitives).

### Frontend — Layer 0 core relocation (`core/` → `libs/core`, 3 files)

| # | Path (target) | Tag | Description | Owner |
|---|---|---|---|---|
| c1 | `libs/core/services/auth.service.ts` | MOVE | AuthService (in-memory signal token store — the future federation singleton, MASTER_PLAN §6.1) | service-builder |
| c2 | `libs/core/guards/auth.guard.ts` | MOVE | authGuard | service-builder |
| c3 | `libs/core/theme/meesell-preset.ts` | MOVE | MeeSellPreset (PrimeNG Aura override — config layer) | service-builder |

### Frontend — Layer 1 design-tokens relocation (1 file)

| # | Path (target) | Tag | Description | Owner |
|---|---|---|---|---|
| d1 | `libs/design-tokens/_tokens.css` (from `src/app/design-system/_tokens.css`) | MOVE | Layer-1 CSS custom properties | component-builder |

> Note: FRONTEND_ARCHITECTURE.md §Layer 1 documents 5 SCSS files (`_tokens`, `_typography`, `_motion`, `_elevation`, `index.scss`). The as-built develop tip `a391671` has collapsed Layer 1 to a SINGLE `design-system/_tokens.css` (knowledge-sync: "design-system = single `_tokens.css`"). Sub-Plan 0 relocates exactly what exists (1 file). The §Layer 1 doc/reality drift is recorded for the FD1 architecture-amendment pass — it is pre-existing, not introduced by relocation.

### Verbatim move enumeration (what the specialist `git mv`s)

The exact source→target moves (history-preserving `git mv`; specs move with their components). Source paths verified on develop tip `a391671`:

```
# Layer 2 — ui-kit (28 source + 17 spec siblings)
src/app/ui/index.ts                                  -> libs/ui-kit/index.ts
src/app/ui/{button,input,otp-input,textarea,password-input,badge,card,table,
            dialog,file-upload,steps,select,tree-select,skeleton,progress-bar,
            toast,confirm-dialog}/**                  -> libs/ui-kit/<same>/**
   (each dir carries its .component.ts, optional .types.ts, .spec.ts; toast + confirm-dialog
    also carry .service.ts — these are the 2 services in the 28)

# Layer 3 — composites (6 source + 5 spec siblings)
src/app/shared/index.ts                              -> libs/composites/index.ts
src/app/shared/{stat-card,status-badge,empty-state,
                page-header,loading-skeleton}/**      -> libs/composites/<same>/**

# Layer 0 — core (3 source + their spec consumers stay in features)
src/app/core/services/auth.service.ts                -> libs/core/services/auth.service.ts
src/app/core/guards/auth.guard.ts                    -> libs/core/guards/auth.guard.ts
src/app/core/theme/meesell-preset.ts                 -> libs/core/theme/meesell-preset.ts
  + NEW libs/core/index.ts (barrel)

# Layer 1 — design-tokens (1)
src/app/design-system/_tokens.css                    -> libs/design-tokens/_tokens.css
```

### Frontend — Import-path rewrites (the consumer edits)

Verified counts on develop tip `a391671` (the sync's "27" was a file-proxy estimate; these are the exact line counts):

| Surface | Tag | Rewrite | Line count | Owner |
|---|---|---|---|---|
| `../ui` (relative, any depth) → `@mesell/ui-kit` | MODIFY | across 20 distinct files (10 feature/layout source + 10 composite source+spec) | **34 import lines** | component-builder |
| `../shared` (relative) → `@mesell/composites` | MODIFY | across 7 feature source files | **8 import lines** | component-builder |
| `./core/...` / `../../core/...` → `@mesell/core` | MODIFY | `app.config.ts` (preset), `app.routes.ts` (guard), `layouts/shell/shell.component.ts` (+spec), `features/auth/otp-verify` (+spec), `features/profile` (+spec) | **~8 import lines** (5 source + 3 spec) | service-builder |
| `src/styles.css` `@import "./app/design-system/_tokens.css"` → `@import "../libs/design-tokens/_tokens.css"` (or alias) | MODIFY | 1 line | component-builder |

> **Reconciliation of the "27 rewrites" sync note.** The memory's "27 import-path rewrites" was the count of *distinct consumer files*, not import lines. The exact figures verified for this plan: **34 `../ui` lines + 8 `../shared` lines + ~8 `core` lines + 1 styles.css line ≈ 51 import-line edits across ~30 distinct files.** Specialists rewrite by *file*, so the ~30-file figure governs review granularity; the line counts govern the diff size. The execution dispatch (§7) gives specialists the exact `grep` to enumerate before editing.

### Frontend — Workspace + federation config

| # | Path | Tag | Description | Owner |
|---|---|---|---|---|
| w1 | `frontend/tsconfig.json` | MODIFY | Add `compilerOptions.paths`: `@mesell/ui-kit`, `@mesell/composites`, `@mesell/core`, `@mesell/design-tokens` → `libs/*` | service-builder |
| w2 | `frontend/package.json` | MODIFY | Add `@angular-architects/native-federation@^21` dep; (NO new build scripts in Sub-Plan 0 — single shell build retained) | service-builder |
| w3 | `frontend/src/main.ts` | MODIFY | Native Federation bootstrap split: `main.ts` calls `initFederation()` then dynamic-imports `bootstrap.ts` | service-builder |
| w4 | `frontend/src/bootstrap.ts` | NEW | Extracted `bootstrapApplication(App, appConfig)` (the federation init pattern) | service-builder |
| w5 | `frontend/federation.config.js` (or `.manifest.json` scaffold) | NEW | Native Federation config — `shared` deps (`@angular/*`, `rxjs`, `@mesell/core` as `singleton:true`), `remotes: {}` empty | service-builder |
| w6 | `frontend/angular.json` | MODIFY | Native Federation esbuild builder hook (`@angular-architects/native-federation:build` / esbuild plugin) — preserves `@angular/build:application` | service-builder |
| w7 | `frontend/postcss.config.mjs` / tailwind `content` globs | MODIFY (if needed) | Extend Tailwind `content` to include `libs/**/*.{html,ts}` so utilities used by relocated `mee-*` are not purged (MASTER_PLAN §6.3, Risk R4) | component-builder |

### Documentation / status / memory

| # | Path | Tag | Description | Owner |
|---|---|---|---|---|
| s1 | `docs/FRONTEND_ARCHITECTURE.md` §2 | MODIFY | PrimeNG-import allowlist amendment (pending FD1) | frontend-lead |
| s2 | `docs/status/feature_board_frontend.md` | MODIFY | `mf-workspace-foundation` row lifecycle (IN PROGRESS → IN REVIEW → MERGED) | frontend-lead |
| s3 | `docs/status/STATUS_FRONTEND.md` | MODIFY | Updates Log chunks | frontend-lead |
| s4 | `.claude/agent-memory/meesell-frontend-coordinator/` | MODIFY | Sub-Plan 0 learnings | frontend-lead |

### The `federation.config.js` scaffold shape (w5 — illustrative, not final)

Native Federation's host config for Sub-Plan 0 declares shared singletons and an EMPTY remotes map. The shape (final tokens confirmed by the service-builder against `@angular-architects/native-federation@^21` at install time):

```js
// frontend/federation.config.js — Sub-Plan 0 (HOST, zero remotes)
const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

module.exports = withNativeFederation({
  name: 'shell',
  // No remotes wired in Sub-Plan 0 (D7). Sub-Plan 1 adds mfe-pricing here.
  remotes: {},
  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
    // @mesell/core is THE auth singleton (MASTER_PLAN §6.1) — declared but not yet
    // consumed across a remote boundary until Sub-Plan 1.
  },
  skip: [
    // build-only / never-federated packages added as discovered at init time
  ],
});
```

And the bootstrap split (w3/w4):

```ts
// frontend/src/main.ts  (becomes the federation entry)
import { initFederation } from '@angular-architects/native-federation';
initFederation()
  .catch(err => console.error(err))
  .then(() => import('./bootstrap'))
  .catch(err => console.error(err));

// frontend/src/bootstrap.ts  (NEW — holds the existing bootstrapApplication unchanged)
import { bootstrapApplication } from '@angular/platform-browser';
import { App } from './app/app';
import { appConfig } from './app/app.config';
bootstrapApplication(App, appConfig).catch(err => console.error(err));
```

`appConfig` (in `app.config.ts`) is otherwise UNCHANGED except its `MeeSellPreset` import becomes `@mesell/core` (D3). `providePrimeNG`/`MessageService`/`ConfirmationService` stay (the documented root-config carve-out, D6/FD1).

### `tsconfig.json` paths block (w1 — exact target)

```jsonc
// frontend/tsconfig.json  compilerOptions.paths
"paths": {
  "@mesell/ui-kit":        ["libs/ui-kit/index.ts"],
  "@mesell/composites":    ["libs/composites/index.ts"],
  "@mesell/core":          ["libs/core/index.ts"],     // NEW barrel re-exporting auth.service + auth.guard + meesell-preset
  "@mesell/design-tokens": ["libs/design-tokens"]       // CSS folder; @use target if SCSS ever consumes it
}
```

> A NEW `libs/core/index.ts` barrel (NEW, owned by service-builder) re-exports `AuthService`, `authGuard`, `MeeSellPreset` so consumers import `@mesell/core` rather than deep paths. This is the only net-NEW source file in the relocation (besides `bootstrap.ts` + `federation.config.js`); it adds no logic.

### Spec-file discovery (R6 mitigation — config surface)

If the `@angular/build:unit-test` builder's default glob does not reach `frontend/libs/**/*.spec.ts` after the move, the 22 relocated specs (17 ui + 5 composites) would silently stop running. The builder discovers via `tsconfig.spec.json` `include`. Phase B extends that `include` to cover `libs/**/*.spec.ts` (a CONFIG edit, NOT a test edit) and re-asserts `392 passed (392)` — a count drop is a hard reject. This is the single most important guard against a false-green.

---

## Documentation deliverables

These are gate conditions in §9. A Sub-Plan 0 PR cannot merge to develop without:

1. **FRONTEND_ARCHITECTURE.md §2 amendment** — the PrimeNG-import allowlist (FD1). Adds: (a) the new `libs/` layer mapping (Layer 1 → `libs/design-tokens`, Layer 2 → `libs/ui-kit`, Layer 3 composites → `libs/composites`, Layer 0 → `libs/core`); (b) the import-alias convention (`@mesell/*`); (c) the two enumerated PrimeNG carve-outs (root app-config; shell-chrome pending Sub-Plan 6). Must keep the "if PrimeNG is replaced, only the ui-kit changes" core principle intact, restated against the `libs/ui-kit` path.
2. **`SUB_PLAN_00_workspace_foundation.md`** (this document) — referenced from MASTER_PLAN §5 row 0 and the §10 footer "next step".
3. **MASTER_PLAN §1.1 / §2.3 path-fact refresh (minor)** — MASTER_PLAN §1.1 still describes the single-app `src/app/{design-system,ui,shared,layouts,features,core}` shape and §1.2 says "17 mee-* wrappers". A follow-up note (NOT a re-ratification) records that Sub-Plan 0 relocated these to `libs/` and that the ui-kit count is **19 components + 2 services** (knowledge-sync correction), not 17. Recorded in the §11 revision history and the lead memory; the MASTER_PLAN body edit is a trivial doc-sync deferred to the same PR or a follow-up.
4. **`feature_board_frontend.md` + `STATUS_FRONTEND.md`** kept current through the board lifecycle (D1/D2 transitions).
5. **Cross-lead memo to infra** (§6) — `handoff_mf_ci_prep.md` flagging C-CI-1 readiness before Sub-Plan 1.

There is no OpenAPI, no prompt-registry, no V1_FEATURE_SPEC §F-stamp (no backend/ai/feature-spec surface touched).

---

## Branch setup

Per repo-management §1.2 as amended F1 (integration branch = `feature/{name}/integration`).

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/mf-workspace-foundation/integration` | `develop` | Integration branch for this feature; only merge commits + the §6.5 status-only board flips | Frontend Lead (merge approval) |
| `feature/mf-workspace-foundation/frontend` | `feature/mf-workspace-foundation/integration` | ALL frontend specialist relocation + federation-init work | `meesell-angular-component-builder`, `meesell-angular-service-builder` |

No infra/backend/ai/data branches (D5: infra deferred to Sub-Plan 1 prep; others have no work).

### Creation commands

Run by the founder (or Frontend Lead) after THIS sub-plan is approved and FD1 + Gates 3+4 are green. (These are EXECUTION-stage commands — NOT run in the authoring session.)

```bash
# from a clean checkout at develop tip
git fetch origin develop
git checkout develop && git pull --ff-only

# integration branch (F1)
git checkout -b feature/mf-workspace-foundation/integration develop
git push -u origin feature/mf-workspace-foundation/integration

# frontend group branch off the integration branch (F1: NEVER off develop)
git checkout -b feature/mf-workspace-foundation/frontend feature/mf-workspace-foundation/integration
git push -u origin feature/mf-workspace-foundation/frontend

# specialists work in a dedicated worktree (PILOT_REPORT learning 3 — explicit-path staging)
git worktree add /tmp/mesell-wt/mf-foundation feature/mf-workspace-foundation/frontend
```

### PR flow (coding stage)

```
feature/mf-workspace-foundation/frontend
        │  PR — Frontend Lead reviews+merges (squash)   [repo-mgmt §2.1 / D1]
        ▼
feature/mf-workspace-foundation/integration
        │  PR — FOUNDER reviews+merges (merge-commit)    [repo-mgmt §2.2 / D1 / FD2]
        ▼
develop  (deploys to dev namespace)
```

Group → integration: **Frontend Lead** is the reviewer (D1). Integration → develop: **Founder** is the reviewer (D1, FD2) — the lead must NOT approve this gate.

### PR templates

| PR | Template |
|---|---|
| `feature/mf-workspace-foundation/frontend` → `.../integration` | `.github/PULL_REQUEST_TEMPLATE/frontend.md` |
| `.../integration` → `develop` | founder's call; uses the frontend template's evidence sections (build time, bundle delta, 360/1280 screenshots, a11y, boundary grep) |

The frontend template's "Layer architecture compliance" section is the natural home for the boundary-grep evidence; the "Build evidence" section captures the ≤90 s + bundle-delta proof.

### Rebase strategy

Because there is only one frontend group branch and no sibling group branches, there is no cross-group rebase contention in Sub-Plan 0. If a *parallel* feature (e.g. auth-otp under federation-first) lands on `develop` while this branch is in flight, the integration branch rebases onto the moved `develop` tip (repo-management §1.4.2: rebase, don't merge). The relocation diff is mechanical, so a rebase conflict would only arise if the parallel feature also touched `frontend/src/app/{ui,shared,core,design-system}` — in which case the §8.3 "extract shared code first" pattern applies and the lead coordinates ordering. Given federation-first ordering, Sub-Plan 0 SHOULD land before any feature branch reopens, eliminating this risk (see Risk R3).

### Branch protection (F3)

`feature/mf-workspace-foundation/integration` is created with the F3 integration-branch profile: PR-only, `required_approving_review_count = 0`, strict status checks (`contexts = []` until CI active), `allow_force_pushes = false`, `allow_deletions = false`, `enforce_admins = false`. The review-count-0 setting permits the §6.5 direct status-only board flip on MERGED. **Re-probe protection empirically before assuming** (PILOT_REPORT learning 4: wrong-blob-sha PUT → 409 vs 403/422).

---

## Memory protocol

### Memories the coding-session leads MUST read at start

- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` (Frontend Lead — own memory; the MF master-plan memo + the knowledge-sync as-built findings: 19 ui components, 34 relocations, ~30-file/51-line rewrites, §4 core not built, no HttpClient, the 2 boundary leaks)
- `.claude/agent-memory/meesell-frontend-coordinator/module_federation_master_plan_2026_06_10.md` (the master-plan memo)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (Gate 4 conditions C-CI-1/C-CSP-1; protection-probe method)

Specialists read the Frontend Lead memory + this Sub-Plan 0 + the MASTER_PLAN §2/§4/§6 before touching files.

### Cross-feature memos

- **Outgoing:** `.claude/agent-memory/meesell-frontend-coordinator/handoff_mf_ci_prep.md` — to infra, flagging C-CI-1 (CI matrix rewrite) must be ready before Sub-Plan 1, and that the reorganised `frontend/src/app/**` + new `frontend/libs/**` paths must be confirmed against the existing `build-frontend` glob. 48h SLA. A row is added to `feature_board_frontend.md` "Inter-lead requests open" (outgoing side); infra reads the memo and adds its own incoming-side row to its own board (never edit infra's board).
- **Forward-reference memo:** `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_00_workspace.md` — records the final `@mesell/*` alias map + the federation-init shape so Sub-Plan 1 (pilot) starts from a stable contract.

### Naming convention for new memos created during this feature

`sub_plan_00_workspace.md` (sorts with the MF series) — ONE convention, not both.

### Session-close memory entries

Each agent appends at coding-session close: session header (`## Session mesell-mf-workspace-foundation-frontend-session-{N}`), decisions ratified (D1–D7 outcomes), files-touched count (34 moves + ~30 rewrite files + 7 config), the measured build time + test pass count, any boundary-grep result, blockers carried, next-step (Sub-Plan 1 pilot readiness).

---

## Dispatch templates

One `### h3` per specialist. Prompts are paste-able for the EXECUTION session (which runs after FD1 + Gates 3+4 clear). Headings inside the fences are prompt content, not document structure.

### meesell-angular-service-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mf-workspace-foundation-frontend-session-1

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_00_workspace_foundation.md (this plan — D1, D3, D7, §3 Code surfaces w1-w7, c1-c3)
- docs/plans/module_federation/MASTER_PLAN.md §2.3 (shared libs), §3 (Native Federation choice), §6.1 (AuthService singleton)
- docs/plans/module_federation/TESTBED_TRIAGE.md (N=0 baseline — ANY new test failure blocks your PR)
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (as-built: §4 core not built, no HttpClient)

## Your mission
PHASE A of Sub-Plan 0. (1) Create frontend/libs/{ui-kit,composites,core,design-tokens} as empty folders and add the four `@mesell/*` path aliases to frontend/tsconfig.json `compilerOptions.paths` pointing at libs/* (D1 — alias workspace, NOT ng-packagr libraries). (2) `git mv` the 3 core files (services/auth.service.ts, guards/auth.guard.ts, theme/meesell-preset.ts) into frontend/libs/core/ preserving subfolders; rewrite EVERY consumer import of those three to `@mesell/core` (enumerate first with: `grep -rn "core/services/auth.service\|core/guards/auth.guard\|core/theme/meesell-preset" frontend/src --include='*.ts'`). (3) Install `@angular-architects/native-federation@^21`; run its init to produce the bootstrap split (main.ts -> initFederation() -> dynamic import of NEW bootstrap.ts holding bootstrapApplication) + the federation.config.js scaffold with `shared` deps declared (@angular/*, rxjs singleton; @mesell/core singleton:true) and `remotes: {}` EMPTY; wire the esbuild-compatible builder in angular.json WITHOUT abandoning @angular/build:application. DO NOT register any remote, DO NOT add any loadRemoteModule call.

## Acceptance criteria
- [ ] frontend/libs/core holds the 3 files; old src/app/core is empty/removed
- [ ] tsconfig paths: @mesell/{ui-kit,composites,core,design-tokens} resolve
- [ ] native-federation@^21 in package.json; bootstrap split present; manifest scaffold has remotes:{}
- [ ] `pnpm build` GREEN and ≤ 90 s (record the exact seconds)
- [ ] `pnpm test` 392/392 GREEN (N=0 baseline preserved)
- [ ] NO loadRemoteModule, NO remote registered, NO feature behaviour change

## Hard constraints
- ZERO logic edits to auth.service/guard/preset — only their OWN imports + their callers' import specifier change
- Do NOT convert libs to ng-packagr build targets (D1)
- Do NOT touch ui/, shared/, design-system relocations — that is Phase B (component-builder)
- Do NOT touch backend/, k8s/, infra/

## Files you MAY touch
- frontend/libs/core/** (new), frontend/tsconfig.json, frontend/package.json, frontend/angular.json, frontend/src/main.ts, frontend/src/bootstrap.ts (new), frontend/federation.config.js (new)
- frontend/src/app/app.config.ts, app.routes.ts, layouts/shell/shell.component.ts(+spec), features/auth/otp-verify/*, features/profile/* (ONLY the @mesell/core import lines)

## Files you must NOT touch
- frontend/src/app/ui/**, shared/**, design-system/** (Phase B)
- Any feature template/logic; any backend/k8s/infra path

## Final report format
Files moved (count), import lines rewritten (count), native-federation version installed, build seconds, test pass count, boundary note. Then STOP for lead review before component-builder Phase B.
```

### meesell-angular-component-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mf-workspace-foundation-frontend-session-2

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_00_workspace_foundation.md (this plan — D2, D4, D6, §3 ui-kit/composites/design-tokens tables, R2/R4)
- docs/plans/module_federation/MASTER_PLAN.md §6.3 (Tailwind single-build), §2.3 (libs)
- docs/plans/module_federation/TESTBED_TRIAGE.md (N=0 — ANY new failure blocks your PR)
- docs/FRONTEND_ARCHITECTURE.md (4-layer boundary; PrimeNG only in Layer 2)

## Your mission
PHASE B of Sub-Plan 0, AFTER service-builder's Phase A is merged/sequenced and the build is green. (1) `git mv` the 28 ui source files (17 component dirs + their .types.ts + index.ts + 2 .service.ts) AND their 17 .spec.ts siblings from src/app/ui -> frontend/libs/ui-kit; (2) `git mv` the 6 composite source files + 5 specs from src/app/shared -> frontend/libs/composites; (3) `git mv` src/app/design-system/_tokens.css -> frontend/libs/design-tokens/_tokens.css. Then rewrite import specifiers: enumerate with `grep -rn "from ['\"]\(\.\./\)\{1,\}ui['\"]" frontend/src --include='*.ts' | grep -v '/ui/'` (expect 34 lines) -> `@mesell/ui-kit`; `grep -rn "from ['\"]\(\.\./\)\{1,\}shared['\"]" frontend/src --include='*.ts' | grep -v '/shared/'` (expect 8 lines) -> `@mesell/composites`; the composites' OWN `../ui` imports -> `@mesell/ui-kit`; update src/styles.css `@import` of _tokens.css to the libs/design-tokens path. Extend Tailwind `content` globs to include `libs/**/*.{html,ts}` (R4 purge guard).

## Acceptance criteria
- [ ] libs/ui-kit holds 28 source + 17 specs; libs/composites holds 6 source + 5 specs; libs/design-tokens holds _tokens.css; old src/app/{ui,shared,design-system} removed
- [ ] ALL `../ui` and `../shared` relative imports rewritten to `@mesell/*` (grep returns 0 stale relative ui/shared imports outside libs/)
- [ ] styles.css imports tokens from the new path; Tailwind content includes libs/**
- [ ] `pnpm build` GREEN ≤ 90 s; `pnpm test` 392/392 GREEN
- [ ] Boundary grep: `grep -rn "from 'primeng" frontend/src frontend/libs | grep -v 'libs/ui-kit/'` returns ONLY the two enumerated carve-outs (app.config providers; shell Drawer/Menu) — NO third leak

## Hard constraints
- ZERO logic/template/class-name edits — only relocation + import-specifier rewrites (D2)
- Do NOT author MeeDrawer/MeeMenu wrappers — that is Sub-Plan 6 (D6); shell's primeng import stays as a documented carve-out
- Do NOT touch core/ relocation or federation config (Phase A, service-builder)
- Do NOT touch backend/, k8s/, infra/

## Files you MAY touch
- frontend/libs/ui-kit/**, frontend/libs/composites/**, frontend/libs/design-tokens/** (new homes)
- The consumer import lines in frontend/src/app/features/**, layouts/**, and the composites' own imports; frontend/src/styles.css; frontend/postcss.config.mjs (Tailwind content only)

## Files you must NOT touch
- frontend/libs/core/**, frontend/federation.config.js, frontend/angular.json builder, frontend/src/main.ts/bootstrap.ts (Phase A)
- Any feature behaviour; any backend/k8s/infra path

## Final report format
Files moved (ui/composites/tokens counts), import lines rewritten (ui/shared counts), build seconds, test pass count, boundary-grep output (must show only the 2 carve-outs). Then STOP for lead review + PR.
```

---

## Review + iteration protocol

### meesell-angular-service-builder (Phase A)

- **Pre-approval checklist (lead inspects):** (a) `git log --follow` on `libs/core/services/auth.service.ts` shows history preserved (git mv, not delete+create); (b) `auth.service.ts` content diff is empty except its own import lines — NO signal/method change (D2); (c) `tsconfig.json` paths resolve (the build proves it); (d) `federation.config.js` has `remotes: {}` EMPTY and `@mesell/core` declared `singleton: true`; (e) NO `loadRemoteModule` anywhere (`grep -rn loadRemoteModule frontend/src` = 0); (f) build seconds recorded and ≤90 s; (g) 392/392 tests green.
- **PR-template gate:** `.github/PULL_REQUEST_TEMPLATE/frontend.md` filled completely, no `<>` placeholders, build evidence + bundle delta present.
- **Re-dispatch triggers:** "converted a lib to an ng-packagr target" → re-dispatch quoting D1; "registered a remote / added loadRemoteModule" → re-dispatch quoting D7; "edited AuthService logic" → re-dispatch quoting D2; "abandoned @angular/build:application for webpack" → re-dispatch quoting MASTER_PLAN §3.
- **Re-dispatch prompt shape:** original Phase A prompt + preamble "Previous run failed on X; fix Y by reading Z (specific D-number / MASTER_PLAN §)".
- **Iteration cap: 3.** Third re-dispatch auto-escalates to founder.

### meesell-angular-component-builder (Phase B)

- **Pre-approval checklist (lead inspects):** (a) every moved file shows preserved history; (b) `grep -rn "from ['\"]\(\.\./\)\{1,\}\(ui\|shared\)['\"]" frontend/src --include='*.ts' | grep -v '/libs/'` returns 0 stale relative imports; (c) boundary grep returns ONLY the 2 enumerated carve-outs — a third PrimeNG-outside-`libs/ui-kit` import is a hard reject; (d) `styles.css` token import resolves; (e) Tailwind `content` includes `libs/**` (R4); (f) build ≤90 s; (g) 392/392 tests green; (h) NO `.types.ts` orphaned (barrel `index.ts` re-exports still resolve).
- **PR-template gate:** `.github/PULL_REQUEST_TEMPLATE/frontend.md` — Layer architecture compliance section confirms Layers 1/2/3 relocated, not logically changed; 360 px + 1280 px screenshots attached showing NO visual change.
- **Re-dispatch triggers:** "authored MeeDrawer/MeeMenu" → re-dispatch quoting D6 (deferred to Sub-Plan 6); "edited a component template/logic" → re-dispatch quoting D2; "left a stale `../ui` import" → re-dispatch with the failing grep line; "third PrimeNG leak introduced" → re-dispatch quoting the §9 boundary gate.
- **Re-dispatch prompt shape:** original Phase B prompt + "Previous run failed on X (paste grep/test output); fix only that, re-run build+test+boundary-grep".
- **Iteration cap: 3.** Third re-dispatch auto-escalates to founder.

---

## Acceptance gate

When every box is `[x]`, `feature/mf-workspace-foundation/integration` is ready for the founder's develop PR.

- [ ] Phase A PR (`feature/mf-workspace-foundation/frontend` → integration, service-builder slice) merged by Frontend Lead
- [ ] Phase B PR (component-builder slice) merged by Frontend Lead — OR both phases on one branch merged as one squash if sequenced on the same branch
- [ ] `pnpm build` GREEN and **≤ 90 s** (CLAUDE.md Decision 12 / Stop Condition) — exact seconds recorded in the PR + STATUS
- [ ] `pnpm test` = **392/392 GREEN, 0 failing, 0 skipped** (N=0 baseline, `TESTBED_TRIAGE.md`) — any new failure blocks the merge
- [ ] **Boundary grep clean:** PrimeNG imports appear ONLY under `libs/ui-kit/`, EXCEPT the two enumerated carve-outs (root app-config providers; shell-chrome Drawer/Menu tracked for Sub-Plan 6). No third leak.
- [ ] **All 10 canonical V1 routes resolve** (route-resolution smoke: `/`, `/login`, `/signup`, `/otp-verify`, `/dashboard`, `/onboarding`, `/profile`, `/catalogs/new`, `/catalogs/:id/edit`+images+preview+pricing+export) — plus the extra `/catalogs` list + `/onboarding` registered today; wildcard `**` → `/login` intact
- [ ] `grep -rn loadRemoteModule frontend/src` = 0 (D7 — no remote wired in Sub-Plan 0)
- [ ] `@mesell/{ui-kit,composites,core,design-tokens}` aliases resolve; no stale relative `../ui` / `../shared` / `../../core` imports remain outside `libs/`
- [ ] Native Federation installed + initialised; `federation.config.js` has `remotes: {}` empty; `@angular/build:application` esbuild builder preserved
- [ ] FRONTEND_ARCHITECTURE.md §2 allowlist amendment landed (FD1 approved)
- [ ] §5.1 MASTER_PLAN post-cutover audit HOOKS referenced — Sub-Plan 0 records the as-merged libs topology so Sub-Plan 7's compliance audit can verify the convention held from the start
- [ ] `feature_board_frontend.md` row = MERGED (lead, §6.5 direct status-only commit); STATUS_FRONTEND.md Updates Log appended; memo to infra filed
- [ ] **Founder approval** on `feature/mf-workspace-foundation/integration` → `develop` (D1 / FD2 — founder's gate, NOT the lead's)

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Stale relative import survives the rewrite** — a `../ui` or `../../core` import is missed, build fails or (worse) resolves to a now-empty path. | Medium | High | Enumerate-before-edit grep is mandatory in both dispatches; §8/§9 gate runs `grep -rn "from ['\"]\(\.\./\)\{1,\}\(ui\|shared\|core\)['\"]"` and asserts 0 outside `libs/`. Build failure catches the rest. N=0 test baseline catches runtime resolution drift. |
| R2 | **Shell PrimeNG Drawer/Menu leak ambiguity** — the §9 boundary gate can't tell the pre-existing shell leak from a new regression. | High | Medium | D6 + FD1: the leak is ENUMERATED as a documented carve-out in FRONTEND_ARCHITECTURE §2, so the gate allows exactly 2 carve-outs and rejects a 3rd. Remediation (MeeDrawer/MeeMenu wrappers) tracked to Sub-Plan 6. NOT fixed here (would break D2 smallest-diff). |
| R3 | **A parallel feature branch touches `src/app/{ui,shared,core}` while Sub-Plan 0 is in flight** → rebase hell on a 34-file move. | Low | High | Federation-first ordering (MASTER_PLAN §1.0 ruling) means Sub-Plan 0 lands BEFORE any feature reopens. Lead confirms no other frontend group branch is open before cutting the branch. If one is open, apply repo-management §8.3 "extract shared first" — land the relocation as the precursor refactor, then siblings rebase onto the new `@mesell/*` aliases. |
| R4 | **Tailwind purge breaks relocated `mee-*` styles** — PostCSS scan no longer sees `libs/**`, utilities used by moved primitives get purged, UI breaks only at runtime. | Medium | Medium | Phase B extends Tailwind `content` globs to `libs/**/*.{html,ts}` (MASTER_PLAN §6.3). 360/1280 screenshots in the PR must show NO visual change vs develop. CI build asserts a known utility class survives (deferred CI gate; manual founder pass for V1). |
| R5 | **Native Federation init pushes the shell build past 90 s** — the bootstrap split + esbuild plugin add overhead. | Low | High | Phase A re-measures build seconds at the A4 checkpoint BEFORE Phase B. Stop Condition: if shell build > 90 s, HALT, do not proceed to Phase B, escalate to founder (CLAUDE.md Decision 12). Current baseline 2.7 s leaves large headroom; the init adds plugin wiring, not remote loading, so the risk is low. |
| R6 | **Regression blindness from spec-file relocation** — moving the 22 spec files (17 ui + 5 composites) breaks the `@angular/build:unit-test` discovery globs, tests silently don't run, "392 green" is a false pass. | Medium | High | Phase B asserts the EXACT count `392 passed (392)` — not just "0 failed". A drop in the total (e.g. 392 → 350) means specs stopped being discovered and is a hard reject. The builder discovers specs by glob under `src/`; if `libs/` falls outside the default glob, the unit-test `tsconfig.spec.json` / builder `include` is extended to cover `libs/**/*.spec.ts` (a config edit, NOT a test edit) and the count re-asserted at 392. |
| R7 | **transloco / @angular/cdk gaps surface during relocation** — knowledge-sync found neither is in package.json; a moved file might reference them. | Low | Low | Neither is referenced by the 34 moved files today (the moved code is the as-built scaffold which dropped transloco in Wave 2B and never added CDK). Relocation does not introduce either dependency. If a moved file unexpectedly imports transloco/cdk, the build fails immediately and the dependency gap is escalated (it would be a pre-existing latent bug, not a relocation regression). CDK is added later by the live-preview feature, NOT by Sub-Plan 0. |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 (DRAFT) | 2026-06-10 | `mesell-module-federation-frontend-session-1` (master-session dispatch) | Initial authoring of Sub-Plan 0 — Workspace Foundation. 34 relocations (28 ui-kit + 6 composites) + 3 core + 1 design-tokens; verified import-rewrite counts (34 ui + 8 shared + ~8 core + 1 styles lines across ~30 files) reconciled against the sync's "27 files"; Native Federation install + init (remotes empty, D7); D1–D7 lead decisions; FD1 (FRONTEND_ARCHITECTURE §2 allowlist) + FD2 (execution authorisation) as the only founder-level calls; 7 risks incl. the 2 boundary leaks (R2), transloco/cdk gaps (R7), regression-blindness (R6). Awaits founder approval to EXECUTE; execution further gated on Gates 3 (SATISFIED) + 4 (CONFIRMED-WITH-CONDITIONS). |

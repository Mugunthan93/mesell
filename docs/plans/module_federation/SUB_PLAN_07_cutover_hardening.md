# Sub-Plan 07 — Federation Cutover & Hardening (THE CLOSER)

**STATUS: DRAFT 2026-06-10 — authored under master-session night-run dispatch (S3, session `mesell-module-federation-frontend-session-3`). Awaits founder approval to EXECUTE.**

| Field | Value |
|---|---|
| Document type | Module-federation sub-plan — the CUTOVER + HARDENING closer (NOT an extraction; planning only — zero application-code changes in THIS authoring session) |
| Parent plan | `docs/plans/module_federation/MASTER_PLAN.md` (APPROVED 2026-06-10) §4.2 "Federation Cutover & Hardening" + §5 row 7 + **§5.1 (the founder-mandated post-cutover repo-management compliance audit — a COMPLETION CRITERION of this sub-plan)** |
| Predecessors | SP00–SP06 ALL EXECUTED + MERGED. All 6 remotes (`mfe-pricing`, `mfe-export`, `mfe-onboarding`, `mfe-dashboard`, `mfe-catalog`, `mfe-auth`) extracted + in the manifest. The full auth loop closed (SP03 C5 READ/LOGOUT + SP06 C4 WRITE). |
| Canonical pattern | `docs/plans/features/_CANONICAL_PATTERN.md` v2.1 — 11 sections, locked order (adapted: a hardening/cutover sub-plan, not an extraction) |
| Author | meesell-frontend-coordinator (Frontend Lead) |
| Feature slug | `mfe-cutover` |
| Remote ID | n/a — touches the shell + ALL 6 remotes' deploy surface + infra |
| Owned scope | (1) Remove shell-internal fallbacks/dead `loadComponent` imports; (2) **AUTHOR the CSP** (resolve D14 / discharge C-CSP-1 — must NOT disturb CORS or the refresh-token `Set-Cookie` per Gate-4); (3) **resolve D9** (the `apps/shell/` relocation decision); (4) version-pin the manifest per env (staging/prod); (5) full federated-app smoke; (6) **discharge ALL 6 Gate-4 C-conditions**; (7) **EXECUTE the §5.1 repo-management compliance audit** (founder-mandated completion criterion). |
| Out of scope | Backend API logic (Wave 6 — federation does not change it); AI; mobile/Ionic; any NEW remote (all 6 done); the auth contract (closed at SP06) |
| Execution gates | SP01–SP06 merged to develop + founder approval of THIS sub-plan + infra readiness on C-RES/C-ROUTE/C-CI/C-STAGING (the off-cluster Option-C surface stood up) + the founder's resolution of the D9 relocation FOUNDER-FLAG |

`mfe-cutover` is the **final sub-plan** — the closer. By SP07, all 6 remotes are extracted, the auth loop is closed, and the dev-validated federation runs on localhost-served remotes with NO CSP (per the inherited D14 deferral). SP07 turns the dev-proven federation into a STAGING/PROD-ready system: it removes the now-dead shell-internal code, authors the production CSP that lets the shell load remotes from `remotes.mesell.xyz`, decides whether the shell physically relocates to `apps/shell/`, version-pins the per-env manifests for safe rollback, runs the full federated smoke, discharges every Gate-4 condition, and — per the founder's §5.1 mandate — audits whether the Model C repo-management convention survived the 6-remote migration. This sub-plan is a JOINT infra↔frontend effort (MASTER_PLAN §5 row 7: `meesell-frontend-coordinator + meesell-infra-builder`).

This is the FIRST sub-plan to author production CSP, the FIRST to potentially relocate the shell, and the ONLY one that closes out a founder-mandated compliance audit. Its complexity is in the CROSS-LEAD coordination (the CSP must not break the refresh-cookie that BACKEND owns and INFRA fronts) and the AUDIT (a meta-task spanning all 6 extractions), not in code volume.

---

## Decisions

D-numbers append-only and monotonic, continuing from SUB_PLAN_06 (which ended at D40). FOUNDER-FLAG marks founder-level calls.

### Adaptations from the canonical V1-feature pattern

This is NOT an extraction — it is a cutover/hardening + audit closer. Adaptations: lineup is one lead (frontend, owning the shell cleanup + the CSP origin/token allowlist + the audit) + `meesell-angular-component-builder` (shell dead-code removal + the optional `apps/shell/` relocation) + a heavy CROSS-LEAD dependency on `meesell-infra-builder` (the CSP header mechanism + per-env manifest templating + the 6 C-conditions' infra side). NO new remote, NO new extraction. §3 is dominated by `MODIFY`/`REMOVE` (shell cleanup) + `NEW` (CSP config, version-pinned manifests). §9 is the heaviest acceptance gate: a full federated smoke + the 6-condition discharge + the audit.

### D41 — Remove shell-internal fallbacks + dead `loadComponent` imports; the shell becomes a PURE host (no feature code)

**Decision.** After SP01–SP06, every feature route in `app.routes.ts` is a `loadRemoteWithFallback`/`loadRemoteRoutesWithFallback` call. SP07 removes any remaining shell-internal feature code: (a) dead `loadComponent: () => import('./features/...')` lines (all features are now remotes — verify NONE remain); (b) the (now-empty) `frontend/src/app/features/` directory; (c) any shell-internal fallback that duplicated a remote's behaviour (NOT the `RemoteFailureComponent` — that STAYS, it is the §6.4 error boundary). The shell retains ONLY: `app.config.ts`, `app.routes.ts`, `main.ts`/`bootstrap.ts`, `core/` (load-remote helpers, remote-failure, the shell-owned guards/interceptors that live in `@mesell/core`), `layouts/shell/` (the chrome), and the federation manifest.

**Rationale.** The strangler-fig endgame: once every feature is a remote, the shell's `features/` directory is dead weight. Removing it (a) shrinks the shell bundle, (b) prevents accidental drift (a developer editing a shell copy instead of the remote), and (c) realises MASTER_PLAN §2.1's "shell = pure host". The `RemoteFailureComponent` + `load-remote.ts` helpers stay (they are host concerns, not features).

**Consequence.** `frontend/src/app/features/` is removed entirely (it should already be empty after SP01–06's `git mv`s — SP07 confirms + removes the dir). The shell's `app.routes.ts` is ALL remote calls + the public/private structure + the wildcard. Verify the shell build SHRINKS (no feature chunks). Any test that imported a feature directly from the shell must be gone (it moved to the remote with its spec).

### D42 — AUTHOR the production CSP (resolve D14 / discharge C-CSP-1); the CSP MUST NOT strip CORS headers or the refresh-token `Set-Cookie` (Gate-4 constraint) — **FOUNDER-FLAG (CSP go-live)**

**Decision.** SP07 authors the production CSP — the joint infra↔frontend C-CSP-1 deliverable. The SPLIT (per GATE4_CONFIRMATION.md C-CSP-1): **frontend-coordinator owns the precise origin/token allowlist the federation runtime demands; infra owns the header MECHANISM + per-env templating.** The frontend allowlist:
```
script-src  'self' https://remotes.mesell.xyz [+ 'wasm-unsafe-eval' or a nonce if Angular/es-module-shims needs it — CONFIRM empirically on dev]
connect-src 'self' https://api.mesell.xyz https://remotes.mesell.xyz   (federation manifest + remoteEntry fetches + the API)
style-src   'self' 'unsafe-inline' https://remotes.mesell.xyz          (Tailwind/PrimeNG runtime styles — confirm token set)
font-src    'self' https://remotes.mesell.xyz
img-src     'self' data: https://remotes.mesell.xyz
```
The MECHANISM (infra's call, two viable layers per Gate-4 Answer 4): (1) `add_header Content-Security-Policy` in the shell image's `nginx.conf`, OR (2) a CSP-only Traefik `Middleware` CRD. **CRITICAL CONSTRAINT (Gate-4 Answer 4 / BACKEND_ARCHITECTURE §4.G):** the CSP header MUST be ADDED ONLY — it must NOT strip/override the app's CORS response headers or the refresh-token `Set-Cookie` (HttpOnly+Secure+SameSite=Strict, per FE-D5/FE-D6 + CLAUDE.md D14). A CSP-only addition is safe; a broad headers middleware is NOT. The CSP must be authored + smoke-tested on `dev` BEFORE any remote ships to staging/prod (C-CSP-1).

**Rationale.** Inherited D14 deferred CSP to SP07. The public landing (SP04 R-SP4-5) + the public auth pages (SP06 R-SP6-6) make the CSP a HARD precondition for staging/prod: without it, every unauthenticated visitor's first paint (landing or login) fails to load its remote — a blank page. C-CSP-1 is one of the 6 Gate-4 conditions SP07 must discharge.

**FOUNDER-FLAG.** CSP go-live is a production-affecting change with a cross-lead blast radius (a wrong CSP can break the refresh-token flow → silent logout-loops, or break remote loading → blank pages). The founder confirms: **author the CSP with the frontend-owned allowlist above + the infra-owned ADD-ONLY mechanism, smoke-test on dev first, and gate the staging/prod remote cutover on a GREEN CSP smoke (no CORS/refresh-cookie regression).** This is a joint infra↔frontend deliverable — a memo to infra carries the frontend allowlist; infra returns the chosen mechanism + the per-env template. The refresh-cookie non-regression is verified by the BACKEND/auth smoke (the 401-test baseline → refresh → retry still works WITH the CSP active).

> **RULED 2026-06-11 (founder, morning session): APPROVED as recommended.** CSP approach approved — the ADD-ONLY policy is authored at SP07, dev smoke first, with the staging/prod cutover gated on a GREEN CSP smoke (no CORS / refresh-cookie regression). Executes at SP07 cutover as the joint infra↔frontend deliverable described above. This discharges C-CSP-1 and resolves the inherited D14.

### D43 — Resolve D9: the shell relocation to `apps/shell/` decision — **FOUNDER-FLAG (resolve the deferred D9)**

**Decision.** SP01 D9 (FOUNDER-FLAG) deferred the shell's physical move from `frontend/src/` into `apps/shell/src/` to SP07. SP07 RESOLVES it. Two options:
1. **RELOCATE** the shell into `apps/shell/` — achieves the idealised MASTER_PLAN §2.1 topology (`apps/shell/` + `apps/mfe-*/` + `libs/`), making the workspace uniform (every project under `apps/`). Cost: a large mechanical churn (`angular.json` `sourceRoot`, `tsconfig` references, the Tailwind `content` glob simplifies from `['src/**','apps/**','libs/**']` to `['apps/**','libs/**']`, every shell-relative path). Zero behaviour change. Best done NOW (cutover) when the shell is already a pure host (D41) with minimal feature code to move.
2. **KEEP** the shell at `frontend/src/` — accept the asymmetry (shell at `src/`, remotes at `apps/`). Zero churn. The Tailwind glob keeps the `src/**` term. The remotes never reference the shell's physical path (they resolve it via the manifest URL + `@mesell/*` aliases), so the asymmetry is purely cosmetic.

**Decision: RECOMMEND RELOCATE (option 1) NOW.** Rationale: SP07 is the natural cutover point; D41 has already stripped the shell to a pure host (the smallest it will ever be), so the relocation churn is minimised; a uniform `apps/` topology simplifies the C-CI-1 cloudbuild matrix (one glob rule: `apps/<name>/**` triggers `<name>`'s build) and the Tailwind glob. Doing it later (post-V1) means churning a shell that has re-accumulated config.

**Rationale.** MASTER_PLAN §2.1 prose specifies `apps/shell/`; the as-built reality (SP0) is `frontend/src/`. SP01 D9 explicitly named SP07 as the resolution point ("a clean later step (a candidate for Sub-plan 7 hardening)"). Resolving it at the cutover, after D41's strip, is the lowest-churn moment.

**FOUNDER-FLAG.** The relocation is a large mechanical diff (every shell path) with zero behaviour benefit beyond topology uniformity + a simpler CI matrix. The founder confirms: **RELOCATE the shell to `apps/shell/` now (recommended — lowest-churn at the post-strip cutover, uniform topology, simpler CI) OR KEEP it at `src/` (zero churn, accept the cosmetic asymmetry).** If KEEP, the Tailwind glob retains `src/**` and the CI matrix keeps a special-case shell rule. Either is federation-correct.

> **RULED 2026-06-11 (founder, morning session): APPROVED as recommended.** Shell relocation to `apps/shell/` approved — execute at SP07 cutover (option 1, RELOCATE). This resolves the deferred D9. The Tailwind `content` glob simplifies to `['apps/**','libs/**']` and the C-CI-1 matrix gets the uniform `apps/<name>/**` rule. The conditional FRONTEND_ARCHITECTURE §2 doc-sync (libs/ + apps/shell topology) is proposed to the founder for §7.3 ratification at execution time — NOT improvised.

### D44 — Version-pin the per-environment manifests for staging/prod (rollback safety; discharge C-STAGING-1 + the R5 contract-drift mitigation)

**Decision.** The dev manifest points at localhost-served remotes (the SP01–06 dev-validation pattern). SP07 authors the STAGING + PROD manifests pointing at version-pinned GCS/CDN URLs:
```
prod/staging:  "mfe-pricing": "https://remotes.mesell.xyz/{env}/mfe-pricing/{version}/remoteEntry.json"
```
where `{version}` is an EXACT build hash/semver per remote (NOT `latest`). The per-env manifest is templated by infra (envsubst, the C-CI-1 path). Version-pinning enables: (a) atomic rollback (re-point the manifest at the prior `{version}`); (b) the R5 cross-remote contract-drift mitigation (the shell's manifest pins the EXACT remote build it was tested against — a remote can't silently ship a breaking model change because the shell pins its hash until the manifest is updated in lockstep).

**Rationale.** MASTER_PLAN §4.3 ("manifest pins versions per environment"; "versioned remote-entries enable rollback") + §6.6 (version compatibility) + R5 (contract drift). C-STAGING-1 requires staging remotes off-cluster too (separate `remotes-staging.mesell.xyz` bucket). Version-pinning is the safety mechanism that makes a 6-remote prod deploy reversible.

**Consequence.** Three manifests (dev = localhost; staging = `remotes-staging.mesell.xyz/.../{version}`; prod = `remotes.mesell.xyz/.../{version}`). Infra owns the templating + the per-env buckets (C-RES-2, C-STAGING-1, C-ROUTE-1). Frontend owns the manifest SHAPE + the version-pin discipline (no `latest`). The C-CI-1 `shared/**`-rebuilds-all rule (SP05 D33/R5) means a `@mesell/core` model change bumps EVERY remote's version in lockstep — recorded for infra.

### D45 — Discharge ALL 6 Gate-4 C-conditions; each gets an explicit PASS with evidence in the SP07 acceptance gate

**Decision.** SP07's completion requires every `GATE4_CONFIRMATION.md` C-condition discharged with evidence:
- **C-RES-1** (Option A in-cluster INFEASIBLE) — DISCHARGED by NOT taking Option A: confirm no remote runs as an in-cluster pod (all 6 are GCS/CDN static). Evidence: `kubectl get deploy -n dev` shows only `mfe-shell` (+ api/worker/etc.), NO `mfe-*` remote pods.
- **C-RES-2** (Option C: shell in-cluster, 6 remotes GCS/CDN, 0 in-cluster remote CPU) — DISCHARGED: the shell Deployment swapped in for the retiring `frontend` Deployment (~0 net CPU); remotes in GCS. Evidence: `kubectl describe node` CPU requests unchanged ±shell delta.
- **C-ROUTE-1** (`remotes.mesell.xyz` Namecheap A + GCP-managed cert, NOT cert-manager) — DISCHARGED by infra: the host resolves + serves `remoteEntry.json` over HTTPS with a GCP-managed cert. Evidence: `curl -I https://remotes.mesell.xyz/.../remoteEntry.json` returns 200 + a valid cert.
- **C-CI-1** (replace single-frontend cloudbuild with `cloudbuild.shell.yaml` + `cloudbuild.remote.yaml` + a `dorny/paths-filter` matrix) — DISCHARGED by infra: a change under `apps/mfe-pricing/` rebuilds ONLY `mfe-pricing`; a `libs/**` change rebuilds ALL. Evidence: a test push showing the matrix fan-out.
- **C-CSP-1** (CSP authored from scratch; ADD-ONLY; no CORS/refresh-cookie regression; smoke-tested on dev first) — DISCHARGED by D42: the CSP is live on dev, the federation loads remotes, the refresh-token flow still works. Evidence: the dev CSP smoke + the 401→refresh→retry non-regression test.
- **C-STAGING-1** (staging remotes off-cluster too) — DISCHARGED by D44: the staging manifest points at `remotes-staging.mesell.xyz` (off-cluster); no in-cluster staging remote pods. Evidence: the staging manifest + `kubectl get deploy -n staging`.

**Rationale.** §5.1 + the master plan name SP07 as the home of the Gate-4 conditions ("these become Sub-plan 7 / MF infra-plan requirements" — Gate-4 verdict). Discharging them with evidence is SP07's infra-side completion criterion.

**Consequence.** SP07's acceptance gate (§9) carries all 6 as explicit checkboxes with the evidence each needs. The infra-owned conditions (C-RES, C-ROUTE, C-CI, C-STAGING) are discharged by `meesell-infra-builder` via the cross-lead memo; the frontend-owned condition (C-CSP-1 allowlist) is discharged by the frontend lead jointly. NONE may be left open at SP07 close.

### D46 — EXECUTE the §5.1 repo-management compliance audit (founder-mandated COMPLETION CRITERION) — owner: frontend-coordinator with master-session review

**Decision.** MASTER_PLAN §5.1 mandates a post-cutover audit as an SP07 completion criterion. SP07 EXECUTES it (not just plans it):
- **(a) Convention-fit re-verification:** confirm the Model C convention (`feature/{name}/{group}` branching, PR templates, feature boards, lead merge gates, session naming) mapped cleanly onto the 6-remote topology where a frontend "feature" = a remote. Specifically: did `feature/mfe-{name}/frontend` → `feature/mfe-{name}/integration` → `develop` (the F1 amendment) hold for all 6 extractions? Did the lead-merges-group / founder-merges-integration split (D1) hold? Did session naming (`mesell-mfe-{name}-frontend-session-{N}`) stay consistent?
- **(b) Agent-obedience audit during the migration:** worktree isolation used (each SP in `/tmp/mesell-wt/`, master tree never branch-switched by a sub-session)? File allowlists respected (no out-of-boundary writes; LOCKED-doc amendments escalated not improvised)? Boards updated at IN REVIEW (specialist, on PR open) / MERGED (lead, on merge) per D2? Iteration caps (3 → founder escalation) honored?
- **(c) Report findings to the founder** — a written audit in `STATUS_FRONTEND.md` + the lead memory, surfaced to the founder via `STATUS_MASTER.md`.
- **(d) Amend `docs/plans/repo_management/MASTER_PLAN.md` IF the convention drifted** — but ONLY with founder approval (§7.3; the repo-mgmt master plan is founder-owned; the frontend lead proposes, the founder ratifies).

**Rationale.** §5.1 is explicit and founder-mandated: "Before Sub-plan 7 is declared complete." It is a META-task — the migration was the first real exercise of the Model C convention at scale (6 features × the branch/board/merge machinery), so the audit captures whether the convention held or needs amendment.

**Consequence.** The audit is a first-class SP07 deliverable (§9 gate). It draws on every SP01–06 memory entry (the recurring `gh pr merge --admin` worktree-branch-delete error, the `$VAR:path` refspec gotcha, the board IN REVIEW/MERGED discipline, the sole-writer board rule). If the convention HELD, the audit records that (no amendment). If it DRIFTED (e.g. the F1 integration-branch amendment to repo-mgmt §1.2 was applied ad-hoc per-sub-plan rather than formally), the audit proposes the amendment for founder ratification. The owner is the frontend-coordinator with master-session review — NOT a specialist (it spans the whole migration's agent behaviour).

### Founder decisions required

1. **FOUNDER-FLAG D42** — author the CSP with the frontend-owned allowlist + the infra-owned ADD-ONLY mechanism, smoke-test on dev first, gate the staging/prod cutover on a GREEN CSP smoke (no CORS/refresh-cookie regression). Joint infra↔frontend. — **RULED 2026-06-11 (founder, morning session): APPROVED as recommended.**
2. **FOUNDER-FLAG D43** — resolve the deferred D9: RELOCATE the shell to `apps/shell/` now (recommended) OR KEEP it at `src/`. — **RULED 2026-06-11 (founder, morning session): APPROVED as recommended (RELOCATE at SP07 cutover).**
3. **Inherited resolution:** D14 (CSP) is RESOLVED by D42; D9 is RESOLVED by D43. D21 (AuthLayout) + D33 (Product/Catalog) were resolved + merged at SP03/SP05.
4. **§5.1 audit (D46)** — the founder REVIEWS the audit findings + ratifies any proposed repo-mgmt amendment (§7.3).

D41 (dead-code removal), D44 (version-pinning), D45 (Gate-4 discharge) are LEAD/infra-level technical decisions. The CSP allowlist content + the audit are frontend-lead deliverables; the CSP mechanism + the infra-side C-conditions are infra deliverables. A FRONTEND_ARCHITECTURE.md LOCKED-doc amendment MAY be warranted IF D43 relocates the shell (the §2 topology doc-sync) — escalate to the founder per §7.3 (do NOT improvise the LOCKED doc).

---

## Agent lineup

| Lead | Specialist / cross-lead | What they do |
|---|---|---|
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-component-builder` (sonnet) | (1) Remove dead shell `loadComponent` imports + the empty `features/` dir (D41); (2) IF the founder approves D43 relocate: move the shell into `apps/shell/` (angular.json `sourceRoot`, tsconfig refs, Tailwind glob simplification, every shell-relative path) — behaviour-preserving; (3) author the dev CSP smoke harness + the version-pinned manifest SHAPE (dev/staging/prod). |
| `meesell-frontend-coordinator` (Frontend Lead) | — (lead-owned) | Owns the CSP origin/token ALLOWLIST (D42 frontend side) + the §5.1 compliance audit (D46) + the full federated smoke orchestration + the Gate-4 discharge sign-off. |
| `meesell-infra-builder` (cross-lead, via memo) | — | The CSP MECHANISM (nginx.conf or Traefik Middleware, ADD-ONLY, no CORS/cookie strip — D42 infra side); the per-env manifest templating + the `remotes(-staging).mesell.xyz` buckets (D44); the infra-side discharge of C-RES-1/2, C-ROUTE-1, C-CI-1, C-STAGING-1 (D45). Coordinated via `handoff_mf_cutover.md`; infra cuts its own `feature/mfe-cutover/infra` group branch if it has work. |

NO new remote, NO extraction. The auth/service-builder is NOT dispatched (the auth contract closed at SP06; the refresh-cookie non-regression is verified by the BACKEND/auth smoke, not a frontend service change). This is the most cross-lead-heavy sub-plan: the CSP is the joint deliverable, and infra owns 4 of the 6 Gate-4 conditions.

### Dispatch order

```
PHASE A — shell strip + (optional) relocation (component-builder)
   A1. Remove any remaining shell-internal loadComponent feature imports from app.routes.ts (all features are remotes now) (D41)
   A2. Remove the empty frontend/src/app/features/ dir (confirm empty after SP01-06)
   A3. IF founder approves D43 RELOCATE: move shell src/ -> apps/shell/src/ (angular.json sourceRoot, tsconfig, Tailwind glob -> ['apps/**','libs/**'], shell-relative paths). Behaviour-preserving. (Skip if KEEP.)
   A4. BUILD CHECKPOINT — shell builds + SHRINKS (no feature chunks); ≤90 s. HARD GATE.

PHASE B — CSP authoring + version-pinned manifests (component-builder + lead + infra memo)
   B1. Lead authors the CSP origin/token allowlist (D42 frontend side) -> memo to infra
   B2. Infra (via memo) implements the ADD-ONLY CSP mechanism (no CORS/cookie strip) + per-env manifest templating + the staging bucket
   B3. component-builder authors the version-pinned manifest SHAPE (dev=localhost, staging/prod={version} URLs) (D44)
   B4. dev CSP SMOKE — the shell loads all 6 remotes WITH the CSP active; the 401->refresh->retry flow still works (no CORS/cookie regression) (D42 / C-CSP-1)

PHASE C — full federated smoke + Gate-4 discharge (lead + infra)
   C1. Full app smoke: every route across all 6 remotes resolves; the auth loop (C5 READ/LOGOUT + C4 WRITE) holds end-to-end; all fallbacks degrade gracefully
   C2. Discharge ALL 6 Gate-4 C-conditions with evidence (D45) — infra side via memo, frontend side (C-CSP-1 allowlist) jointly
   C3. Build-budget final check: shell ≤90 s; each remote within its budget (R4)

PHASE D — the §5.1 compliance audit + close (lead, master-session review)
   D1. EXECUTE the §5.1 audit (D46): convention-fit (a) + agent-obedience (b) across SP00-07
   D2. Report findings -> STATUS_FRONTEND.md + STATUS_MASTER.md (founder surface)
   D3. IF the convention drifted: propose a docs/plans/repo_management/MASTER_PLAN.md amendment for FOUNDER ratification (§7.3 — do NOT improvise)
   D4. Final merge-gate review + the cutover integration PR; declare the migration COMPLETE
```

---

## Code surfaces

Exhaustive inventory. Tags: `MODIFY` / `REMOVE` / `NEW`. Source paths assume the post-SP06 state (all 6 remotes extracted).

### Shell strip (D41)

| # | Path | Tag | Description |
|---|---|---|---|
| 1 | `frontend/src/app/app.routes.ts` | MODIFY | Remove any dead `loadComponent: () => import('./features/...')` lines (none should remain after SP01–06 — confirm + clean). The route table is ALL `loadRemoteWithFallback`/`loadRemoteRoutesWithFallback` + the public/private structure + the `**` wildcard. |
| 2 | `frontend/src/app/features/` | REMOVE | The (now-empty) feature directory — all 11 features are remotes. Confirm empty, then remove. |
| 3 | shell test files that imported a feature directly | REMOVE | Any shell-level integration spec that imported a feature component (it moved to the remote with its spec). Verify the test count reconciles (feature specs now run under `apps/mfe-*/`). |

`RemoteFailureComponent` + `core/load-remote.ts` STAY (host concerns, §6.4).

### Shell relocation (D43 — ONLY if founder approves RELOCATE)

| # | Path | Tag | Description |
|---|---|---|---|
| 4 | `frontend/src/**` → `frontend/apps/shell/src/**` | MOVE | The shell source. Behaviour-preserving. |
| 5 | `frontend/angular.json` | MODIFY | Shell project `sourceRoot`/`root` → `apps/shell`. |
| 6 | `frontend/tsconfig*.json` | MODIFY | Shell path references → `apps/shell/`. |
| 7 | `frontend/postcss.config.mjs` / Tailwind `content` | MODIFY | Simplify glob from `['src/**','apps/**','libs/**']` → `['apps/**','libs/**']`. |

(If KEEP: surfaces 4–7 are skipped; the Tailwind glob retains `src/**`.)

### CSP (D42 — joint; frontend authors the allowlist, infra the mechanism)

| # | Path | Tag | Description |
|---|---|---|---|
| 8 | (infra-owned) shell `nginx.conf` `add_header Content-Security-Policy` OR a Traefik `Middleware` CRD | NEW | The ADD-ONLY CSP with the frontend allowlist (D42). Infra implements; MUST NOT strip CORS or the refresh `Set-Cookie`. |
| 9 | `docs/plans/module_federation/sub_plan_07_csp_allowlist.md` (or in the infra memo) | NEW | The frontend-owned CSP origin/token allowlist (`script-src`/`connect-src`/`style-src`/`font-src`/`img-src`), empirically confirmed on dev. |

### Version-pinned manifests (D44)

| # | Path | Tag | Description |
|---|---|---|---|
| 10 | `frontend/public/federation.manifest.json` (dev) | MODIFY | Dev = localhost-served (unchanged shape). |
| 11 | staging/prod manifest templates (infra-templated) | NEW | `{version}`-pinned `remotes(-staging).mesell.xyz` URLs (D44). Infra owns the envsubst templating; frontend owns the shape + the no-`latest` discipline. |

### Documentation / status / memory / audit

| # | Path | Tag | Description |
|---|---|---|---|
| 12 | `docs/status/feature_board_frontend.md` | MODIFY | `mfe-cutover` row lifecycle + infra inter-lead row (D42/D44/D45). |
| 13 | `docs/status/STATUS_FRONTEND.md` | MODIFY | Updates Log — the cutover smoke, the 6-condition discharge evidence, **the §5.1 audit findings** (D46). |
| 14 | `docs/status/STATUS_MASTER.md` | MODIFY (founder surface) | Surface the §5.1 audit findings to the founder (D46c). |
| 15 | `docs/plans/repo_management/MASTER_PLAN.md` | MODIFY (CONDITIONAL — founder-ratified ONLY) | Amend IF the §5.1 audit found the convention drifted (D46d). The frontend lead PROPOSES; the founder RATIFIES (§7.3). NOT improvised. |
| 16 | `docs/FRONTEND_ARCHITECTURE.md` | MODIFY (CONDITIONAL — founder-ratified ONLY) | A §2 topology doc-sync IF D43 relocates the shell to `apps/shell/`. LOCKED-doc → founder approval (§7.3). |
| 17 | `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_07_cutover.md` | NEW | The cutover record + the Gate-4 discharge evidence + the §5.1 audit findings + the migration-complete milestone. |
| 18 | `docs/plans/module_federation/MASTER_PLAN.md` | MODIFY | §5 row 7 status → DONE + the §11 revision-history close-out (the migration COMPLETE). |

No backend API logic surface (the refresh-cookie non-regression is a VERIFICATION, not a backend change).

---

## Documentation deliverables

Gate conditions in §9. The cutover PR cannot merge to integration without:

1. **`SUB_PLAN_07_cutover_hardening.md`** (this document) — referenced from MASTER_PLAN §5 row 7 + §5.1.
2. **The CSP allowlist** (`sub_plan_07_csp_allowlist.md` or the infra memo) — empirically dev-confirmed (D42).
3. **The version-pinned manifest shape** (dev/staging/prod) + the no-`latest` discipline (D44).
4. **The 6-condition Gate-4 discharge** — every C-condition PASS with evidence (D45).
5. **The §5.1 compliance audit** — convention-fit + agent-obedience findings, reported to the founder, with a proposed repo-mgmt amendment IF drifted (D46). **This is the founder-mandated COMPLETION CRITERION.**
6. **Infra memo** (`handoff_mf_cutover.md`) — the CSP allowlist (→ infra returns the mechanism), the per-env manifest templating + staging bucket, the infra-side 4 C-conditions.
7. **`feature_board_frontend.md` + `STATUS_FRONTEND.md` + `STATUS_MASTER.md`** current; the MASTER_PLAN §5 row 7 marked DONE.

---

## Branch setup

Feature slug `mfe-cutover`. Per F1.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/mfe-cutover/integration` | `develop` (AFTER SP06 merged) | Integration branch | Frontend Lead |
| `feature/mfe-cutover/frontend` | `feature/mfe-cutover/integration` | Shell strip + (optional) relocation + CSP allowlist + version-pinned manifests + the audit | `meesell-angular-component-builder` + Frontend Lead |
| `feature/mfe-cutover/infra` | `feature/mfe-cutover/integration` | The CSP mechanism + per-env manifest templating + the infra-side Gate-4 discharge | `meesell-infra-builder` (infra lead's call per repo-mgmt §1.2 — a group gets a branch if it has work; SP07 infra HAS work) |

This is the FIRST sub-plan likely to use TWO group branches (frontend + infra) merging into one integration branch — a real test of the multi-group merge gate (the §5.1 audit notes this). Both group PRs → integration are reviewed by the FRONTEND lead (D1: lead merges group → integration); the integration → develop PR is the FOUNDER's gate.

### F1 branch-setup commands (EXECUTION stage)

```bash
git fetch origin develop
git checkout develop && git pull --ff-only          # must include SP06's merge

git checkout -b feature/mfe-cutover/integration develop
git push -u origin feature/mfe-cutover/integration

git checkout -b feature/mfe-cutover/frontend feature/mfe-cutover/integration
git push -u origin feature/mfe-cutover/frontend
# infra cuts feature/mfe-cutover/infra from integration in parallel (infra lead's call)

git worktree add /tmp/mesell-wt/mfe-cutover feature/mfe-cutover/frontend
```

### PR flow

```
feature/mfe-cutover/frontend  ──┐
                                ├─ PR (each) — Frontend Lead reviews+merges (squash)   [D1]
feature/mfe-cutover/infra    ──┘
        │
        ▼
feature/mfe-cutover/integration
        │  PR — FOUNDER reviews+merges (merge-commit)    [D1] — + the founder reviews the §5.1 audit here
        ▼
develop  (the migration is COMPLETE)
```

Group → integration: Frontend Lead (BOTH the frontend AND infra group PRs — the lead is the frontend-domain merge gate; infra's group branch merging into a FRONTEND feature's integration is reviewed by the frontend lead per D1, with infra-content review delegated to the infra lead's sign-off in the PR). Integration → develop: Founder. F3 protection; re-probe empirically.

---

## Memory protocol

### Memories the coding-session leads MUST read at start

- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` (own memory — ALL SP00–06 session entries: the recurring `gh pr merge --admin` worktree-branch-delete error, the `$VAR:path` refspec gotcha, the board IN REVIEW/MERGED discipline, the deep-import bundle landmine, the `apps/**/*.spec.ts` test-discovery — these feed the §5.1 agent-obedience audit)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_0[1-6]_*.md` (ALL the extraction recipes + the auth contract — the audit's convention-fit input)
- `docs/plans/module_federation/MASTER_PLAN.md` §4.3 (build pipeline / manifest version-pin), §5.1 (THE audit mandate), §6.6 (version compatibility), §7 R4 (build budget) + R5 (contract drift)
- `docs/plans/infra/GATE4_CONFIRMATION.md` (THE 6 C-conditions to discharge — C-RES-1/2, C-ROUTE-1, C-CI-1, C-CSP-1, C-STAGING-1)
- `docs/plans/repo_management/MASTER_PLAN.md` §1 (branch model) + §2 (merge flow) + §6 (feature_board) + §7 (lead responsibilities, esp. §7.3 LOCKED-doc amendment) — the audit's convention reference
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (GATE4 Option-C; the CSP mechanism options; the per-env bucket plan)

### Cross-feature memos

- **Outgoing → infra (the heaviest of the migration):** `handoff_mf_cutover.md` — the CSP origin/token allowlist (infra returns the ADD-ONLY mechanism + confirms no CORS/cookie strip); the per-env manifest templating + the `remotes-staging.mesell.xyz` bucket; the infra-side discharge of C-RES-1/2, C-ROUTE-1, C-CI-1, C-STAGING-1. 48h SLA. Board row added.
- **Outgoing → backend (verification, not a change):** confirm the 401→refresh→retry flow is unaffected by the CSP (the refresh `Set-Cookie` is not stripped). A lightweight memo or a note in the cutover smoke.
- **Forward-reference:** `sub_plan_07_cutover.md` — the migration-complete record + the §5.1 audit findings (the founder's close-out artefact).

### Session-close memory entries

Session header (`## Session mesell-mfe-cutover-frontend-session-{N}`), D41–D46 outcomes (esp. the D42 CSP go-live + the D43 relocation resolution + the D46 audit findings), the shell-strip + relocation result, the CSP dev-smoke result (no CORS/cookie regression), the version-pinned manifest shape, the 6-condition Gate-4 discharge evidence, the full federated smoke result, **the §5.1 compliance audit findings (convention held / drifted + any proposed repo-mgmt amendment)**, the MIGRATION-COMPLETE milestone, blockers, next-step (Wave 6 real-API wiring — now lands per-remote in its final home).

---

## Dispatch templates

### meesell-angular-component-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-cutover-frontend-session-1

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_07_cutover_hardening.md (this plan — D41 shell strip, D43 relocation IF approved, D44 version-pinned manifests)
- .claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md + sub_plan_05_catalog.md (the helpers + the manifest shape)
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (the bundle landmine; the apps/**/*.spec.ts test-discovery; the Tailwind glob)
- docs/plans/module_federation/MASTER_PLAN.md §2.1 (shell topology), §4.3 (manifest version-pin)

## Your mission
PHASE A: (1) Remove any dead loadComponent feature imports from app.routes.ts (all features are remotes now — confirm NONE remain) (D41). (2) Remove the empty frontend/src/app/features/ dir (confirm empty after SP01-06). (3) IF the lead tells you the founder approved D43 RELOCATE: move the shell src/ -> apps/shell/src/ (angular.json sourceRoot/root, tsconfig refs, Tailwind content glob -> ['apps/**','libs/**'], every shell-relative path) — behaviour-preserving (skip if KEEP). BUILD CHECKPOINT: shell builds + SHRINKS (no feature chunks) ≤90 s. HARD GATE.
PHASE B: (4) Author the version-pinned manifest SHAPE: dev=localhost (unchanged); staging/prod = {version}-pinned remotes(-staging).mesell.xyz URLs (NO 'latest') (D44). The infra lead templates the per-env substitution; you define the shape + the no-latest discipline. (5) Wire the dev CSP smoke harness (the lead provides the allowlist; you verify the shell loads all 6 remotes WITH the CSP active on dev).

## Acceptance criteria
- [ ] no dead loadComponent feature imports in app.routes.ts; frontend/src/app/features/ removed (D41)
- [ ] shell builds + SHRINKS (no feature chunks) ≤90 s; bundle delta noted
- [ ] IF RELOCATE: shell at apps/shell/, Tailwind glob simplified, all paths resolve, behaviour-preserving (tests green)
- [ ] version-pinned manifest shape authored (dev localhost; staging/prod {version} URLs, no 'latest') (D44)
- [ ] dev CSP smoke: the shell loads all 6 remotes WITH the CSP active (the lead's allowlist); the 401->refresh->retry flow unaffected
- [ ] `pnpm test` total == prior baseline, 0 failing/skipped

## Hard constraints
- Do NOT remove RemoteFailureComponent or core/load-remote.ts (host concerns, §6.4 — they STAY)
- Do NOT improvise a FRONTEND_ARCHITECTURE.md amendment (LOCKED — if RELOCATE needs a §2 doc-sync, the LEAD escalates to the founder, §7.3)
- Do NOT author the CSP MECHANISM (that is infra's — you wire the dev SMOKE only); do NOT strip CORS/refresh-cookie headers
- Do NOT touch backend/, k8s/ logic; do NOT change any remote's internals (all 6 are done + merged)

## Files you MAY touch
- frontend/src/app/app.routes.ts (dead-import cleanup), frontend/src/app/features/ (remove), frontend/public/federation.manifest.json + the staging/prod manifest shape
- IF RELOCATE: frontend/apps/shell/** (moved), frontend/angular.json, frontend/tsconfig*.json, frontend/postcss.config.mjs

## Files you must NOT touch
- frontend/apps/mfe-*/** (all 6 remotes done); libs/**; frontend/src/app/core/{remote-failure,load-remote} (STAY); backend/k8s/infra mechanism; the LOCKED FRONTEND_ARCHITECTURE.md

## Final report format
Shell-strip confirmation (no feature chunks, build shrank + seconds), relocation result (if done), the version-pinned manifest shape, the dev CSP smoke result (6 remotes load + refresh-flow unaffected), test count. Then STOP for lead review (the lead runs the Gate-4 discharge + the §5.1 audit).
```

> The CSP mechanism, per-env templating, staging bucket, and the infra-side Gate-4 conditions are dispatched to `meesell-infra-builder` via `handoff_mf_cutover.md` (cross-lead memo, NOT a frontend specialist dispatch). The §5.1 compliance audit (D46) is LEAD-owned (master-session review) — no specialist dispatch.

---

## Review + iteration protocol

### meesell-angular-component-builder (shell strip + relocation + manifest shape)

- **Pre-approval checklist (lead inspects):** (a) `grep -rn "loadComponent.*features" frontend/src` returns ZERO (no dead feature imports — D41); (b) `frontend/src/app/features/` removed (or `frontend/apps/shell/src/app/features/` if relocated — and empty); (c) `RemoteFailureComponent` + `core/load-remote.ts` STILL present (host concerns); (d) the shell build SHRANK (no feature chunks) + ≤90 s; (e) IF RELOCATE: the Tailwind glob simplified + all paths resolve + tests green + behaviour-preserving; (f) the version-pinned manifest shape has NO `latest` (D44); (g) the dev CSP smoke shows all 6 remotes load + the refresh flow unaffected; (h) test count == prior baseline.
- **PR-template gate:** complete, no `<>`; build evidence, bundle delta (the shell SHRINKS — note it), 360/1280 screenshots confirming the federated app renders end-to-end, a11y, boundary output.
- **Re-dispatch triggers:** "left a dead loadComponent feature import" → re-dispatch with the failing grep + D41; "removed RemoteFailureComponent/load-remote" → re-dispatch quoting §6.4 (they STAY); "improvised a LOCKED-doc amendment" → re-dispatch quoting §7.3 (escalate, don't improvise); "manifest uses 'latest'" → quote D44; "CSP stripped CORS/cookie headers" → re-dispatch quoting D42/Gate-4 Answer 4; "relocation broke a path" → re-dispatch with the build error.
- **Iteration cap: 3** → founder escalation.

### Cross-lead (infra) review

- Infra's `feature/mfe-cutover/infra` group PR → integration is reviewed by the FRONTEND lead (D1) with the INFRA lead's content sign-off in the PR. The CSP mechanism MUST be ADD-ONLY (verified: the 401→refresh→retry flow + CORS still work WITH the CSP active). If the CSP strips a CORS/cookie header → reject + re-coordinate via the memo. The infra-side Gate-4 evidence (C-RES/C-ROUTE/C-CI/C-STAGING) must be attached.

---

## Acceptance gate

When every box is `[x]`, `feature/mfe-cutover/integration` is ready for the founder's develop PR — AND the migration is declared COMPLETE.

- [ ] Frontend + infra group PRs (`feature/mfe-cutover/{frontend,infra}` → integration) merged by Frontend Lead (squash)
- [ ] **Shell stripped to a pure host (D41):** no dead `loadComponent` feature imports; `features/` dir removed; `RemoteFailureComponent` + `load-remote.ts` retained; shell build SHRANK + ≤90 s
- [ ] **D43 resolved (FOUNDER-FLAG):** the shell is either RELOCATED to `apps/shell/` (recommended) or KEPT at `src/` per the founder's call; if relocated, behaviour-preserving + tests green + the FRONTEND_ARCHITECTURE §2 doc-sync proposed for founder ratification
- [ ] **CSP authored + dev-smoked (D42 / C-CSP-1, FOUNDER-FLAG):** the shell loads all 6 remotes from `remotes.mesell.xyz` WITH the CSP active on dev; the CSP is ADD-ONLY — the 401→refresh→retry flow + CORS are UNAFFECTED (no `Set-Cookie`/CORS strip); the allowlist is empirically confirmed
- [ ] **Version-pinned manifests (D44 / C-STAGING-1):** dev=localhost; staging/prod = `{version}`-pinned `remotes(-staging).mesell.xyz` URLs (NO `latest`); per-env templating owned by infra
- [ ] **Full federated smoke:** every route across all 6 remotes resolves; the auth loop (SP03 C5 READ/LOGOUT + SP06 C4 WRITE) holds end-to-end; all `loadRemoteWithFallback`/`loadRemoteRoutesWithFallback` fallbacks degrade gracefully on a broken manifest
- [ ] **ALL 6 Gate-4 C-conditions DISCHARGED with evidence (D45):**
  - [ ] C-RES-1 — no in-cluster remote pods (Option A not taken); `kubectl get deploy -n dev` shows only `mfe-shell`
  - [ ] C-RES-2 — shell in-cluster (swapped the retiring `frontend` Deployment, ~0 net CPU); remotes in GCS
  - [ ] C-ROUTE-1 — `remotes.mesell.xyz` resolves + serves `remoteEntry.json` over HTTPS with a GCP-managed cert
  - [ ] C-CI-1 — the `cloudbuild.shell.yaml` + `cloudbuild.remote.yaml` + `dorny/paths-filter` matrix fans out (a remote-only change rebuilds only that remote; a `libs/**` change rebuilds all)
  - [ ] C-CSP-1 — CSP live on dev, ADD-ONLY, no CORS/cookie regression, smoke-tested before staging/prod
  - [ ] C-STAGING-1 — staging remotes off-cluster (`remotes-staging.mesell.xyz`); no in-cluster staging remote pods
- [ ] **§5.1 repo-management compliance audit EXECUTED (D46 — the founder-mandated COMPLETION CRITERION):**
  - [ ] (a) convention-fit re-verified: `feature/mfe-{name}/{group}` → integration → develop held for all 6 extractions; the lead-merges-group / founder-merges-integration split (D1) held; session naming consistent
  - [ ] (b) agent-obedience audited: worktree isolation used (master tree never branch-switched by a sub-session); file allowlists respected; LOCKED-doc amendments escalated not improvised; boards updated at IN REVIEW/MERGED (D2); iteration caps honored
  - [ ] (c) findings reported to the founder via `STATUS_FRONTEND.md` → `STATUS_MASTER.md`
  - [ ] (d) a `docs/plans/repo_management/MASTER_PLAN.md` amendment PROPOSED for founder ratification IF the convention drifted (§7.3 — proposed, not improvised)
- [ ] **Build-budget final:** shell ≤90 s; every remote within its budget (R4); no regression
- [ ] FOUNDER-FLAGs: D42 (CSP go-live) + D43 (relocation) resolved by the founder; D14 + D9 thereby CLOSED; D21 + D33 already merged — *(founder RULED both APPROVED-as-recommended 2026-06-11; this gate is satisfied on execution)*
- [ ] Infra deploy memo (`handoff_mf_cutover.md`) resolved (the CSP mechanism + per-env templating + the infra-side 4 C-conditions); board inter-lead row CLOSED
- [ ] `feature_board_frontend.md` row = MERGED; `STATUS_FRONTEND.md` + `STATUS_MASTER.md` appended; `sub_plan_07_cutover.md` written; MASTER_PLAN §5 row 7 = DONE + the §11 close-out
- [ ] **Founder approval** on `feature/mfe-cutover/integration` → `develop` (founder's gate, NOT the lead's) — AND founder review of the §5.1 audit
- [ ] **THE MIGRATION IS COMPLETE** — all 6 remotes live, CSP enforced, manifests version-pinned, Gate-4 discharged, the convention audited. Wave 6 (real-API wiring) now lands per-remote in its final home.

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-SP7-1 | **CSP strips the refresh-token `Set-Cookie` or a CORS header** — a broad headers middleware (or a misconfigured nginx `add_header`) overrides the app's response headers, breaking the 401→refresh→retry flow → silent logout-loops in production. | Medium | **P0** | D42 + Gate-4 Answer 4: the CSP is ADD-ONLY (exactly one response header); NOT a broad headers middleware. The dev CSP smoke explicitly verifies the 401→refresh→retry flow + CORS WITH the CSP active. Backend verification memo. A regression here is a hard reject. This is the single highest-stakes risk of the cutover. |
| R-SP7-2 | **CSP too strict → remotes don't load** — a missing `script-src`/`connect-src` token (e.g. Angular/es-module-shims needs `'wasm-unsafe-eval'` or a nonce) blocks `remoteEntry.json` → blank pages, worst for the PUBLIC landing + auth pages (every unauthenticated visitor). | Medium | High | D42: the allowlist is empirically confirmed on dev FIRST (C-CSP-1: author + smoke-test on dev before staging/prod). The public-landing (SP04 R-SP4-5) + public-auth (SP06 R-SP6-6) escalations made this the known highest-traffic CSP surface. Iterate the token set on dev until all 6 remotes (esp. the 2 public ones) load. |
| R-SP7-3 | **Shell relocation breaks a path (D43)** — moving `src/` → `apps/shell/` mis-updates an `angular.json`/`tsconfig`/Tailwind path → build break or purged styles. | Medium (if RELOCATE) | Medium | D43: behaviour-preserving move; the build + the full test suite + the federated smoke catch any break. If the founder chooses KEEP, this risk is ZERO. The relocation is done at the post-strip cutover (D41) when the shell is smallest — minimal churn. |
| R-SP7-4 | **A Gate-4 condition can't be discharged** — e.g. C-ROUTE-1's GCP-managed cert isn't provisioned, or C-CI-1's matrix isn't ready, blocking the staging/prod cutover. | Medium | High | D45: each condition has explicit evidence; the infra-side 4 are tracked via `handoff_mf_cutover.md` (48h SLA → founder escalation). The frontend merge (shell strip + dev CSP smoke) does NOT block on the infra conditions (dev-validation uses localhost remotes); the staging/prod CUTOVER blocks on them. So SP07 can merge the frontend cleanup to develop while the infra conditions land in parallel — but the migration is not COMPLETE until all 6 are discharged. |
| R-SP7-5 | **The §5.1 audit finds the convention DRIFTED but no amendment is ratified** — the audit surfaces drift (e.g. the F1 integration-branch amendment was applied ad-hoc per-sub-plan) but the founder hasn't ratified the repo-mgmt amendment, leaving the convention doc out of sync with practice. | Medium | Medium | D46: the audit PROPOSES the amendment (does not improvise it — §7.3); the founder ratifies at the integration→develop PR review. If unratified, the drift is recorded in `STATUS_MASTER.md` as an OPEN founder item — the migration can still be COMPLETE (the audit was executed; the amendment is a follow-up). The audit's EXECUTION is the completion criterion, not the amendment's ratification. |
| R-SP7-6 | **Version-pin drift (R5 endgame)** — a remote ships a new `{version}` to GCS but the manifest isn't updated in lockstep, so the shell still loads the old version (stale) — or worse, a `@mesell/core` model change ships in the shell but a pinned remote is built against the old model. | Low | High | D44 + the C-CI-1 `shared/**`-rebuilds-all rule (SP05 R5): a `@mesell/core` change rebuilds EVERY remote + bumps every pinned `{version}` in lockstep; the manifest is the single source of truth for which version is live; rollback = re-point the manifest. Infra owns the lockstep templating. The version-pin is the R5 mitigation made operational. |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1.1 | 2026-06-11 | `meesell-frontend-coordinator` (founder-ruling landing session) | Landed the founder's 2026-06-11 morning rulings on the two SP07 FOUNDER-FLAGs: **D42 (CSP go-live) APPROVED as recommended** — ADD-ONLY CSP authored at SP07, dev smoke first, staging/prod cutover gated on a GREEN CSP smoke (no CORS/refresh-cookie regression); discharges C-CSP-1, resolves inherited D14. **D43 (shell relocation) APPROVED as recommended** — RELOCATE the shell to `apps/shell/` at SP07 cutover (option 1), resolving the deferred D9; conditional §2 doc-sync proposed for §7.3 ratification at execution time. Additive RULED annotations on the D42/D43 FOUNDER-FLAG blocks + the Founder-decisions-required summary + the §9 FOUNDER-FLAGs acceptance line. No structural change. |
| v1 (DRAFT) | 2026-06-10 | `mesell-module-federation-frontend-session-3` (night-run master-session dispatch) | Initial authoring of Sub-Plan 07 — Federation Cutover & Hardening, THE CLOSER (NOT an extraction). Grounded in the post-SP06 state (all 6 remotes extracted, the auth loop closed) + the GATE4_CONFIRMATION.md 6 C-conditions + MASTER_PLAN §5.1. D41–D46: shell strip to a pure host + features/ removal (D41); AUTHOR the production CSP resolving D14 + discharging C-CSP-1, ADD-ONLY so it does NOT strip CORS or the refresh-token Set-Cookie per Gate-4 (D42 FOUNDER-FLAG); resolve the deferred D9 shell relocation (D43 FOUNDER-FLAG, recommend RELOCATE at the post-strip low-churn moment); version-pin the per-env manifests for rollback + the R5 mitigation (D44); discharge ALL 6 Gate-4 C-conditions with evidence (D45); EXECUTE the founder-mandated §5.1 repo-management compliance audit — convention-fit + agent-obedience across SP00-07, report to the founder, propose a repo-mgmt amendment IF drifted (D46, the COMPLETION CRITERION). Heavy cross-lead: the CSP is a joint infra↔frontend deliverable (frontend owns the allowlist, infra the ADD-ONLY mechanism); infra owns 4 of the 6 C-conditions; FIRST sub-plan with TWO group branches (frontend + infra) into one integration. 6 risks incl. the CSP-strips-refresh-cookie P0 (R-SP7-1), the CSP-too-strict-blocks-public-remotes (R-SP7-2), and the audit-drift-unratified (R-SP7-5). TWO new FOUNDER-FLAGs (D42 CSP go-live, D43 relocation); D14 + D9 thereby CLOSED. A CONDITIONAL FRONTEND_ARCHITECTURE §2 doc-sync IF D43 relocates (founder-ratified, §7.3). On completion the migration is COMPLETE and Wave 6 lands per-remote. Awaits founder approval to EXECUTE; gated on SP01–SP06 merged + infra readiness + the D9 resolution. |

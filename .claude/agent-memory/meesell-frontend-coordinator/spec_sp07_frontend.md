# SP07 — Cutover & Hardening — FRONTEND task spec (for the sonnet specialist)

**Authored:** mesell-mfe-cutover-frontend-session-1 (HYBRID step 1 — SPEC ONLY, no code, no git, no dispatch)
**Authoritative source:** `docs/plans/module_federation/SUB_PLAN_07_cutover_hardening.md` (DRAFT, FOUNDER-FLAGs D42/D43 RULED 2026-06-11)
**Ground-truth tip:** `origin/develop` @ `756d070` (PR #96 merged — ALL SIX remotes coexist).
**Target specialist:** `meesell-angular-component-builder` (sonnet). The CSP allowlist authoring + the §5.1 audit + Gate-4 discharge are LEAD-owned (not in this spec). The CSP MECHANISM is infra (see `spec_sp07_infra.md`).

---

## 0. Session header to use in the dispatch

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-cutover-frontend-session-1
```

The first commit footer carries the session name.

---

## 1. GROUND-TRUTH STATE on develop @ 756d070 (verified by the lead — DO NOT re-assume from the sub-plan prose)

The sub-plan was authored BEFORE SP01–06 executed; several of its D41 assumptions are now already-satisfied by the extractions. The lead verified the ACTUAL state:

- **`frontend/src/app/features/` IS ALREADY GONE.** `git ls-tree -r origin/develop -- frontend/src/app/features/` returns EMPTY. SP01–06's `git mv`s removed every feature. **D41(b) is therefore confirm-only — there is no dir to remove.** If a `features/` dir is somehow present in your worktree, that is a regression — STOP and report.
- **There are ZERO dead `loadComponent: () => import('./features/...')` lines** in `app.routes.ts`. Every feature route is already `loadRemoteWithFallback`/`loadRemoteRoutesWithFallback`. The ONLY non-remote `loadComponent` is the shell layout itself:
  `loadComponent: () => import('./layouts/shell/shell.component').then(m => m.ShellComponent)` — **this STAYS** (it is the shell chrome, a host concern). **D41(a) is therefore confirm-only.**
- **The shell src tree is already a pure host:** `src/app/{app.config.ts, app.routes.ts, app.ts, app.html, app.css, app.spec.ts}`, `src/app/core/{load-remote.ts, remote-failure.component.ts}` (+ their specs), `src/app/layouts/shell/` (chrome), `src/{main.ts, bootstrap.ts, index.html, styles.css}`. NO `core/guards`/`core/interceptors`/`core/api` files exist in the shell — `authGuard`/`AuthService` live in `@mesell/core` (libs/). This matches D41's "shell = pure host" endgame ALREADY.
- **Manifest** `frontend/public/federation.manifest.json` has all 6 entries pointing at `http://localhost:420{1-6}/remoteEntry.json`.
- **Test baseline = 44 spec files / 416 tests, 0 fail / 0 skip** (SP06 merge-gate, re-verified by the lead via `git ls-tree -r origin/develop` spec-file count = 44). Breakdown: apps/ = 15 (auth 4, catalog 4, dashboard 2, export 1, onboarding 3, pricing 1), libs/ = 25 (ui-kit 19, composites 6), src/ = 4 (app.spec 1, core 2, layouts 1). **THIS IS THE NON-REGRESSION GATE: `pnpm test` must report ≥ 416 tests passing, 0 fail / 0 skip after your work.**

**NET CONSEQUENCE: D41 is essentially already done by the extractions.** Your real work is **D43 (relocation)** + the **version-pinned manifest shape (D44)** + wiring the **dev CSP smoke** (the lead provides the allowlist). Do NOT manufacture D41 churn that does not exist.

---

## 2. Mandatory reads (in this order)

1. `docs/plans/module_federation/SUB_PLAN_07_cutover_hardening.md` (D41/D43/D44; the §9 acceptance gate)
2. `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md` (the validated remote-build recipe + the index.html gotcha + the test-discovery dual-include)
3. `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_06_auth.md` (the `pnpm install --config.dangerously-allow-all-builds=true` worktree fix; the concurrent-build trust-the-artifact rule)
4. `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` — esp. the bundle-landmine (deep-import `./ui/providers`, never the barrel, at root), the `apps/**/*.spec.ts` test-discovery gotcha (`include` globs resolve with `cwd = sourceRoot`, NOT workspace root), the keep-both union recipe
5. `docs/plans/module_federation/MASTER_PLAN.md` §2.1 (shell topology `apps/shell/`), §4.3 (manifest version-pin)

---

## 3. THE TASK — three phases, STRICT ORDER

### PHASE A — D41 confirm-only (NO churn) + D43 RELOCATION (the real work)

**A1. Confirm D41 is already satisfied (no edits expected).**
- Run `git grep -n "loadComponent.*features" -- frontend/src` → must return ZERO. (Confirm.)
- Run `ls frontend/src/app/features 2>/dev/null` → must be absent. (Confirm.)
- Run `git grep -n "RemoteFailureComponent\|load-remote" -- frontend/src/app/core` → must show `core/load-remote.ts` + `core/remote-failure.component.ts` PRESENT. **These STAY (host concerns, §6.4). Do NOT remove them.**
- If all three confirm, D41 needs ZERO file edits. Record the confirmation in your report. Do NOT invent removals.

**A2. RELOCATE the shell `frontend/src/` → `frontend/apps/shell/src/` (D43 — founder RULED RELOCATE).**

This is a BEHAVIOUR-PRESERVING mechanical move. The target topology matches the remotes: `apps/shell/` mirrors `apps/mfe-pricing/`. Use `git mv` for every moved file so the move shows as R100 renames (byte-identical) — the lead verifies move-integrity via `git diff -M --summary`.

Files to MOVE (`git mv`):
- `frontend/src/**` → `frontend/apps/shell/src/**` (the entire tree: `app/`, `main.ts`, `bootstrap.ts`, `index.html`, `styles.css`)
- `frontend/public/**` → `frontend/apps/shell/public/**` (assets — the `federation.manifest.json` lives here; it MOVES with the shell)
- `frontend/federation.config.js` → `frontend/apps/shell/federation.config.js` (the shell's federation config; `name: 'shell'` already)

**A3. UPDATE every config path that referenced the old shell location.** This is the blast-radius — the sub-plan calls it "shell-only" but the lead's audit of develop @ 756d070 found it is NOT shell-only because of the single-styles-build pattern. The EXHAUSTIVE touchpoint list:

| File | Current value | New value | Why |
|---|---|---|---|
| `frontend/angular.json` → project `frontend` → `root` | `""` | `"apps/shell"` | project root relocates |
| `frontend/angular.json` → project `frontend` → `sourceRoot` | `"src"` | `"apps/shell/src"` | source relocates |
| `frontend/angular.json` → `frontend.architect.esbuild.options.browser` | `"src/main.ts"` | `"apps/shell/src/main.ts"` | |
| `frontend/angular.json` → `frontend.architect.esbuild.options.tsConfig` | `"tsconfig.app.json"` | `"apps/shell/tsconfig.app.json"` | the shell gets its OWN tsconfig.app.json (see A4) |
| `frontend/angular.json` → `frontend.architect.esbuild.options.assets[0].input` | `"public"` | `"apps/shell/public"` | |
| `frontend/angular.json` → `frontend.architect.esbuild.options.styles[0]` | `"src/styles.css"` | `"apps/shell/src/styles.css"` | the shell's own style entry |
| `frontend/angular.json` → `frontend.architect.test.options.tsConfig` | `"tsconfig.spec.json"` | `"apps/shell/tsconfig.spec.json"` (see A4) | |
| `frontend/angular.json` → `frontend.architect.test.options.include` | `['**/*.spec.ts','../libs/**/*.spec.ts','../apps/**/*.spec.ts']` | **see A5 — test-discovery cwd math CHANGES** | CRITICAL |
| **EACH of the 6 remotes** → `mfe-*.architect.esbuild.options.styles[0]` | `"src/styles.css"` | `"apps/shell/src/styles.css"` | **THE BIG ONE — see A6** |

**A4. The shell's tsconfigs.** Today the shell uses the ROOT `frontend/tsconfig.app.json` + `frontend/tsconfig.spec.json` (every remote has its OWN `apps/mfe-*/tsconfig.app.json`). To make the shell uniform with the remotes, give it its own under `apps/shell/`:
- Create `frontend/apps/shell/tsconfig.app.json` modelled on a remote's (extends `../../tsconfig.json`, `outDir ./out-tsc/app`, `include: ["src/**/*.ts"]` — relative to `apps/shell/`). Remote precedent: `apps/mfe-pricing/tsconfig.app.json`.
- DECISION POINT for the spec-shape (lead ruling, baked in): the ROOT `frontend/tsconfig.spec.json` is the SINGLE test tsconfig the `unit-test` builder uses across the whole workspace (it includes `src/**`, `libs/**`, `apps/**`). **KEEP `frontend/tsconfig.spec.json` at the root** (it is workspace-wide, not shell-specific) BUT update its `include` globs: `src/**/*.spec.ts` → `apps/shell/**/*.spec.ts` (so the shell's 4 specs are still compiled). The `apps/**/*.spec.ts` glob already covers `apps/shell/**` once relocated — so you can simply DROP the `src/**` terms and rely on `apps/**`. Net: `tsconfig.spec.json` include becomes `["apps/**/*.d.ts","apps/**/*.spec.ts","libs/**/*.d.ts","libs/**/*.spec.ts"]`. Update `frontend/tsconfig.app.json` similarly OR retire it in favour of the per-project `apps/shell/tsconfig.app.json` — keep whichever the build target references (you pointed `frontend.architect.esbuild.options.tsConfig` at `apps/shell/tsconfig.app.json` in A3, so the root `tsconfig.app.json` is now unreferenced — you MAY delete it, but confirm `tsconfig.json` `references[]` no longer points at a deleted file).
- Update root `frontend/tsconfig.json` `references[]`: `./tsconfig.app.json` → `./apps/shell/tsconfig.app.json` (and keep `./tsconfig.spec.json`).

**A5. Test-discovery cwd math (THE single highest-risk item — re-read the SP0 gotcha in MEMORY.md).** The `@angular/build:unit-test` builder globs `include` with `cwd = the project's sourceRoot`. After A3, the `frontend` project's `sourceRoot` becomes `apps/shell/src`. So the include globs that were relative to the OLD `src/` cwd MUST be recomputed:
- OLD (cwd was `src/`): `['**/*.spec.ts', '../libs/**/*.spec.ts', '../apps/**/*.spec.ts']` → `**` matched `src/**`, `../libs` matched `frontend/libs`, `../apps` matched `frontend/apps`.
- NEW (cwd is `apps/shell/src/`): to keep matching the SAME files, the relative offsets change:
  - shell's own specs: `**/*.spec.ts` (still cwd-relative — matches `apps/shell/src/**`) ✓
  - libs: `../../../libs/**/*.spec.ts` (up from `apps/shell/src` → `apps/shell` → `apps` → `frontend`, then `libs`)
  - apps (the OTHER remotes): `../../**/*.spec.ts` (up from `apps/shell/src` → `apps/shell` → `apps`, then `**` matches all `apps/*` including the remotes AND shell — harmless re-match, vitest dedups by file path) — OR more precisely `../../mfe-*/**/*.spec.ts` if you want to exclude shell's double-match. **SAFEST: `['**/*.spec.ts', '../../../libs/**/*.spec.ts', '../../**/*.spec.ts']`.**
- **VERIFY EMPIRICALLY:** after the change, `pnpm test` (or `./node_modules/.bin/ng test`) must DISCOVER all 44 spec files and report ≥416 tests. A DROP below 44 files = silent non-discovery = HARD FAIL — re-tune the glob until the count returns. This is the exact failure mode that bit SP0 (401→266). Do not declare done on a count drop.

**A6. The single-styles-build re-point (the non-shell-only blast radius).** All 6 remotes' esbuild `styles[0]` = `"src/styles.css"` (the SHELL's styles.css — the MASTER_PLAN single-Tailwind-build-at-shell pattern). When the shell's styles.css moves to `apps/shell/src/styles.css`, every remote's `styles[0]` must update to `"apps/shell/src/styles.css"` (these paths are workspace-root-relative in angular.json). There are **7 occurrences of `src/styles.css`** in angular.json (6 remotes + shell) — update ALL 7 to `apps/shell/src/styles.css`. Miss one → that remote builds with NO Tailwind/PrimeNG styles (purged/unstyled). Verify with `grep -c "apps/shell/src/styles.css" angular.json` == 7 and `grep -c '"src/styles.css"' angular.json` == 0 after.

**A7. Tailwind `@source` re-point (NOT a `content` glob — the sub-plan's D43 prose is stale).** There is NO `tailwind.config.js` and NO `content: [...]` array. Tailwind v4 scans via `@import "tailwindcss"` (auto-scan of the project) + an explicit `@source "../libs"` directive INSIDE `styles.css`. The `@source "../libs"` is relative to the styles.css file location. Today `frontend/src/styles.css` → `../libs` = `frontend/libs` ✓. After the move to `frontend/apps/shell/src/styles.css`, `../libs` would resolve to `frontend/apps/shell/libs` (WRONG). **Update the directive in the moved styles.css: `@source "../libs"` → `@source "../../../libs"`** (up from `apps/shell/src` → `apps/shell` → `apps` → `frontend`, then `libs`). Also re-check the `@import "../libs/design-tokens/_tokens.css"` line in styles.css → `@import "../../../libs/design-tokens/_tokens.css"`. **This is what the sub-plan meant by "simplify the Tailwind glob" — but the real mechanism is `@source`/`@import` relative-path re-pointing, NOT a `content` array simplification. Record this correction.**

**A8. package.json `start:shell` script.** `"start:shell": "ng serve frontend --port 4200"` references the `frontend` project KEY. **DECISION (lead ruling, baked in): do NOT rename the angular.json project key from `frontend` to `shell` in this slice.** Renaming the key cascades into every `frontend:esbuild:*` target reference (build/serve/test/serve-original all use `frontend:` self-references), the `start:shell` script, AND the C-CI-1 cloudbuild matrix that infra is building in parallel — that is churn beyond "behaviour-preserving" and risks a merge collision with infra's `feature/mfe-cutover/infra` branch. KEEP the project key `frontend` (it is an internal key; the federation.config.js `name: 'shell'` is what the manifest uses). The `apps/shell/` PATH gives the topology uniformity D43 wants; the project KEY rename is a cosmetic follow-up the lead can flag for a later chore. So `start:shell` stays `ng serve frontend --port 4200` (still resolves — the project key is unchanged). **If you believe the key MUST rename, STOP and ask the lead — do not rename unilaterally.**

**A9. BUILD CHECKPOINT — HARD GATE.**
- `pnpm install --config.dangerously-allow-all-builds=true` (worktree esbuild extraction — see SP06 memory; check `find node_modules/.pnpm -path "*@esbuild*darwin*" -name esbuild` if the top-level symlink doesn't resolve).
- `./node_modules/.bin/ng build` (shell) → GREEN, ≤90 s (D12 STOP if exceeded). Note the build seconds + the initial-bundle total. **The shell should NOT shrink further** (D41 already done by extractions — there are no feature chunks left to remove; the SP06 baseline was 60.62 kB initial). If it changes materially, explain why.
- Build at least 2 remotes (e.g. `ng build mfe-pricing`, `ng build mfe-auth`) → GREEN, and CONFIRM their dist carries Tailwind/PrimeNG styles (the A6 re-point worked — the dist `styles-*.css` is non-trivially sized, not empty).
- `pnpm test` → **≥416 tests, 44+ spec files discovered, 0 fail / 0 skip.** This is the A5 verification. HARD GATE.

### PHASE B — version-pinned manifest SHAPE (D44) + dev CSP smoke wiring

**B1. Author the version-pinned manifest SHAPE (D44). The dev manifest stays localhost; staging/prod are templates.**
- `frontend/apps/shell/public/federation.manifest.json` (the DEV manifest — moved in A2) stays EXACTLY as-is: `http://localhost:420{1-6}/remoteEntry.json`. Do NOT change dev.
- Create the staging + prod manifest TEMPLATES (shape only — infra does the envsubst substitution; you define the shape + enforce no-`latest`). Place them where infra can template them; recommended: `frontend/apps/shell/public/federation.manifest.staging.json` and `frontend/apps/shell/public/federation.manifest.prod.json` (OR a `manifests/` sibling dir — confirm the path with the lead's infra memo `handoff_mf_cutover.md`). Shape per remote:
  ```json
  {
    "mfe-pricing":   "https://remotes.mesell.xyz/{ENV}/mfe-pricing/{VERSION}/remoteEntry.json",
    "mfe-export":    "https://remotes.mesell.xyz/{ENV}/mfe-export/{VERSION}/remoteEntry.json",
    "mfe-onboarding":"https://remotes.mesell.xyz/{ENV}/mfe-onboarding/{VERSION}/remoteEntry.json",
    "mfe-dashboard": "https://remotes.mesell.xyz/{ENV}/mfe-dashboard/{VERSION}/remoteEntry.json",
    "mfe-catalog":   "https://remotes.mesell.xyz/{ENV}/mfe-catalog/{VERSION}/remoteEntry.json",
    "mfe-auth":      "https://remotes.mesell.xyz/{ENV}/mfe-auth/{VERSION}/remoteEntry.json"
  }
  ```
  Staging uses `remotes-staging.mesell.xyz` (C-STAGING-1). `{ENV}`/`{VERSION}` are infra envsubst tokens — `{VERSION}` is an EXACT build hash/semver, **NEVER the literal `latest`** (D44 / R5 / R-SP7-6). Add a top-of-file comment: `// VERSION is an exact build hash per remote — NEVER 'latest'. Rollback = re-point VERSION at the prior build.`
- **STOP condition: if any manifest (incl. the templates) contains the token `latest`, that is a D44 violation — fail your own check before reporting.** Run `git grep -i "latest" -- frontend/apps/shell/public/federation.manifest*` → must be ZERO.

**B2. Wire the DEV CSP smoke harness (the LEAD provides the allowlist content — you wire the mechanics).**
- The lead authors the CSP origin/token allowlist (`script-src`/`connect-src`/`style-src`/`font-src`/`img-src`) and hands it to you. The INFRA lead emits the header in the dev environment (nginx/Traefik — `spec_sp07_infra.md`). YOUR job is the FRONTEND-SIDE SMOKE PROOF that the federation still works WITH the CSP active:
  - A headless-capable smoke (extend the SP01 `load-remote.spec.ts` pattern): assert the shell can resolve all 6 remoteEntry URLs from the manifest and that `loadRemoteWithFallback`/`loadRemoteRoutesWithFallback` succeed; assert the D12 fallback fires on a broken URL. This proves remote-loading is not blocked by missing `script-src`/`connect-src` tokens.
  - Because the real CSP header is emitted by infra at the ingress (not by the Angular build), the FULL CSP-active smoke is run by the LEAD against the dev environment (the lead orchestrates the 401→refresh→retry non-regression with backend). YOUR deliverable is the harness + a documented manual smoke procedure the lead runs: load `/` (public landing, mfe-dashboard) and `/login` (public auth, mfe-auth) in a browser with the dev CSP header active and confirm NO `Refused to load`/`Refused to connect` console violations + both remotes mount. **These two public pages (R-SP4-5 landing + R-SP6-6 auth) are the highest-stakes CSP surfaces — call them out explicitly in the harness.**
- Do NOT author the CSP header mechanism (infra's). Do NOT strip/alter any CORS or `Set-Cookie` header — you have no header-authoring surface in the frontend build anyway, but do not add one.

### PHASE C — report + STOP (the lead runs Gate-4 discharge + the §5.1 audit; do NOT)

Stop after Phase B and report. The lead executes the full federated smoke orchestration, the 6 Gate-4 C-condition discharge, the §5.1 compliance audit, and the merge gate. Those are LEAD-owned, not specialist work.

---

## 4. Acceptance criteria (every box checked before you report DONE)

- [ ] D41 confirmed already-satisfied: ZERO `loadComponent.*features` in app.routes.ts; NO `features/` dir; `load-remote.ts` + `remote-failure.component.ts` RETAINED. No churn invented.
- [ ] D43 RELOCATE: shell at `frontend/apps/shell/src/**`; `public/` + `federation.config.js` moved; all moves are `git mv` R100 (byte-identical — the lead verifies via `git diff -M --summary`)
- [ ] angular.json updated: `frontend` project `root=apps/shell`, `sourceRoot=apps/shell/src`, esbuild `browser`/`tsConfig`/`assets.input`/`styles[0]` re-pointed; ALL 7 `src/styles.css` → `apps/shell/src/styles.css` (`grep -c '"src/styles.css"'`==0)
- [ ] `apps/shell/tsconfig.app.json` created (per-project, mirrors a remote); root `tsconfig.json` `references[]` re-pointed; `tsconfig.spec.json` include globs cover `apps/shell/**` (via the `apps/**` term)
- [ ] test-discovery glob recomputed for the new `apps/shell/src` cwd (A5); **`pnpm test` discovers all 44+ spec files, ≥416 tests, 0 fail / 0 skip** (NO drop — the SP0 failure mode)
- [ ] Tailwind `@source` + `@import` in the moved styles.css re-pointed (`../libs` → `../../../libs`); 2 sample remotes build WITH styles present in dist
- [ ] shell builds ≤90 s; build seconds + initial-bundle total noted (no material shrink expected — D41 already done)
- [ ] version-pinned manifest SHAPE authored (dev=localhost unchanged; staging/prod templates with `{ENV}`/`{VERSION}`, `remotes(-staging).mesell.xyz`); **ZERO `latest` tokens** (`git grep -i latest` on manifests == 0)
- [ ] dev CSP smoke HARNESS wired + manual smoke procedure documented (public landing + public auth called out); CSP MECHANISM left to infra; NO CORS/Set-Cookie surface touched
- [ ] PR template (`.github/PULL_REQUEST_TEMPLATE/frontend.md`) filled completely — no `<>` placeholders; build evidence; bundle delta; 360px + 1280px screenshots proving the federated app renders end-to-end (landing + login + dashboard + one catalog route); a11y confirmed; boundary grep output (`grep -rn "from 'primeng" frontend/apps frontend/libs | grep -v libs/ui-kit/` == 0)

---

## 5. STOP / HARD-CONSTRAINT conditions

- **Build > 90 s** → STOP, escalate to lead (D12).
- **Test count drops below 44 files / 416 tests** → STOP, re-tune the test-discovery glob (A5) until it returns; do NOT report DONE on a drop.
- **Any manifest contains `latest`** → STOP, fix (D44).
- **You find yourself removing `RemoteFailureComponent` or `core/load-remote.ts`** → STOP, they STAY (§6.4).
- **A relocation breaks a remote's styling (empty dist styles)** → you missed an A6 `src/styles.css` occurrence — fix all 7.
- **You are tempted to amend `docs/FRONTEND_ARCHITECTURE.md`** (the §2 topology doc-sync) → STOP. It is LOCKED. The LEAD escalates the doc-sync to the founder (§7.3). Do NOT improvise.
- **You are tempted to author the CSP HEADER mechanism, or strip/alter a CORS/`Set-Cookie` header** → STOP, that is infra's (D42 split). You wire the dev SMOKE only.
- **You are tempted to rename the angular.json project key `frontend`→`shell`** → STOP, ask the lead first (A8 — it cascades into CI/scripts; deferred to a later chore).
- **You are tempted to touch `apps/mfe-*/**` internals, `libs/**`, `backend/`, or `k8s/`** → STOP, out of scope (the 6 remotes are done + merged; you only edit their angular.json `styles[0]` line per A6).
- **Iteration cap: 3 re-dispatches → founder escalation.**

---

## 6. Files you MAY touch

- `git mv` the shell tree: `frontend/src/**` → `frontend/apps/shell/src/**`; `frontend/public/**` → `frontend/apps/shell/public/**`; `frontend/federation.config.js` → `frontend/apps/shell/federation.config.js`
- `frontend/angular.json` (the `frontend` project block paths + ALL 7 `src/styles.css` style refs across all projects)
- `frontend/tsconfig.json` (references), create `frontend/apps/shell/tsconfig.app.json`, edit `frontend/tsconfig.spec.json` (include globs), optionally remove the now-unreferenced root `frontend/tsconfig.app.json`
- the moved `frontend/apps/shell/src/styles.css` (`@source`/`@import` re-point)
- `frontend/apps/shell/public/federation.manifest.json` (moved; dev unchanged) + the new staging/prod manifest templates
- a dev CSP smoke spec/harness under `frontend/apps/shell/src/app/core/` (extend the load-remote smoke)
- `.github/PULL_REQUEST_TEMPLATE/frontend.md` is your CHECKLIST (you fill the PR body, not the template file)

## 7. Files you must NOT touch

- `frontend/apps/mfe-*/**` internals (the 6 remotes — DONE + merged; ONLY their angular.json `styles[0]` line per A6, which lives in angular.json not in their tree)
- `frontend/libs/**` (shared libs — frozen)
- `frontend/apps/shell/src/app/core/{load-remote.ts,remote-failure.component.ts}` content (they MOVE but their LOGIC is unchanged — host concerns, STAY)
- `docs/FRONTEND_ARCHITECTURE.md` (LOCKED — lead escalates any §2 doc-sync)
- `backend/`, `k8s/`, the infra CSP mechanism, `cloudbuild.*.yaml`
- `pnpm-workspace.yaml` / `package.json` deps (no dep changes this slice; `start:shell` stays as-is per A8)

## 8. Final report format (then STOP for lead review)

1. D41 confirmation (3 greps, all clean — no churn).
2. Relocation result: `git diff -M --summary` move list (R100 count), the angular.json touchpoint count, the 7-styles-ref re-point confirmation.
3. Build: shell seconds + initial total; 2 sample remotes GREEN with styles-in-dist confirmed.
4. Test: file count + test count (must be ≥44/416, 0 fail/skip) + the discovery-glob value used.
5. Tailwind `@source`/`@import` re-point confirmation.
6. Version-pinned manifest shape (paths + the no-`latest` grep == 0).
7. Dev CSP smoke harness + the documented manual procedure (public landing + auth called out).
8. Open questions / anything you stopped on.

Then STOP. The lead runs Gate-4 discharge + the §5.1 audit + the merge gate.

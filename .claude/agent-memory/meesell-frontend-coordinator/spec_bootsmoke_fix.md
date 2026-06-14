# SPEC — Finish the boot-smoke gate (#213): retarget to the `ng serve` dev path

**Author:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-13
**Specialist:** `meesell-angular-service-builder`
**Session header to carry:** `mesell-bootsmoke-frontend-session-1`
**HYBRID rule 7:** this is step 1 (SPEC ONLY). The specialist writes the code; the Lead runs the merge-gate review (step 3) against §7 below.
**Branch model (D1):** `feature/bootsmoke/frontend` → `feature/bootsmoke` (Lead merges); `feature/bootsmoke` → develop is the founder's gate.

---

## 1. Problem diagnosis (precise, with citations)

The `frontend-boot-smoke` job in `.github/workflows/ci.yml` HANGS and never goes green.

- **Job:** `.github/workflows/ci.yml` lines **711–879** (`frontend-boot-smoke`), `timeout-minutes: 90` (line 727 — already bumped 25→90 in commit `96d84d7`, masking the real problem).
- **Root cause — the 7 sequential PRODUCTION builds, lines 757–784.** The first one, **"Build shell"** (lines **758–760**: `pnpm exec ng build frontend --configuration production`), stalls ~24 min on a cold CI runner inside Native Federation's "Preparing shared npm packages" step. The remaining six remote prod builds (lines 762–784) each repeat NF prepare work. Total wall time approaches the 90-min ceiling → the gate is effectively hung, never delivering a usable signal.
- **The harness itself is GOOD — do NOT rewrite it.** `frontend/tools/boot-smoke/boot-smoke.js` already implements the F-001-immune assertions: HTTP-200 document capture (lines 213–228, 252–259), real per-route selectors (`assertRealSelector`, lines 91–160: `app-landing` for `/`, `mee-login`+`form`+`mee-input` for `/login`, authGuard redirect for `/profile`), zero hard console errors / zero pageerrors (lines 264–268), RemoteFailureComponent = FAIL (lines 92–102), AND it already emits screenshots per route×width (lines 270–278) + a JSON results file (line 362). The problem is 100% in the CI *driver* (prod-build + static-serve), not the harness.
- **`frontend/tools/boot-smoke/serve.js`** is the static SPA-fallback server used by the prod-build path (CORS headers + index.html fallback, lines 55–117). It only matters if we keep the prod-build path. Under the recommended dev-path fix below, `serve.js` is **no longer used** by CI (the `ng serve` processes provide their own SPA fallback) — leave the file in place (it documents the prod-serve behaviour and may be reused later) but the workflow stops invoking it.

---

## 2. Fix strategy — RECOMMENDATION (single, definite)

**RETARGET the boot-smoke gate to drive the `ng serve` dev path** — boot the shell + 6 remotes via
`pnpm run start:all` (`tools/dev/start-all.mjs`), then run the EXISTING `boot-smoke.js` against
`http://localhost:4200`. Drop the 7 production builds and `serve.js` from the CI job.

**Justification (the three reasons, plus a fourth):**

1. **It matches reality.** `start:all` is the exact command the founder runs locally (see `frontend/RUNBOOK.md`). The gate then proves *the thing we actually ship to a developer's machine* boots — not an artificial prod-static arrangement.
2. **It sidesteps the NF prod-prepare stall.** `ng serve` (dev) does the NF shared-package prepare incrementally with the dev cache and does NOT hit the cold prod "Preparing shared npm packages" 24-min wall. This is the single change that takes the job from ~90 min → minutes.
3. **It still catches the F-001 class.** F-001 was a native-federation import-map subpath miss that is build-green / browser-dead. The Playwright harness asserts the document is 200, real selectors mount, and there are zero "Unable to resolve specifier" console errors — those fire identically under `ng serve` (the import map is generated the same way; a subpath miss still throws at runtime in the browser). The dev path does NOT weaken F-001 detection.
4. **It removes a whole class of prod-only flakiness** (manifest-localhost assertion, serve.js CORS, 7-way readiness race) that has cost multiple commits (`9e49e6a`, `449fe09`, `e293b35`, `96d84d7`) without ever producing a green run.

**Alternative (DO NOT implement unless the founder overrides the recommendation):** keep the 7 prod builds but add caching — cache `frontend/.angular/` (Angular build cache) AND the Native Federation prepare output (`frontend/node_modules/.cache/native-federation` / the `@angular-architects/native-federation` prepare dir) keyed on `pnpm-lock.yaml` + `federation.config.js`, via `actions/cache@v4`, and build the 7 units with `--max-workers`/parallelism. This is strictly more complex, still slower than dev, and does not match what the founder runs. State it as the fallback only.

> **Recommendation stands: retarget to the dev `ng serve` path.**

---

## 3. Required behaviour of the retargeted job

The specialist rewrites ONLY the `frontend-boot-smoke` job body in `.github/workflows/ci.yml`. New step sequence:

1. Checkout, setup Node 22, setup pnpm 11.5.2 (unchanged, lines 730–741).
2. `pnpm install --frozen-lockfile` + `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract` (unchanged, lines 743–750) — `ng serve` needs the native binaries too.
3. `npx playwright install --with-deps chromium` (unchanged, lines 752–754).
4. **REPLACE lines 757–784 (the 7 prod builds) with a single backgrounded `pnpm run start:all`.** Start it with `nohup`/`&` (or `run_in_background`-equivalent in CI: append `&`), redirect combined output to a log file uploaded as an artifact for diagnosis.
5. **REPLACE the manifest-localhost assertion (lines 786–799) — it is unnecessary on the dev path** (dev manifest already points at localhost:4201–4206; no dist/ manifest is produced). Drop it.
6. **REPLACE the readiness gate (lines 818–848)** with a dev-equivalent bounded poll: wait (bounded loop, hard-fail with a clear message) until `http://localhost:4200` (shell) AND each remote `http://localhost:420{1..6}/remoteEntry.json` return 200. `ng serve` does NOT serve a literal `/index.html` path the same way — poll `http://localhost:4200/` (root) for the shell, not `/index.html`. ALSO keep the SPA-fallback proof: `curl http://localhost:4200/login` must return 200 (dev server provides history fallback natively).
   - **Allow generous readiness budget** but keep it bounded: the FIRST `start:all` on a cold runner does NF cold-prepare per server. Budget up to ~6–8 min for readiness (NOT 90). If not ready by the bound, hard-fail with the captured `start:all` log tail so the failure is diagnosable — do NOT silently hang.
7. **Run boot smoke (unchanged, lines 851–857)** against `SMOKE_SHELL_URL: http://localhost:4200` with the existing screenshot + results env. No change to `boot-smoke.js`.
8. **Upload artifacts — CHANGE from `if: failure()` to ALWAYS upload screenshots + results** (see §4 — the founder wants the images regardless of pass/fail). Also upload the `start:all` log.
9. Teardown: kill the `start:all` process group (`if: always()`).
10. **Set `timeout-minutes: 15`** on the job (down from 90) — comfortably above the <10 min target, hard ceiling so a regression can never hang for an hour again.

---

## 4. Screenshots — the founder MUST get actual screen images

- The harness already screenshots every route×width to `SMOKE_SCREENSHOT_DIR` (CI: `tools/boot-smoke/screenshots`). **The CI artifact upload must become unconditional** (`if: always()`, not `if: failure()`) so a GREEN run still publishes `boot-smoke-{root,login,profile}-{360,1280}px.png` as a downloadable artifact. This is the founder's "I want to see the screen" deliverable.
- **Local-run path:** when run locally, screenshots already land at `frontend/tools/boot-smoke/screenshots/` (the `boot-smoke.js` default, line 48 — `path.join(__dirname, 'screenshots')`). DO NOT change that default. Add a one-line note to `frontend/tools/boot-smoke/README.md` documenting: "After a local run (`pnpm run start:all` in one terminal, then `pnpm run smoke:boot` in another), the screen images are at `frontend/tools/boot-smoke/screenshots/`." This gives the founder a known local path with real screen images.
- Minimum routes captured (already in the harness, do NOT reduce): `/` and `/login` at both 360px and 1280px. `/profile` (authGuard redirect) also captured — keep it.

---

## 5. Exact acceptance criteria

The retargeted gate is DONE when:

1. **Runtime bound:** the `frontend-boot-smoke` job completes in **< 10 min** on a cold CI runner (job `timeout-minutes: 15` as a hard ceiling).
2. **Real DOM assertion (not tautology):** the gate passes ONLY because `boot-smoke.js` asserted the shell DOM rendered real content — `app-root` has children, `app-landing` (route `/`) is present and non-empty, `mee-login`+`form`+`mee-input` (route `/login`) are present, zero hard console errors, zero pageerrors. (These assertions already exist; the spec forbids weakening them.)
3. **`/login` and `/` reachable** and asserting their real selectors; `/profile` redirects to `/login` and asserts `mee-login`.
4. **Screenshots emitted** for `/` and `/login` (min) at 360 + 1280, uploaded as a CI artifact on **both pass and fail**, and present at `frontend/tools/boot-smoke/screenshots/` on a local run.
5. **CI workflow YAML changes enumerated in the PR body** — every changed line range in `frontend-boot-smoke`, with before/after.
6. **No change to the F-001 app.config barrel import in this task.** The barrel-import follow-on (the `@mesell/ui-kit` deep-vs-barrel concern) is a SEPARATE task. This gate's job is only to PROVE boot works; it does not refactor app wiring. If the gate goes green, F-001 is proven cleared at runtime.

---

## 6. Lane discipline (what the specialist may touch)

ONLY these files:

- `.github/workflows/ci.yml` — the `frontend-boot-smoke` job body ONLY (lines 711–879). Do NOT touch any backend gate, the frontend-build matrix, build/deploy, or nightly jobs.
- `frontend/tools/boot-smoke/README.md` — add the local-screenshot-path note (§4).
- `frontend/package.json` — ONLY if a `smoke:boot` convenience already exists it does (line 17); confirm `start:all` exists (it does, on develop, line 17-equivalent). No NEW dependency. No new script unless strictly required to background `start:all` in CI (prefer inlining `&` in YAML — no script change needed).

FORBIDDEN: `boot-smoke.js` (harness is correct — touching it risks reintroducing a false-pass), `serve.js`, `app.config.ts`, `app.routes.ts`, any `libs/**`, any feature/remote source, `federation.config.js`, `federation.manifest.json`.

---

## 7. Merge-gate criteria the LEAD will check (HYBRID step 3)

When the specialist opens `feature/bootsmoke/frontend` → `feature/bootsmoke`, the Lead REJECTS unless ALL hold:

1. **Real DOM assertion preserved, not a tautology.** `boot-smoke.js` is unchanged (diff shows zero lines touched in that file). The pass condition still requires `realSelectorMounted` + `zeroHardConsoleErrors` + `zeroPageErrors` + `docStatus200`. A gate that passes on a blank/404 body is an automatic reject.
2. **Screenshots present.** PR body links/attaches the CI artifact (or a local run) showing `/` and `/login` at 360 + 1280 — actual rendered screens, not blank. Artifact upload is `if: always()`.
3. **Runtime bound met.** A CI run of the job shows wall-clock < 10 min; `timeout-minutes` set to 15. PR body quotes the actual job duration from the green run.
4. **Lane discipline.** `git diff --name-only` shows ONLY `.github/workflows/ci.yml` + `frontend/tools/boot-smoke/README.md` (+ at most a justified `package.json` script line). Any other path = reject.
5. **F-001 app.config barrel import untouched** — `app.config.ts` not in the diff.
6. **PR template fully filled** (`.github/PULL_REQUEST_TEMPLATE/frontend.md`, no `<>` placeholders), Session block = `mesell-bootsmoke-frontend-session-1`, board row flipped to IN REVIEW by the specialist on PR open (D2).
7. **Evidence the gate actually went GREEN once** (a CI run link on the branch). A spec'd-but-never-observed-green gate is not done.

---

## 8. Notes for the specialist

- `start:all` and `tools/dev/start-all.mjs` exist on develop (confirmed). The federation manifest
  (`apps/shell/public/federation.manifest.json`) maps mfe-pricing:4201, mfe-export:4202,
  mfe-onboarding:4203, mfe-dashboard:4204, mfe-catalog:4205, mfe-auth:4206. Shell on 4200.
- The harness tests routes `/`, `/login`, `/profile` — which require shell + mfe-dashboard (4204) +
  mfe-auth (4206). All 6 remotes must be up anyway because the shell manifest references them and a
  missing remote could surface RemoteFailureComponent. `start:all` boots all 7 — correct.
- This is a CI-driver change. The specialist is `meesell-angular-service-builder` because the work is
  build/serve wiring + CI plumbing (no component or styling change). No code in `src/` or `apps/`.

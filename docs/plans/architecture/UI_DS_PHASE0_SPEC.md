# UI Design-System Decoupling — Phase 0 BUILD SPEC

**Status:** BUILD SPEC (Step 1 of the MeeSell HYBRID dispatch — no code in this doc).
**Date:** 2026-06-16
**Author:** `meesell-frontend-coordinator` (Frontend Lead).
**Parent plan:** `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` → §4 "Phase 0 — Scaffolding & contract harness".
**Phase 0 mandate (verbatim from parent §4):** create the `@mesell/layout` lib skeleton; create `frontend/tools/contracts/` + `run-all.mjs` (rules start **warn-only**); add a **non-blocking** CI job. **No behavior change, no component code, no migrations.**

---

## 0. Hard guardrails for this phase

1. **NO component code.** No `mee-icon`, no aggregator arrays, no layout primitives. The `@mesell/layout` barrel ships an **empty** `MEE_LAYOUT = []` + a TODO. Those are Phases 1–4.
2. **NO migration.** The 3 `pi pi-*` leaks (`apps/shell/.../shell.component.{ts,html}` ×2, `apps/mfe-catalog/.../smart-picker.component.ts`) and the `mee-button` `MATERIAL_TO_PI` map are **NOT** touched here — they are flagged WARN-only and fixed in Phase 1.
3. **NO strict mode.** Every scanner is warn-only; `run-all.mjs` exits **0** in Phase 0 regardless of violation count. A `--strict` flag exists but is NOT exercised by CI in Phase 0.
4. **NO new npm deps.** Scanners are dependency-free Node ESM (`fs` + `path` + a hand-rolled recursive walk), mirroring the backend `check_*.py` AST-scanner idiom (small, single-purpose, runnable standalone).
5. **NO backend, k8s, or LOCKED-doc edits.** Do not touch `backend/`, `k8s/`, `docs/legal/`, or `docs/FRONTEND_ARCHITECTURE.md`.
6. **Do not modify any existing component or MFE.** Only NEW files + two small additive edits (`tsconfig.json` paths block, `.github/workflows/ci.yml` new job).

---

## 1. Measured baseline (verified 2026-06-16 — drives scanner allow-lists)

These were grepped against the live worktree and **define the expected Phase-0 WARN output**:

| Contract | Current violations (warn-only target) | Notes |
|---|---|---|
| **FE-1** PrimeNG seal | **0** real import leaks. | `primeng`/`@primeuix` strings DO appear in every `apps/*/federation.config.js` (shareAll list + an `// F-001` comment) — these are **share-config, NOT TS imports** and MUST be excluded. The seal is already clean for real imports (PR #38). |
| **FE-2** Icon seal | **3 files** with raw `pi pi-*`: `apps/shell/src/app/layouts/shell/shell.component.ts`, `…/shell.component.html`, `apps/mfe-catalog/src/app/smart-picker/smart-picker.component.ts`; plus `mee-button`'s `MATERIAL_TO_PI` map inside ui-kit (allowed — it's inside ui-kit, but the registry file does not exist yet). | Phase 1 migrates these. Warn-only now. |
| **FE-3** Chrome shell-only | **0** today (no chrome primitives exist yet; `ShellComponent` lives in `apps/shell` and is imported by nothing). | Becomes meaningful after Phase 4. |
| **FE-4** Lib DAG | **0** back-edges expected (current DAG: `composites → core/ui-kit`; `@mesell/layout` is empty). | `@mesell/layout` is new + empty, so no edges yet. |
| **FE-5** Public barrels | **Pre-existing deep imports exist** (`@mesell/ui-kit/*`, `@mesell/composites/*` subpath imports — the intentional lean-bundle pattern from PR #38/SP0). | These will warn. That is acceptable in Phase 0 (warn-only). Phase 5 decides the final allow-list. **The scanner MUST treat `@mesell/*/*` deep imports as WARN, never error, in Phase 0**, and a documented allow-list seed is provided in §3.6 so Phase 5 can tighten without churn. |

**Key correctness fact for the builder:** the FE-1 scanner that naively greps `primeng` across all files **will false-positive on 7 `federation.config.js` files**. It MUST (a) only scan `.ts` + `.html` source files, and (b) only match real ES import/`import(...)`/`require(...)` forms — not bare substring `primeng`. See §3.2.

---

## 2. Files to create / edit (manifest)

| # | Path (absolute) | Action | Owner-builder |
|---|---|---|---|
| F1 | `frontend/libs/layout/index.ts` | CREATE | service-builder |
| F2 | `frontend/tsconfig.json` | EDIT (paths block — add 2 aliases) | service-builder |
| F3 | `frontend/tools/contracts/run-all.mjs` | CREATE | service-builder |
| F4 | `frontend/tools/contracts/_walk.mjs` | CREATE (shared helper) | service-builder |
| F5 | `frontend/tools/contracts/fe1_no_primeng_outside_uikit.mjs` | CREATE | service-builder |
| F6 | `frontend/tools/contracts/fe2_no_raw_pi_icons.mjs` | CREATE | service-builder |
| F7 | `frontend/tools/contracts/fe3_chrome_shell_only.mjs` | CREATE | service-builder |
| F8 | `frontend/tools/contracts/fe4_lib_dag.mjs` | CREATE | service-builder |
| F9 | `frontend/tools/contracts/fe5_public_barrels_only.mjs` | CREATE | service-builder |
| F10 | `frontend/tools/contracts/README.md` | CREATE (short — what each contract is, warn→strict roadmap) | service-builder |
| F11 | `.github/workflows/ci.yml` | EDIT (add 1 non-blocking job) | service-builder + **infra coordination** (see §5) |

> **No `package.json` edit.** Do NOT add an npm script or a dependency. The CI job calls `node tools/contracts/run-all.mjs` directly. (Optional: a `"contracts": "node tools/contracts/run-all.mjs"` script is *permitted* but not required — if added, it is the ONLY package.json change and must not alter deps. Default recommendation: skip it to keep the diff minimal.)

---

## 3. Per-file spec

### F1 — `frontend/libs/layout/index.ts` (CREATE)

**Purpose:** placeholder public barrel for the new `@mesell/layout` tier (DAG: `composites → layout → ui-kit`). Path-mapped TS lib — **NOT** Nx, **NOT** a buildable ng-package; it compiles INTO each consumer via tsconfig path aliases, exactly like `@mesell/ui-kit`/`@mesell/composites`.

**Required content (behavioral spec, builder writes the literal TS):**
- Export a `const MEE_LAYOUT` typed as a readonly array, value `[]` (empty). It is the future page-primitive aggregator (parent §3.1 row `MEE_LAYOUT`).
- A top-of-file comment block: this is Phase 0 scaffolding; page primitives (`mee-page`, `mee-section`, `mee-toolbar`, `mee-grid`, `mee-form-layout`) land in Phase 3 and chrome primitives in Phase 4; `MEE_LAYOUT` will be spread into standalone `imports`.
- A `// TODO(Phase 3):` line naming the primitives to come.
- Must be a valid TS module that `tsc` resolves with zero errors and zero unused-symbol complaints (an exported empty `const` is fine).

**Acceptance:** `tsc -p frontend/tsconfig.json --noEmit` resolves `import { MEE_LAYOUT } from '@mesell/layout';` with no error; the barrel exports exactly one symbol (`MEE_LAYOUT`); no PrimeNG / Angular runtime imports.

---

### F2 — `frontend/tsconfig.json` paths block (EDIT — additive only)

**Purpose:** register the `@mesell/layout` path aliases, mirroring the existing `@mesell/ui-kit` / `@mesell/composites` pattern (a barrel alias + a deep-subpath wildcard alias).

**Exact additions (insert inside `compilerOptions.paths`, keeping alphabetical-ish grouping with the other `@mesell/*` entries):**
```jsonc
"@mesell/layout": ["libs/layout/index.ts"],
"@mesell/layout/*": ["libs/layout/*"],
```
**Constraints:**
- Edit ONLY the `paths` object. Do NOT touch `strict`, `strictTemplates`, `references`, or any other key.
- The wildcard `@mesell/layout/*` is included now (even though no subpaths exist) for parity with `@mesell/ui-kit/*` and to keep Phase 3/4 from needing a tsconfig edit.
- App/spec tsconfigs (`apps/*/tsconfig.app.json`, `tsconfig.spec.json`) `extends` this root config, so the alias **propagates automatically** — do NOT edit them.

**Acceptance:** `pnpm exec ng build shell --configuration production` (or `./node_modules/.bin/ng build frontend`) still succeeds; `@mesell/layout` resolves from any app/lib; no other path entry changed (diff is exactly +2 lines).

---

### Scanner harness — shared conventions (apply to F3–F9)

All scanners are **Node ESM** (`.mjs`), **zero-dependency** (`node:fs`, `node:path` only), runnable two ways, mirroring the backend `check_*.py` contract idiom:
- `node tools/contracts/<scanner>.mjs` — runs that one scanner standalone, prints violations.
- Imported by `run-all.mjs` via a named export `export function scan(opts) { … }` returning `{ contract, violations: [{file, line, snippet, reason}] }`.

Shared rules:
- **CWD assumption:** scanners are invoked from `frontend/` (the CI job sets `working-directory: frontend`). All roots are resolved relative to a `REPO_FE` constant = the dir containing `tools/` (compute via `fileURLToPath(import.meta.url)` → up to `frontend/`), so they also work when invoked from elsewhere.
- **Recursive walk** lives once in `_walk.mjs` (F4): `walk(dir, { exts })` yields absolute file paths, **skipping** `node_modules`, `dist`, `out-tsc`, `.angular`, `.git`, `coverage`, and any `*.spec.ts` is INCLUDED unless a scanner opts out (FE-1/FE-2 include specs; FE-5 may exclude specs — see each).
- **Line-accurate reporting:** each violation prints `relative/path.ts:LINE: <trimmed source line>` plus a one-line `reason`. Mirror the backend scanner output style (path:line + message).
- **Warn-only contract:** each scanner's `scan()` NEVER calls `process.exit`. Only `run-all.mjs` decides exit code.
- **No regex catastrophes:** keep patterns simple and line-based (read file, split on `\n`, test each line). No multi-line AST parsing needed for Phase 0.

---

### F4 — `frontend/tools/contracts/_walk.mjs` (CREATE — shared helper)

**Purpose:** the single recursive directory walker + small shared utilities (path-relativize, read-lines), so the 5 scanners stay DRY and dependency-free.

**Required exports (behavioral):**
- `walk(absDir, { exts: string[] })` → generator/array of absolute file paths with a matching extension, pruning the ignore-dir set listed above.
- `feRoot()` → absolute path to `frontend/` (derived from `import.meta.url`).
- `rel(absPath)` → path relative to `frontend/` using POSIX separators (stable cross-platform output).
- `readLines(absPath)` → `string[]`.

**Acceptance:** importing `_walk.mjs` and walking `libs/ui-kit` yields the wrapper `.ts` files and excludes `node_modules`; no third-party import anywhere.

---

### F5 — `fe1_no_primeng_outside_uikit.mjs` (CREATE) · Contract FE-1

**Rule:** no PrimeNG / PrimeUIX **import** outside `frontend/libs/ui-kit/`.

**Scan set:** `.ts` + `.html` files under `frontend/apps/**`, `frontend/libs/**`, `frontend/src/**` (src may not exist post-relocation; tolerate absence). **INCLUDE** `*.spec.ts`.

**Allow-list (NOT flagged):**
- Anything under `frontend/libs/ui-kit/` (the sealed boundary).
- **`federation.config.js` files are NOT in the scan set** (only `.ts`/`.html` are scanned) — this is the critical false-positive guard (7 config files reference `'primeng'`/`'@primeuix'` as share strings + a comment).

**Match (flag) — line-based, only real import forms:**
- `import … from '<spec>'` / `import '<spec>'` where `<spec>` starts with `primeng` or `@primeuix` (e.g. `primeng/button`, `@primeuix/themes`, `@primeuix/themes/aura`).
- Dynamic `import('<spec>')` and `require('<spec>')` with the same prefixes.
- Match the **module-specifier string**, not a bare substring — i.e. the prefix must appear inside the quotes of an import/require/dynamic-import. A comment line mentioning `primeng` is NOT flagged (comments are not import statements; a simple guard: the line must contain `import`/`require` AND the quoted specifier).

**Reason string:** `FE-1: PrimeNG/@primeuix may only be imported inside libs/ui-kit/.`

**Phase-0 expectation:** **0 violations** (already clean). If any appear, they are real regressions worth the warn line.

---

### F6 — `fe2_no_raw_pi_icons.mjs` (CREATE) · Contract FE-2

**Rule:** no raw `pi pi-*` icon class outside the (future) icon registry file `frontend/libs/ui-kit/icon/icon.registry.ts`.

**Scan set:** `.ts` + `.html` under `frontend/apps/**`, `frontend/libs/**`, `frontend/src/**`. INCLUDE specs.

**Allow-list (NOT flagged):**
- `frontend/libs/ui-kit/icon/icon.registry.ts` (the one permitted file — may not exist yet in Phase 0; allow-list it anyway so Phase 1 needs no scanner edit).
- **Also allow `frontend/libs/ui-kit/button/` `MATERIAL_TO_PI` map** for Phase 0 ONLY (it lives inside ui-kit). Implement this as an allow-prefix of `frontend/libs/ui-kit/` for FE-2 in Phase 0 — i.e. **any `pi pi-` inside ui-kit is allowed in Phase 0**; Phase 1 narrows the allow-list to exactly the registry file. Document this narrowing in F10/README so Phase 1 knows to tighten it.

**Match (flag):** the literal token `pi pi-` followed by a word char (regex `pi\s+pi-[a-z]`), anywhere in a scanned line outside the allow-list. This catches both template strings (`icon: 'pi pi-home'`) and HTML class attributes.

**Reason string:** `FE-2: raw 'pi pi-*' is only allowed in libs/ui-kit/icon/icon.registry.ts — use a MeeIconName semantic.`

**Phase-0 expectation:** the **3 known leak files** warn (shell.component.ts, shell.component.html, smart-picker.component.ts). Builder must confirm the count is exactly 3 files (the baseline) — more = an undiscovered leak; fewer = a scan-set bug.

---

### F7 — `fe3_chrome_shell_only.mjs` (CREATE) · Contract FE-3

**Rule:** MFEs (`apps/mfe-*`) must not import shell chrome primitives or `ShellComponent`.

**Scan set:** `.ts` files under `frontend/apps/mfe-*/**` (the remotes ONLY — the shell at `apps/shell/**` is exempt; it OWNS the chrome).

**Match (flag) — import specifiers referencing chrome:**
- An import whose specifier resolves to `ShellComponent` (e.g. `from '…/layouts/shell/shell.component'`, or a future `@mesell/layout` chrome subpath).
- An import of any future chrome primitive name. **Phase 0 seed allow-list of chrome identifiers to flag when imported:** `ShellComponent`, `MeeAppBarComponent`/`mee-app-bar`, `MeeSideNavComponent`/`mee-side-nav`, `MeeNavItemComponent`/`mee-nav-item`, `MeeUserMenuComponent`/`mee-user-menu`. (None exist yet — this is a forward-compat list so Phase 4 needs no scanner edit.) Match on the imported **symbol name** OR a specifier path segment `/shell/shell.component` / `@mesell/layout/chrome`.

**Reason string:** `FE-3: chrome primitives and ShellComponent are shell-only — MFEs must not import them.`

**Phase-0 expectation:** **0 violations** (no MFE imports chrome today). Becomes load-bearing after Phase 4.

---

### F8 — `fe4_lib_dag.mjs` (CREATE) · Contract FE-4

**Rule:** lib imports flow strictly `composites → layout → ui-kit` (→ `core`/`primeng` at the base). No back-edges, no cycles. Concretely, **forbidden edges:**
- `libs/ui-kit/**` importing `@mesell/layout` or `@mesell/composites`.
- `libs/layout/**` importing `@mesell/composites`.
- (DAG tiers — declare the order as data: `ui-kit` rank 0, `layout` rank 1, `composites` rank 2. A file in tier *r* may import a `@mesell/*` lib of tier *< r* only; importing tier `>= r` is a back-edge/cycle and is flagged. `@mesell/core` and `@mesell/design-tokens`/`@mesell/env` are rank-0 shared bases — importable by all, importing none of the UI tiers.)

**Scan set:** `.ts` files under `frontend/libs/**` (exclude specs is OPTIONAL; recommended to INCLUDE so a test file can't sneak a back-edge).

**Match (flag):** an `import … from '@mesell/<lib>'` (barrel or `/*` deep) where `<lib>`'s rank is `>=` the importing file's lib rank, per the table above.

**Reason string:** `FE-4: lib DAG violation — composites → layout → ui-kit only (no back-edge/cycle).`

**Phase-0 expectation:** **0 violations** (`@mesell/layout` is empty; ui-kit imports no sibling UI lib).

---

### F9 — `fe5_public_barrels_only.mjs` (CREATE) · Contract FE-5

**Rule:** MFEs/apps import `@mesell/*` **public barrels only** — no deep `@mesell/*/<subpath>` imports, and no cross-MFE imports (`apps/mfe-a` importing from `apps/mfe-b`).

**Scan set:** `.ts` files under `frontend/apps/**`. (May exclude `*.spec.ts` — recommended EXCLUDE specs here, since test files sometimes deep-import a private subject; document the choice.)

**Match (flag) — two sub-rules:**
1. **Deep barrel bypass:** `import … from '@mesell/<lib>/<subpath>'` (any specifier with a slash after the lib name, e.g. `@mesell/ui-kit/input/input.component`).
2. **Cross-MFE import:** an import whose specifier resolves into a *different* `apps/<unit>/` than the importing file (relative paths that climb into a sibling app, or an absolute path into another `apps/*`).

**Phase-0 allow-list (WARN, do not error — see §3.6):** the existing intentional deep imports (`@mesell/ui-kit/*`, `@mesell/composites/*`, `@mesell/core/models`) from PR #38/SP0's lean-bundle pattern WILL match sub-rule 1. In Phase 0 these are **warn-only** and that is fine. Provide a **seed allow-list constant** (§3.6) of currently-accepted deep-import prefixes so Phase 5 can flip FE-5 to strict by either (a) emptying the allow-list after a barrel-refactor, or (b) ratifying the lean-bundle deep imports as permanent. Do NOT delete or rewrite any import in Phase 0.

**Reason string:** `FE-5: import @mesell/* public barrels only — no deep subpaths, no cross-MFE imports.`

**Phase-0 expectation:** several WARN lines (the known deep imports). Builder records the exact count so Phase 5 has a baseline.

---

### F3 — `frontend/tools/contracts/run-all.mjs` (CREATE — the runner)

**Purpose:** orchestrate the 5 scanners, print a per-contract report, and own the exit code.

**Required behavior:**
- Import `scan` from each of F5–F9 (or import their default exports), run all 5, collect violations.
- Print a **report block** per contract: contract id + name, violation count, and the `path:line: snippet — reason` lines (cap to a sane number if huge, but Phase-0 counts are small). End with a summary table: `FE-1 … FE-5 → N warnings each` + total.
- **Exit code (Phase 0 = warn-only):**
  - Default (no `--strict`): **always `process.exit(0)`** even with violations. Print a banner: `WARN-ONLY MODE (Phase 0): violations reported, pipeline not failed.`
  - `--strict` flag: `process.exit(1)` if ANY violation exists (this path is NOT used by CI in Phase 0 — it's the Phase-1/4/5 on-ramp).
  - `--strict=fe2,fe3` (comma-list, optional nicety): exit 1 only if a listed contract has violations — supports the parent plan's **per-contract** flip (Phase 1 flips FE-2, Phase 4 flips FE-3, Phase 5 flips FE-1/FE-4/FE-5). If implementing the comma-list is non-trivial, a plain boolean `--strict` is acceptable for Phase 0; note the per-contract need in README for the later phase.
- Must run start-to-finish on a clean tree in **well under 10 s** (it's a line walk over a few hundred files).

**Acceptance:** `node tools/contracts/run-all.mjs` (from `frontend/`) prints the report and **exits 0**; `node tools/contracts/run-all.mjs --strict` exits 1 (because FE-2/FE-5 have known warnings) — proving the strict on-ramp works without being wired to CI.

---

### F10 — `frontend/tools/contracts/README.md` (CREATE)

**Purpose:** document the 5 contracts, their allow-lists, the warn→strict roadmap (which phase flips which contract), and how to run. Short (≈1 screen). Mirrors how the backend lint dir is self-documenting.
**Must state:** Phase 0 = all warn-only, CI non-blocking; Phase 1 flips FE-2 (after icon migration); Phase 4 flips FE-3; Phase 5 flips FE-1/FE-4/FE-5 and makes the CI job a required check. Must note the FE-2 ui-kit allow-prefix is intentionally broad in Phase 0 and narrows to the single registry file in Phase 1. Must note the FE-5 seed allow-list (§3.6) is the lean-bundle deep-import set awaiting a Phase-5 ratify/refactor decision.

---

### 3.6 — Seed allow-list constants (record in the scanner + README)

To make Phase 5 a config flip rather than a rewrite, the builder hard-codes these as named constants (commented as "Phase-0 baseline, revisit at the flip phase"):

- **FE-2 ui-kit allow-prefix (Phase 0):** `libs/ui-kit/` (whole tree). **Phase 1 narrows to:** `libs/ui-kit/icon/icon.registry.ts`.
- **FE-5 accepted deep-import prefixes (Phase 0 lean-bundle pattern):** `@mesell/ui-kit/`, `@mesell/composites/`, `@mesell/core/models`. These warn in Phase 0; Phase 5 either keeps (ratify) or removes (after a barrel refactor).

---

### F11 — `.github/workflows/ci.yml` new job (EDIT — additive only)

**Purpose:** add a **non-blocking, report-only** CI job named exactly **`FE Gate: lint (5 contracts)`** that runs the harness. **Non-blocking** = NOT added to any `needs:` of `build`/`deploy`, NOT a required status check, and (because `run-all.mjs` exits 0 in Phase 0) it cannot fail the pipeline.

**Required job shape (match existing workflow conventions — see the `frontend-build` / `frontend-boot-smoke` jobs for the canonical pnpm setup):**
- `name: "FE Gate: lint (5 contracts)"`.
- `runs-on: ubuntu-latest`, `if: github.event_name != 'schedule'`, `timeout-minutes: 5`.
- **No `needs:`** on build/deploy; do NOT add this job to `build.needs` (line ~892) or `deploy.needs`. It runs independently like `frontend-boot-smoke`.
- Steps:
  1. `actions/checkout@v4`.
  2. `actions/setup-node@v4` with `node-version: "22"` (match existing frontend jobs).
  3. **No `pnpm install` needed** — the scanners are dependency-free Node ESM using only Node built-ins. Skip pnpm setup entirely (faster, and avoids the `pnpm rebuild` native-binary dance). If the builder prefers symmetry with other jobs, a pnpm setup is *allowed* but is dead weight — **recommendation: Node-only, no install.**
  4. Run step: `name: "Run FE contract scanners (warn-only)"`, `working-directory: frontend`, `run: node tools/contracts/run-all.mjs`.
- **Add a header comment** above the job (matching the workflow's heavily-commented style) explaining: Phase 0 = warn-only/report-only; the job mirrors backend Gate 3 (§16.E) but for the frontend; it will become blocking + a required status check at Phase 5 (founder wires the required-check in branch protection, exactly as noted for `frontend-boot-smoke`).
- **Trigger scope:** the workflow already fires on push/PR to `develop`/`main`. This job inherits that. Optionally gate it on the `frontend-changes` paths-filter (`needs: frontend-changes` + an `if:` on `outputs.libs || outputs.shell || any mfe`) to avoid running on backend-only PRs — **recommended** for cleanliness, matching `frontend-boot-smoke`'s pattern. If added, `needs: frontend-changes` is the ONLY `needs:` and does not couple it to build/deploy.

**Acceptance:** the job appears in the Actions run, executes `node tools/contracts/run-all.mjs`, prints the warn report, and **reports success (green)** because the runner exits 0; it is NOT in `build`/`deploy` `needs`; it is NOT a required status check (founder confirms branch-protection is untouched).

---

## 4. Which specialist builds this

**Primary builder: `meesell-angular-service-builder`** — this phase is lib-skeleton + tooling + tsconfig wiring (services/tooling territory, no UI/styling). No `meesell-angular-component-builder` work (no components) and no `meesell-angular-ui-styler` work (no styling) in Phase 0.

**Coordination: `meesell-infra-builder`** for F11 (the `ci.yml` job). The lead (me) authors the exact job YAML in this spec; the service-builder applies it; **infra-builder reviews the CI delta** to confirm: (a) the job is genuinely non-blocking (not in `build`/`deploy` `needs`, not a required check), (b) it matches the workflow's existing job/style conventions, and (c) it does not perturb the paths-filter fan-out or the backend gates. Per the HYBRID rule this is a coordination touch, not a separate dispatch — infra signs off the CI hunk at merge-gate review.

---

## 5. Verification checklist (the merge-gate evidence the builder must attach)

The specialist's PR body must show:

1. **`@mesell/layout` resolves:** `cd frontend && ./node_modules/.bin/ng build frontend --configuration production` (or `pnpm exec ng build shell`) succeeds; a throwaway `import { MEE_LAYOUT } from '@mesell/layout'` (e.g. in a temporary spec, then removed) type-checks. At minimum `tsc -p tsconfig.json --noEmit` is clean. Build time noted (< 90 s per CLAUDE.md Decision 12 — expected ~3 s, no real delta since no app imports layout yet).
2. **Harness runs green (warn-only):** `node tools/contracts/run-all.mjs` from `frontend/` prints the per-contract report AND **exits 0** (`echo $?` → `0`). Paste the summary table.
3. **Baseline counts match §1:** FE-1 = 0, FE-2 = 3 files, FE-3 = 0, FE-4 = 0, FE-5 = N (record N). Any deviation is explained.
4. **Strict on-ramp proven (not wired):** `node tools/contracts/run-all.mjs --strict; echo $?` → `1` (because FE-2/FE-5 warn). Confirms the Phase-1+ flip mechanism works.
5. **Each scanner runs standalone:** `node tools/contracts/fe2_no_raw_pi_icons.mjs` prints its 3 leaks. (Sanity that they're independently runnable like the backend `check_*.py`.)
6. **Zero new deps:** `git diff frontend/package.json frontend/pnpm-lock.yaml` is empty (or package.json shows ONLY an optional `"contracts"` script if the builder chose to add it — no dependency change).
7. **No existing component/MFE touched:** `git diff --stat` shows only the F1–F11 set — NEW files under `libs/layout/` + `tools/contracts/`, plus exactly 2 edits (`frontend/tsconfig.json` +2 lines, `.github/workflows/ci.yml` +1 job). The 3 `pi pi-` leak files are UNCHANGED.
8. **Tests unbroken:** `pnpm test` (or the per-project test target) still passes at the SP0 baseline (40/401-class count — no new spec files expected; the scanners are not Vitest specs). No test count drop.
9. **CI job is non-blocking:** screenshot/log showing the `FE Gate: lint (5 contracts)` job present, green, and NOT listed under `build`/`deploy` `needs` (paste the relevant `needs:` lines proving it's absent), and confirmation that branch-protection required checks were NOT modified.

---

## 6. Out-of-scope (explicit — refuse if asked to do these in Phase 0)

- **No strict enforcement.** CI stays report-only; `run-all.mjs` exits 0. (Phases 1/4/5 flip contracts.)
- **No component code:** no `mee-icon`, no `MEE_ICONS` registry, no aggregator arrays (`MEE_FORM`…`MEE_UI_ALL`), no page/chrome primitives. `MEE_LAYOUT` ships empty.
- **No leak migration:** do NOT rewrite the 3 `pi pi-*` leaks or fold `mee-button`'s `MATERIAL_TO_PI` map — those are Phase 1.
- **No deep-import cleanup:** do NOT rewrite the existing `@mesell/*/<subpath>` lean-bundle imports — FE-5 warns on them; Phase 5 decides.
- **No new npm dependency** and no eslint plugin (the parent plan deliberately chose scanner scripts over eslint for the FE contracts — mirror backend §16.E).
- **No `package.json` script requirement** (optional `"contracts"` script only; default skip).
- **No backend / k8s / LOCKED-doc edits** (`docs/FRONTEND_ARCHITECTURE.md` is LOCKED — any §2 boundary-doc sync is a separate founder-gated change, NOT Phase 0).
- **No `AuthLayout` move, no Sakai adoption, no visual change.**

---

## 7. Risks / decisions for the master session to confirm before the build step

1. **FE-1 false-positive guard is load-bearing.** A naive `grep primeng` flags 7 `federation.config.js` share-config files. The spec scopes FE-1 to `.ts`/`.html` + real import forms only. **Confirm** the builder honors this (else the "already-clean" FE-1 will spuriously warn and erode trust in the gate).
2. **FE-5 will warn loudly in Phase 0** on the intentional lean-bundle deep imports (`@mesell/ui-kit/*` etc.). This is expected and harmless (warn-only), but the founder should know the FE-5 strict flip (Phase 5) requires a **ratify-or-refactor decision** on the lean-bundle pattern — flagged now so it's not a surprise later. No action in Phase 0.
3. **CI job placement:** recommendation is a **Node-only, no-pnpm, `needs: frontend-changes`-gated, non-blocking** job mirroring `frontend-boot-smoke`. Confirm the founder is fine with it firing on frontend-affecting PRs only (vs. every PR). Either is fine; recommendation is paths-gated.
4. **`pnpm-workspace.yaml` is `allowBuilds`-only (no `packages:` glob).** Confirms libs are path-mapped TS (not pnpm workspace packages) — so `@mesell/layout` needs NO pnpm-workspace edit, only the tsconfig alias. No risk; recorded so the builder doesn't add a spurious workspace entry.
5. **Optional `--strict=fe2,fe3` comma-list** vs. a plain boolean `--strict`. The per-contract flip is what Phases 1/4/5 need; a plain boolean is acceptable for Phase 0 with the per-contract need deferred. Confirm whether to build the comma-list now (cheap) or defer.

---

*End of Phase 0 BUILD SPEC. Next HYBRID step: master session dispatches `meesell-angular-service-builder` with this spec; `meesell-frontend-coordinator` then runs the merge-gate review (with `meesell-infra-builder` signing off the `ci.yml` hunk).*

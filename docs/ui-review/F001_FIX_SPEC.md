# SPEC — F-001 Federation Subpath Import-Map Fix

**Author:** `meesell-frontend-coordinator` (HYBRID step 1 of 3) — 2026-06-13
**For:** `meesell-angular-service-builder` (step 2); merge-gate review by coordinator (step 3)
**Finding:** `docs/ui-review/GATE5_FINDINGS.md` F-001 (P0) — shell blank-screen, never bootstraps in browser.
**Verified against live source 2026-06-13.**

## Confirmed reality (read before executing)

- **Shell was RELOCATED to `apps/shell/`** (D43 executed). `app.config.ts` is now `apps/shell/src/app/app.config.ts` (line 9 = the subpath import). There are **7** federation configs: `apps/shell` + 6 remotes.
- `@mesell/*` are **tsconfig-alias-only local libs** — no `node_modules/@mesell`, no per-lib `package.json`, no `exports` map. tsconfig has `@mesell/ui-kit → libs/ui-kit/index.ts` AND a wildcard `@mesell/ui-kit/* → libs/ui-kit/*`. The wildcard lets deep imports compile while failing at runtime.
- Built `dist/frontend/browser/remoteEntry.json`: 161 shared entries; ui-kit appears as **one root key `@mesell/ui-kit` only** — zero subpath keys. Kit emitted as a single shared ESM chunk `_mesell_ui_kit.js` (66.5 kB) — the file named in the F-001 console error.
- **CRITICAL EXPANSION beyond the original diagnosis** — breakage is NOT just `app.config.ts` + `theme.ts`. **11 deep `@mesell/ui-kit/<subpath>` imports across 5 files** all fail identically once their remote loads:
  - `apps/mfe-onboarding/src/app/profile.component.ts:15-19` (card, badge, input, button, + badge.types)
  - `apps/mfe-auth/src/app/login.component.ts:11-12` (input, button)
  - `apps/mfe-auth/src/app/signup.component.ts:11-12` (input, button)
  - `apps/mfe-auth/src/app/otp-verify.component.ts:13-14` (otp-input, button)
  - `apps/shell/src/app/app.config.ts:9` (providers)
  - plus `libs/ui-kit/theme.ts:6` → `@primeuix/themes/aura` (real node_modules pkg, subpath, **inside** the shared kit chunk).
- The barrel `libs/ui-kit/index.ts` **already exports everything needed** (`provideMeeUi`, `MeeCardComponent`, `MeeBadgeComponent`, `MeeInputComponent`, `MeeButtonComponent`, `MeeOtpInputComponent`, type `MeeBadgeSeverity`). Rewrite needs **zero new exports**.
- **The "barrel = 1 MB initial-bundle breach" gotcha in prior memory is MOOT under federation.** That applied to a non-federated single app. Here `@mesell/ui-kit` is a separate shared chunk; barrel and deep imports resolve to the *same* chunk. Keep a post-fix budget check as a guard.

## 1. Chosen approach — (a) barrel-only for `@mesell/ui-kit` + (c) unshare `@primeuix/themes`

**Rationale:** Native Federation registers one import-map key per shared package *root*; `shareAll` never enumerates subpaths, and alias-only libs have no `package.json#exports` to advertise secondary entry points. Only subpath keys literally in the import map resolve at runtime — there are none. So **(a)** route every `@mesell/ui-kit/*` import through the barrel root key (which IS in the map). `@primeuix/themes/aura` is imported from *inside* the shared kit chunk, so the barrel rewrite can't reach it; **(c)** unshare `@primeuix/themes` so Aura bundles directly into each consumer's chunk — no import-map lookup. Consistent with MASTER_PLAN §6.2 (theme is shell-scoped config, not a cross-remote runtime singleton).

**Why not (b) explicit subpath sharedMappings:** brittle, must be re-added in 7 configs per new subpath import, same bug class silently returns. (a)+(c) removes the failure mode structurally.

## 2. Exact file-by-file change list

**A. Rewrite all `@mesell/ui-kit/<subpath>` imports → barrel root `@mesell/ui-kit`**

1. `apps/shell/src/app/app.config.ts` L9: `from '@mesell/ui-kit/providers'` → `from '@mesell/ui-kit'`. Update the L7-8 comment (currently says "Deep import (not the barrel)…", now the opposite).
2. `apps/mfe-onboarding/src/app/profile.component.ts` L15-18 → one `import { MeeCardComponent, MeeBadgeComponent, MeeInputComponent, MeeButtonComponent } from '@mesell/ui-kit';` and L19 `import type { MeeBadgeSeverity } from '@mesell/ui-kit';`
3. `apps/mfe-auth/src/app/login.component.ts` L11-12 → `import { MeeInputComponent, MeeButtonComponent } from '@mesell/ui-kit';`
4. `apps/mfe-auth/src/app/signup.component.ts` L11-12 → same as login.
5. `apps/mfe-auth/src/app/otp-verify.component.ts` L13-14 → `import { MeeOtpInputComponent, MeeButtonComponent } from '@mesell/ui-kit';`

After editing, **re-grep to prove zero remain**: `grep -rn "@mesell/ui-kit/" apps libs --include='*.ts' | grep -v node_modules` → empty. Same for `@mesell/core/` and `@mesell/composites/` (currently zero — keep zero).

**B. Unshare `@primeuix/themes` in all 7 federation configs.** Do NOT touch `theme.ts` — its `@primeuix/themes/aura` import must stay so Aura bundles in. Config-side only: add `'@primeuix/themes'` (and as a guard `'@primeuix/themes/aura'`) to each existing `skip: [...]` array, with an inline F-001 comment. Apply to: `apps/shell` + `apps/mfe-{pricing,export,onboarding,dashboard,catalog,auth}/federation.config.js`.

**Verify the mechanism against installed `@angular-architects/native-federation@21.2.x`**: confirm `skip` removes an already-`shareAll`-included package from the import map by inspecting the rebuilt `remoteEntry.json` shared array (NOT by assumption). If `skip` doesn't drop it, fall back to explicit `shared` override (`'@primeuix/themes': false` or filtered `shareAll`). Success: rebuilt `remoteEntry.json` shared list no longer contains `@primeuix/themes`, and `_mesell_ui_kit.js` self-contains the Aura preset.

**C. Do NOT change:** `libs/ui-kit/index.ts` (already complete), `libs/ui-kit/theme.ts`, `libs/ui-kit/providers.ts`, manifest, routes, load-remote helpers.

## 3. Regression guard — browser-boot smoke (MANDATORY)

Build-green already passed while the shell was dead, so `ng build` is **not** sufficient. The failing path is an es-module-shims **browser** runtime resolution — a Node `import()` will not reproduce it. Machine constraints: **no `ms-playwright` cache, no system chromium/chrome, founder is Safari-only.**

Required: build shell + at least mfe-auth, mfe-onboarding, mfe-pricing; serve them; confirm each `remoteEntry.json` is 200; then a real-engine boot check:
- **Preferred:** install chromium into a temp cache (`npx playwright install chromium`), headless-navigate to `/`, `/login`, `/profile`, wait network-idle, assert (a) `document.body.innerText.trim().length > 0` and (b) zero console messages matching `Unable to resolve specifier`. Screenshot to `docs/ui-review/f001-boot-*.png` at 360px + 1280px.
- **Fallback if chromium download blocked:** document the limitation in the PR, run the Node-side dry check, and request a founder manual Safari boot of `/`, `/login`, `/profile` — a green Safari screenshot is acceptable given Safari-only constraint. PR must state which path was used.

Smoke MUST cover `/login` (mfe-auth) and `/profile` (mfe-onboarding) — the deep-import remotes — not just `/` (landing has no ui-kit deep imports, would pass even with an incomplete fix). **Green build + red/skipped boot = REJECT at the gate.**

## 4. Branch + PR plan

- **Branch:** `fix/frontend/f001-federation-subpath` off `develop`.
- **Commit:** `fix(frontend): resolve F-001 federation subpath import-map failures (shell blank-screen)` with footer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **PR base:** `develop` (hotfix blocking all 6 remotes; default direct-to-develop, confirm at review if a `feature/{name}` wrapper is wanted).
- **PR description must state:** (1) root cause; (2) the fix — 11 deep imports across 5 files rewritten to barrel + `@primeuix/themes` unshared in 7 configs; (3) evidence — build time, shell initial bundle < 1 MB, grep-proof zero subpath imports remain, rebuilt `remoteEntry.json` proving `@primeuix/themes` gone, and the **browser-boot smoke** result with 360px/1280px screenshots on `/`, `/login`, `/profile`; (4) confirmation the old 1 MB budget gotcha does not recur.
- **Merge gate:** lead reviews via HYBRID step 3; builder sets board row IN REVIEW on PR open, lead flips MERGED on merge.

## 5. Conflict-surface note

Touched: `apps/shell/src/app/app.config.ts`, 7 `federation.config.js`, 4 remote component files. **No `libs/` edits.** Active branches at dispatch are backend microservices (MS-A/C/D/E image-service, xlsx-export, image-precheck) — **none touch `apps/**` or `federation.config.js`, frontend conflict risk low.** Before branching, builder must `git fetch`, check `origin/develop` tip, re-grep the touch-set for any in-flight `fix/frontend/*` or `feature/{name}/frontend` editing these files; if found, STOP and escalate to lead.

## Merge-gate review checklist (HYBRID step 3)
- Reject if "fixed" via subpath sharedMappings (approach b) — reintroduces the latent bug class.
- Verify `theme.ts` was NOT edited (Aura import must remain to bundle in).
- Verify boot smoke ran in a real browser engine (or founder-Safari fallback documented), not just Node.
- Verify grep proof: zero `@mesell/ui-kit/` subpath imports remain.
- Verify rebuilt `remoteEntry.json` no longer shares `@primeuix/themes`.

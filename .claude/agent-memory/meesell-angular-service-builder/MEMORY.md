# Memory — meesell-angular-service-builder

## Agent Identity
Angular 18 service specialist for MeeSell. Owns services + RxJS state + HttpClient + JWT interceptor + auth guards + typed ApiClientService + typed models. Decentralized memory ecosystem.

## Session: F-001 federation subpath fix (2026-06-13)

**Branch/commit:** fix/frontend/f001-federation-subpath @ 3ae9fd3
**PR:** #203 (→ develop, IN REVIEW at merge-gate)

### Root cause (F-001)
- Native Federation registers ONE import-map key per shared package ROOT. Subpath imports
  (e.g. @mesell/ui-kit/providers, @mesell/ui-kit/input/input.component) compile fine via
  tsconfig wildcard alias but fail at runtime in the browser — es-module-shims cannot resolve
  them because no subpath key exists in the import map.
- @primeuix/themes/aura is imported INSIDE libs/ui-kit/theme.ts (inside the shared chunk).
  @primeuix/themes root is in the import map but /aura is not → second crash on chunk load.

### Fix (a)+(c) per SPEC
- (a) Rewrote all @mesell/ui-kit/<subpath> imports → barrel root @mesell/ui-kit. 4 files touched.
  libs/ui-kit/index.ts was already complete — zero new exports added.
- (c) Added @primeuix/themes + @primeuix/themes/aura to skip[] in all 7 federation configs.
  libs/ui-kit/theme.ts NOT touched — Aura import stays, bundles into _mesell_ui_kit.js (204 kB).

### Evidence
- Grep proof: 3 greps all return empty
- remoteEntry.json proof: 161 shared entries, 0 @primeuix entries in shell + mfe-auth + mfe-onboarding
- Boot smoke: 6/6 PASS (headless chromium 148.0.7778.96), zero resolveErrors

### Key learnings

**BARREL-ONLY import rule (P0 for federation):**
  RIGHT: import { MeeCardComponent } from '@mesell/ui-kit';
  WRONG: import { MeeCardComponent } from '@mesell/ui-kit/card/card.component';
  Subpaths compile via tsconfig wildcard but fail at runtime in the browser (no import-map key).

**build-green != boot-green for federation:**
  esbuild resolves tsconfig aliases at compile time. Runtime failure is browser-only (es-module-shims).
  Always run a headless browser smoke after federation changes.

**playwright on macOS arm64:**
  PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers npx playwright install chromium
  Executable: /tmp/pw-browsers/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell
  Install playwright package in /tmp/smoke-runner (NOT in frontend/ — not a frontend dep)

**pnpm-workspace.yaml allowBuilds fix (PR #203):**
  Placeholder values were in develop until PR #203. Now all 5 entries = true.
  DO NOT overwrite this file on branch checkout — already correct.

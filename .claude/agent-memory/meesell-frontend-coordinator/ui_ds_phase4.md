# UI Design-System Decoupling — Phase 4 (chrome primitives + shell refactor)

**Status:** BUILT + PR OPEN. 2026-06-17.
**PR:** #267 `feat/ui-ds-phase4 → feat/ui-ds-phase3` (STACKED — base auto-retargets to develop when #265 merges). Commit `e114aa5`. Stacked worktree `/tmp/mesell-wt/ui-ds-phase4` cut off the Phase-3 tip (NOT develop) to avoid a `libs/layout/index.ts` barrel conflict.

## What shipped
Four shell-only chrome primitives in `@mesell/layout/chrome/` + thin-host shell refactor:
- `mee-app-bar` (sticky 60px header, hamburger `menuToggle`, trailing actions slot; `:host{display:contents}` keeps `<header>` a direct flex child so sticky is unchanged).
- `mee-side-nav` (`<nav>` landmark + brand + nav groups; reused desktop + inside mobile drawer; `navigated` re-emit).
- `mee-nav-item` (routerLink + icon + label; active exact/prefix; accent CTA; `navigated` output).
- `mee-user-menu` (avatar + dropdown; owns its toggle viewChild).
- `chrome.types.ts`: `MeeNavItem`/`MeeNavGroup` contract.
Shell = thin host: KEEPS nav DATA + AuthService + onboardingComplete + userMenuItems + userInitials + drawer signal + `<router-outlet>`; ADDS `visibleNavGroups` computed (filter visible → drop empty → map prefixMatch→exact); css keeps only composition/positioning + `::ng-deep` drawer overrides.

## Contract design (resolves plan §7)
- Chrome exported from the **@mesell/layout barrel ROOT** (shell import stays FE-5 barrel-clean). MFE misuse sealed by **FE-3 symbol-name matcher** (forward-compat seeded — no scanner edit). **NO MEE_CHROME aggregator** (an aggregator symbol bypasses the symbol seal). → §7 resolved in favor of lint-only seal, not a `/chrome` sub-entry (which would trip FE-5 from the shell).
- **FE-3 flipped strict**: ci.yml `--strict=fe2` → `--strict=fe2,fe3`. Job stays non-required + out of build/deploy needs (required-check = Phase 5).

## Parity (the bar) — what worked
- `shell.component.spec.ts` parity oracle passed **UNMODIFIED** (strongest signal). Class names lifted verbatim (`nav-item`, `nav-group__label`, `sidebar-desktop`, `avatar`...).
- **ui-styler caught a real a11y regression**: extraction dropped the original `<nav aria-label="Main navigation">` landmark → ui-styler re-added it inside mee-side-nav (+ spec). WCAG 2.4.1 parity restored.
- **Specificity guard (mine, key learning):** mee-side-nav `:host{display:flex}` injects AFTER the shell stylesheet, so the mobile-hide had to be scoped `.shell-layout .sidebar-desktop` (0,2,0) to beat `:host` (0,1,0). Plain `.sidebar-desktop{display:none}` would have LOST → desktop sidebar visible on mobile. ui-styler confirmed 0,2,0 wins.
- `.nav-item i` (16/20px) is a no-op in BOTH phases (cross-encapsulation: rule scoped to shell/nav-item, `<i>` lives in mee-icon) — icon inherits 14px from `.nav-item`. Parity = leave as-is.

## Build/infra learnings (IMPORTANT for later phases)
- **API 529 overload**: subagent dispatch failed 3× (component-builder hit 529 before writing ANY files each time, ~5-10min wasted each). FALLBACK USED: coordinator built Phase 4 DIRECTLY (handoff sanctions "execute directly" when agents unavailable), then dispatched ui-styler for parity once API recovered. Lesson: under sustained overload, build directly + use one specialist pass for review rather than burning retries.
- **Fresh worktree has NO node_modules** (not shared across git worktrees). FIX: `ln -s /tmp/mesell-wt/ui-ds-phase3/frontend/node_modules <phase4>/frontend/node_modules` — instant, safe for ng build/test (node_modules is gitignored so never committed). Avoids a slow pnpm install on the 8GB machine. Do this for every new phase worktree.
- **`npx tsc` resolves to a typo-squat** ("not the tsc command"); no local tsc binary in pnpm layout. Rely on `ng build`/`ng test` for type-checking instead.
- Test NG0205 "Injector destroyed" unhandled rejection when a spec clicks a real `routerLink` against `provideRouter([])` → navigation finds no route, errors after teardown. FIX: `provideRouter([{ path: '**', children: [] }])` (wildcard) so navigation resolves cleanly.

## Evidence
5 contracts CLEAN (strict fe2,fe3 exit 0); ng test 1183 pass (parity oracle GREEN unmodified + 4 chrome specs); ng build green, bundle delta +0.10kB; greps clean. Pre-existing `app.spec.ts` NG0201 MessageService still the only failure (every UI-DS PR until fixed).

## Roadmap (remaining)
- **Phase 5** (next): finalize FE-1/FE-4/FE-5 scanners; flip FE Gate to **blocking required check** on develop. (FE-2+FE-3 already strict.)
- **Phase 6**: per-MFE adoption sweep (MEE_LAYOUT page primitives + aggregators + mee-icon).
- **Phase 7**: swap-proof (2nd theme + icon-set, one-file each).
- **Carry**: `mee-page` `asMain` landmark input (Phase-3 carry) — still NOT needed (shell keeps `<main>`); only if shell cedes the landmark.
- Discipline: one phase = one fresh worktree off develop (or stacked on the prior unmerged phase) = one branch = one PR; founder merges; NEVER git in the master tree.

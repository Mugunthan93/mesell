# Federation `shared` Singleton Trim — Proposal (NOT applied)

**Status:** PROPOSAL — analysis only. No `federation.config.js` is modified by this document.
**Author:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-14
**Scope:** `frontend/apps/{shell,mfe-*}/federation.config.js` (Native Federation `shared`/`skip`)
**Decision class:** modest **startup optimization**, not a correctness fix. See §7.

---

## 0. TL;DR

| | Count |
|---|---|
| Shared singletons today (per remoteEntry.json, verified on mfe-onboarding) | **161** |
| **KEEP** (must stay singleton) | **15** real packages (9 @angular/* + 3 @mesell/* + rxjs + tslib + rxjs/operators) + 13 `@nf-internal/*` chunks that are **not skippable** |
| **UN-SHARE candidates** (safe to bundle per-remote) | **133** `primeng/*` sub-entries |
| **UNSURE / needs-test** | 0 hard blockers; `primeng/api`, `primeng/base`, `primeng/config`, `primeng/dom` flagged as *watch-items* inside the candidate set (§3.3) |
| Shared count **after** the proposed change | **~28** (161 − 133) |

**Recommended change:** keep `shareAll(...)` and **expand the `skip:` array** with the 133 `primeng/*` sub-entries (Option A — matches the existing F-001 precedent). Do **not** un-share any `@angular/*`, `@mesell/*`, `rxjs`, or `tslib`.

**Why primeng is safe to un-share:** all `mee-*` wrappers live in `@mesell/ui-kit`, which **stays shared+singleton**. PrimeNG is a leaf, presentational dependency *of* ui-kit; it holds no cross-boundary application state. The PrimeNG `MessageService`/`ConfirmationService` singletons are provided at the **shell** via `provideMeeUi()` and injected through Angular DI — that DI singleton is unaffected by whether the *module code* of `primeng/*` is import-map-shared or bundled per remote (§3.2).

---

## 1. Verified current state (live this session)

All 7 configs (`apps/shell` + `apps/mfe-{auth,onboarding,dashboard,catalog,pricing,export}`) use an **identical** share block:

```js
shared: {
  ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
},
skip: [
  'rxjs/ajax', 'rxjs/fetch', 'rxjs/testing', 'rxjs/webSocket',
  '@primeuix/themes',       // F-001
  '@primeuix/themes/aura',  // F-001 guard
],
features: { ignoreUnusedDeps: true },
```

Live remoteEntry.json shared counts (dev servers on :4200–:4206):

| Remote | total shared | primeng/* | @nf-internal/* |
|---|---|---|---|
| shell | 161 | 133 | 13 |
| mfe-auth | 161 | 133 | 13 |
| mfe-onboarding | 161 | 133 | 13 |
| mfe-dashboard | 164 | 133 | 15 |
| mfe-catalog | 164 | 133 | 15 |

remoteEntry.json size (mfe-onboarding): **38,939 bytes (~39 KB)**.

**Key empirical finding:** the `primeng/*` count is **133 on EVERY remote** — identical for `mfe-auth`/`mfe-dashboard` (which use a handful of components) and `mfe-catalog` (which uses many). `shareAll` shares PrimeNG's **entire installed sub-entry surface** regardless of per-remote usage. That uniform 133 is the bloat this proposal targets.

**Two things the prompt assumed that are NOT in the live data:**
- There are **no** `@primeuix/styles/*` or `@primeuix/*` util packages in `shared[]` — `@primeuix/themes` + `/aura` are already `skip`-ped (F-001), and nothing else from `@primeuix` appears. So the "`@primeuix` candidates" hypothesised in the brief do not exist to un-share.
- `shared[]` contains **13 `@nf-internal/*` chunk entries** (Native-Federation-generated browser/chunk shims). These are **not npm packages** and **cannot be removed via `skip:`** — `skip` matches package names, and the NF runtime emits these itself. They stay.

---

## 2. Full enumeration of the 161 (mfe-onboarding, representative)

### KEEP — framework runtime + shared cross-boundary state (15 real packages)

| Package | Reason |
|---|---|
| `@angular/common` | framework runtime — must be one instance |
| `@angular/common/http` | framework runtime (HttpClient/interceptor chain) |
| `@angular/core` | framework runtime — DI/zone/signals root |
| `@angular/core/primitives/di` | @angular/core internal — travels with core |
| `@angular/core/primitives/signals` | @angular/core internal — signals cross the boundary (D22 C3) |
| `@angular/forms` | framework runtime (Reactive Forms) |
| `@angular/platform-browser` | framework runtime (bootstrap/DOM) |
| `@angular/platform-browser/animations/async` | framework runtime (animations provider) |
| `@angular/router` | framework runtime — single Router across host+remotes |
| `@mesell/core` | **shared cross-boundary state — AuthService singleton** (D22 C1/C2; otp-verify WRITES, ProfileComponent READS) |
| `@mesell/ui-kit` | shared component instances (the `mee-*` wrappers + `provideMeeUi`) |
| `@mesell/composites` | shared component instances (PageHeader, AuthLayout, StatusBadge) |
| `rxjs` | framework runtime — one Observable/Subject identity |
| `rxjs/operators` | rxjs subpath — travels with rxjs |
| `tslib` | TS runtime helpers — one instance |

### KEEP (not removable) — Native Federation internals (13)
`@nf-internal/browser-*` + `@nf-internal/chunk-*` — NF-emitted shims, **not npm packages**, not addressable by `skip`. Count varies 13–15 per remote.

### UN-SHARE CANDIDATES — `primeng/*` (133)
Breakdown: **52** component/util entries · **25** `primeng/types/*` (type-only) · **56** `primeng/icons/*` (leaf icon components). Full list in §4 (the literal skip additions).

---

## 3. Categorization rationale

### 3.1 Why `@angular/*`, `@mesell/*`, rxjs, tslib MUST stay shared
- **`@angular/core`/`router`/`forms`/`common`** — two copies = two DI roots, two Router instances, `NG0203`/`inject()` context errors, duplicate zone. Non-negotiable.
- **`@mesell/core`** — the AuthService singleton. otp-verify (mfe-auth) WRITES `setSession`; ProfileComponent (mfe-onboarding) READS `currentUser()`. Two copies = two AuthServices = login does not persist across the boundary. This is the migration's auth GO/NO-GO (D22 C5/C4).
- **`@mesell/ui-kit` / `@mesell/composites`** — shared component *instances*; also `ui-kit` is where the PrimeNG `provideMeeUi()` providers are registered. Keeping ui-kit shared is what lets PrimeNG be un-shared safely (§3.2).
- **`rxjs` / `rxjs/operators` / `tslib`** — identity-sensitive runtime; `instanceof Observable` and operator chains break across duplicate copies.

### 3.2 Why `primeng/*` is SAFE to un-share (the core argument)
1. **No cross-boundary application state.** PrimeNG components are presentational. There is no PrimeNG global that a remote mutates and another remote reads.
2. **The DI singletons survive.** `MessageService` and `ConfirmationService` are provided **once at the shell** via `@mesell/ui-kit`'s `provideMeeUi()`. They are Angular-DI singletons resolved through the (still-shared) `@angular/core` injector + the (still-shared) `@mesell/ui-kit`. Un-sharing the `primeng/*` **module code** does not create a second `MessageService` provider — providers come from ui-kit, not from import-map identity of `primeng/api`.
3. **The boundary rule already isolates PrimeNG.** Per FRONTEND_ARCHITECTURE.md §2, PrimeNG is imported **only** inside `@mesell/ui-kit`. Remotes consume `mee-*` wrappers, not raw `primeng/*`. So `primeng/*` is a transitive dep of the shared ui-kit chunk — un-sharing it bundles PrimeNG into the ui-kit-consuming chunks per remote rather than negotiating 133 import-map keys at startup.
4. **Cost of un-sharing = minor byte duplication.** If >1 remote loads ui-kit (all do), each carries its own copy of the PrimeNG code it actually uses. Because `ignoreUnusedDeps` + esbuild tree-shaking already prune unused PrimeNG per remote, the duplicated bytes are bounded by *actually-used* components, not the full 133.
5. **Precedent.** `@primeuix/themes` (+`/aura`) is **already** un-shared via `skip` (F-001) for an import-map subpath miss. Un-sharing `primeng/*` extends the same established, safe-when-justified pattern.

### 3.3 Watch-items inside the candidate set (still recommended to un-share, but verify in the test pass)
- `primeng/config`, `primeng/api` — host the PrimeNG `PrimeNG`/`Config` provider + `MessageService`/`ConfirmationService` **classes**. The *providers* are registered at the shell via ui-kit, so DI identity is shell-owned regardless. Listed as watch-items only because they carry the service classes; the validation in §6 (toast/confirm dialog fire from a remote) directly exercises them.
- `primeng/base`, `primeng/basecomponent`, `primeng/usestyle`, `primeng/dom` — PrimeNG's internal style-injection base. Per-remote duplication injects the same `<style>` twice (idempotent by PrimeNG's keyed `useStyle`). Confirm no double-styling / FOUC in the §6 visual check.

### 3.4 UNSURE / needs-test (do NOT un-share without proof)
None outside the watch-items above. `@angular/*`, `@mesell/*`, rxjs, tslib are firmly KEEP; `@nf-internal/*` are not addressable. The 133 `primeng/*` are candidates with the four watch-items called out for explicit observation.

---

## 4. Recommended config change (Option A — proposal, not applied)

**Option A (RECOMMENDED): keep `shareAll`, expand `skip`.** Lowest risk, matches the F-001 precedent, single-line-per-entry diff, trivially revertible. Native Federation `skip` matches **exact package keys** (proven by the configs skipping `@primeuix/themes` AND `@primeuix/themes/aura` as two separate entries) — so each `primeng/*` sub-entry must be listed explicitly; a bare `'primeng'` would NOT cover the 133 sub-entries (there is no root `primeng` key in `shared[]`).

**Option B (NOT recommended): replace `shareAll` with an explicit `shared` map of only the 15 keep packages.** Rejected because: (a) it diverges from the F-001/skip idiom every config already uses; (b) it loses `shareAll`'s auto-discovery of future @angular/@mesell subpaths (e.g. a new `@angular/core/primitives/*`), turning every Angular minor bump into a manual map edit; (c) larger, riskier diff across 7 files.

### Proposed `skip:` block (append the 133 lines below to the EXISTING skip array in ALL 7 configs)

```js
  skip: [
    // --- existing (unchanged) ---
    'rxjs/ajax',
    'rxjs/fetch',
    'rxjs/testing',
    'rxjs/webSocket',
    '@primeuix/themes',       // F-001
    '@primeuix/themes/aura',  // F-001 guard

    // --- PROPOSED ADDITIONS (F-TRIM): un-share all primeng/* sub-entries. ---
    // PrimeNG is a leaf presentational dep of @mesell/ui-kit (which STAYS shared).
    // No cross-boundary state; MessageService/ConfirmationService DI singletons are
    // provided at the shell via provideMeeUi() and are unaffected. See proposal §3.2.
    // primeng component + util entries (52)
    'primeng/api',
    'primeng/autofocus',
    'primeng/badge',
    'primeng/base',
    'primeng/basecomponent',
    'primeng/baseeditableholder',
    'primeng/baseinput',
    'primeng/basemodelholder',
    'primeng/bind',
    'primeng/button',
    'primeng/card',
    'primeng/checkbox',
    'primeng/chip',
    'primeng/config',
    'primeng/confirmdialog',
    'primeng/datepicker',
    'primeng/dialog',
    'primeng/dom',
    'primeng/drawer',
    'primeng/fileupload',
    'primeng/fluid',
    'primeng/focustrap',
    'primeng/iconfield',
    'primeng/inputicon',
    'primeng/inputnumber',
    'primeng/inputotp',
    'primeng/inputtext',
    'primeng/menu',
    'primeng/message',
    'primeng/motion',
    'primeng/overlay',
    'primeng/paginator',
    'primeng/password',
    'primeng/progressbar',
    'primeng/progressspinner',
    'primeng/radiobutton',
    'primeng/ripple',
    'primeng/scroller',
    'primeng/select',
    'primeng/selectbutton',
    'primeng/skeleton',
    'primeng/steps',
    'primeng/table',
    'primeng/tag',
    'primeng/textarea',
    'primeng/toast',
    'primeng/togglebutton',
    'primeng/tooltip',
    'primeng/tree',
    'primeng/treeselect',
    'primeng/usestyle',
    'primeng/utils',
    // primeng/types — type-only, never in runtime graph (25)
    'primeng/types/button',
    'primeng/types/card',
    'primeng/types/checkbox',
    'primeng/types/chip',
    'primeng/types/confirmdialog',
    'primeng/types/datepicker',
    'primeng/types/dialog',
    'primeng/types/drawer',
    'primeng/types/fileupload',
    'primeng/types/fluid',
    'primeng/types/inputnumber',
    'primeng/types/menu',
    'primeng/types/paginator',
    'primeng/types/password',
    'primeng/types/progressbar',
    'primeng/types/radiobutton',
    'primeng/types/scroller',
    'primeng/types/select',
    'primeng/types/selectbutton',
    'primeng/types/table',
    'primeng/types/tag',
    'primeng/types/toast',
    'primeng/types/togglebutton',
    'primeng/types/tree',
    'primeng/types/treeselect',
    // primeng/icons — leaf icon components (56)
    'primeng/icons',
    'primeng/icons/angledoubledown',
    'primeng/icons/angledoubleleft',
    'primeng/icons/angledoubleright',
    'primeng/icons/angledoubleup',
    'primeng/icons/angledown',
    'primeng/icons/angleleft',
    'primeng/icons/angleright',
    'primeng/icons/angleup',
    'primeng/icons/arrowdown',
    'primeng/icons/arrowdownleft',
    'primeng/icons/arrowdownright',
    'primeng/icons/arrowleft',
    'primeng/icons/arrowright',
    'primeng/icons/arrowup',
    'primeng/icons/ban',
    'primeng/icons/bars',
    'primeng/icons/baseicon',
    'primeng/icons/blank',
    'primeng/icons/calendar',
    'primeng/icons/caretleft',
    'primeng/icons/caretright',
    'primeng/icons/check',
    'primeng/icons/chevrondown',
    'primeng/icons/chevronleft',
    'primeng/icons/chevronright',
    'primeng/icons/chevronup',
    'primeng/icons/exclamationtriangle',
    'primeng/icons/eye',
    'primeng/icons/eyeslash',
    'primeng/icons/filter',
    'primeng/icons/filterfill',
    'primeng/icons/filterslash',
    'primeng/icons/home',
    'primeng/icons/infocircle',
    'primeng/icons/minus',
    'primeng/icons/pencil',
    'primeng/icons/plus',
    'primeng/icons/refresh',
    'primeng/icons/search',
    'primeng/icons/searchminus',
    'primeng/icons/searchplus',
    'primeng/icons/sortalt',
    'primeng/icons/sortamountdown',
    'primeng/icons/sortamountupalt',
    'primeng/icons/spinner',
    'primeng/icons/star',
    'primeng/icons/starfill',
    'primeng/icons/thlarge',
    'primeng/icons/times',
    'primeng/icons/timescircle',
    'primeng/icons/trash',
    'primeng/icons/undo',
    'primeng/icons/upload',
    'primeng/icons/windowmaximize',
    'primeng/icons/windowminimize',
  ],
```

> The literal 133-line block above is generated verbatim from the live `shared[].packageName` set. Apply identically to all 7 configs (shell + 6 remotes) so the shared contract stays uniform across the boundary.

---

## 5. Estimated benefit (be honest: modest)

| Metric | Before | After (est.) |
|---|---|---|
| `shared[]` entries per remoteEntry.json | 161 | ~28 |
| remoteEntry.json size (mfe-onboarding) | ~39 KB | ~10–12 KB (est., −70%) |
| Singletons negotiated at `initFederation` startup | 161 × 6 remotes | ~28 × 6 remotes |

**Effect:** smaller remoteEntry.json downloads at startup, far fewer import-map keys to negotiate when the eager-fetch builds the shared map. Startup negotiation is O(shared × remotes), so cutting 133 keys per remote is the dominant win.

**Honest caveats:**
- This is a **startup/transfer optimization, NOT a correctness fix.** Nothing is broken today.
- Per-remote PrimeNG bytes **increase** (duplication), bounded by tree-shaken actual usage. For a 6-remote app each loading ui-kit, the net is "smaller startup negotiation + slightly larger per-remote chunk." On a CDN with caching this is a clear win; on a cold first paint it is roughly neutral on bytes but better on negotiation latency.
- The 13 `@nf-internal/*` entries remain — the floor is ~15 real+internal, not 0.

---

## 6. Risk + MANDATORY validation plan (run AFTER applying, in a separate change)

Un-sharing breaks things **only if** a package secretly needs to be a single instance. The four watch-items (§3.3) are the only realistic risk surface. The following gates are **mandatory** before any trimmed config merges:

1. **Route integrity — `pnpm run dev:check-routes` must stay 11/11.** Any drop = a remote failed to mount = hard reject, revert the skip additions.
2. **Auth singleton must hold (the GO/NO-GO).** Manually: log in via `/otp-verify` (mfe-auth WRITES `setSession`), navigate to `/profile` (mfe-onboarding READS `currentUser()`), confirm the **same** session persists and `isAuthenticated()` is true. This proves `@mesell/core` is still the one shared AuthService. (This is unaffected by the primeng trim by construction — @mesell/core stays shared — but it is the canary that the shared map still resolves correctly after editing the skip array.)
3. **PrimeNG DI singletons fire from a remote (watch-item check).** From a remote page, trigger a `MeeToast` and a `MeeConfirm` (the `MessageService`/`ConfirmationService` paths). Confirm exactly one toast/dialog renders — proves no duplicate service provider crept in.
4. **No visual regression / double-style (watch-item check).** Load `/catalogs/new` (heavy PrimeNG) at 360 px and 1280 px; confirm no FOUC, no doubled `<style>`, theme intact.
5. **Test suite stays green** (`pnpm test` == current baseline) and **build < 90 s** (CLAUDE.md Decision 12 stop condition).

If any of 1–4 fails, `git revert` the skip additions — they are isolated, single-array edits with zero coupling to component code.

---

## 7. Recommendation

Adopt **Option A**: keep `shareAll`, append the 133 `primeng/*` entries to the `skip` array in all 7 configs, uniformly. KEEP all `@angular/*`, `@mesell/*`, `rxjs`, `rxjs/operators`, `tslib` shared+singleton. Treat `@nf-internal/*` as immovable. Gate the applied change behind the §6 validation plan. Expect ~161 → ~28 shared entries and a ~70% smaller remoteEntry.json, framed honestly as a startup-negotiation/transfer optimization rather than a correctness fix.

**This document changes no code.** The actual `federation.config.js` edit and the §6 validation are a separate, tested change.

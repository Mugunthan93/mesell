# UI Design-System Phase 6 — `dashboard` MFE B-Pilot Migration SPEC

**Status:** READY TO BUILD (6a is MERGED to `develop` as #273 — `padding="tight"` shipped).
**Author:** `meesell-frontend-coordinator` (HYBRID dispatch SPEC).
**Date:** 2026-06-17
**Parent:** `docs/plans/architecture/UI_DS_PHASE6_SUBPLAN.md` §5 (per-MFE playbook) + §5.2 (B steps + bar) + §5.3 (mapping rules).
**Founder decision:** A (standing convention) + 6a (shipped) + **a single B pilot = `dashboard`** (chosen after inspection showed `pricing` barely adopts).
**Inventory base:** worktree `/tmp/mesell-wt/ui-ds-phase6-dashboard` on branch `feat/ui-ds-phase6-dashboard` @ `283496d` (off `develop`, **HAS 6a**).
**Target MFE:** `frontend/apps/mfe-dashboard/` — multi-expose remote, TWO exposed components: `DashboardComponent` (route `/dashboard`) + `LandingComponent` (route `/`).
**Acceptance bar (B):** pixel-identical at **360 / 768 / 1280px** · lazy-chunk delta **≤ +2 KB gzip** · FE Gate green. ANY visual delta blocks B (or escalates that element to a founder C-decision).

> **Why dashboard is a GOOD pilot (vs pricing's near-no-op):** the dashboard page container is `px-4 py-6 sm:px-6 max-w-7xl mx-auto w-full flex flex-col gap-6` — this maps to `mee-page` **byte-for-byte** now that 6a's `padding="tight"` exists, and it uses a **real flex `gap-6`** (not `space-y`), so there is **no margin-vs-gap hazard** (the exact thing that forced pricing's L1 to leave-raw). Dashboard yields the genuine "clean `mee-page` adoption" exemplar the convention points to.

---

## 0. Locked scope

**IN scope — exactly ONE element changes, in exactly ONE file:**
- `frontend/apps/mfe-dashboard/src/app/dashboard.component.ts` — replace the **inner page-container `<div>`** (template line 64) with `<mee-page maxWidth="xl" padding="tight" gap="lg">`. Add `MeePageComponent` (or `...MEE_LAYOUT`) to `imports`. **Nothing else in this template or its styles changes.**

**OUT of scope (do NOT touch):**
- `landing.component.ts` — see §1.2 (no aggregator swap, no layout-primitive swap; it is a bespoke marketing page with its own media-query CSS — leave entirely as-is).
- All `@mesell/composites` imports in `dashboard.component.ts` (`MeeAlertBanner`, `MeeOfflineBanner`, `PageHeader`, `StatCard`, `StatusBadge`, `EmptyState`, `LoadingSkeleton`) — there is **no composites aggregator**; leave individual.
- All `@mesell/core` service imports (`NetworkService`, `ErrorService`) and the `@mesell/ui-kit` `MeeConfirmService` import — these are **providers/services injected via `inject()`**, NOT components in `imports:[]`; aggregators do not apply (§1.1).
- The entire `styles: [...]` block of `dashboard.component.ts` — `.mee-stat-grid`, `.mee-table*`, `.mee-control`, `.mee-pagination`, `.mee-page-btn`, `.mee-delete-btn`, `.mee-retry-btn` all stay verbatim.
- `dashboard.model.ts`, `services/dashboard-api.service.ts`, both `.spec.ts`, `public-api.ts`, `main.ts`, `index.html` — zero changes.
- Any FE Gate contract / scanner / `ci.yml` — untouched (adoption only moves toward the canonical surface).

---

## 1. Import-swap plan (file-by-file)

### 1.1 `dashboard.component.ts` — aggregator decision: **NO ui-kit aggregator swap. ADD `MeePageComponent` only.**

Real `imports:[]` on the component today:
```
ReactiveFormsModule,            // Angular core — out of scope
StatCardComponent,              // @mesell/composites — no aggregator exists
StatusBadgeComponent,           // @mesell/composites
PageHeaderComponent,            // @mesell/composites
EmptyStateComponent,            // @mesell/composites
LoadingSkeletonComponent,       // @mesell/composites
MeeAlertBannerComponent,        // @mesell/composites
MeeOfflineBannerComponent,      // @mesell/composites
```
Plus, injected (NOT in `imports`): `MeeConfirmService` (`@mesell/ui-kit`), `NetworkService` + `ErrorService` (`@mesell/core`).

| Symbol | Library | In an aggregator? | Verdict |
|---|---|---|---|
| 7× composites components | `@mesell/composites` | **No** — no composites aggregator exists (subplan §5.3; confirmed: only `MEE_*` ui-kit + `MEE_LAYOUT` groups exist) | **keep individual** (rule-clean) |
| `MeeConfirmService` | `@mesell/ui-kit` | **No** — it is a **provider**, supplied at root via `provideMeeUi()`; aggregators are component-class arrays for `imports:[]` ONLY (verified in `libs/ui-kit/aggregators.ts` header: *"SERVICES ARE NOT HERE… Placing a service in a component's imports array is an Angular compile-time error"*) | **keep individual** (cannot be in any group) |
| `NetworkService`, `ErrorService` | `@mesell/core` | n/a (services) | **keep individual** |

**Conclusion:** the dashboard component imports **zero aggregator-eligible `@mesell/ui-kit` components.** Its only ui-kit symbol is the `MeeConfirmService` provider, which is structurally ineligible for an aggregator. **There is NO ui-kit aggregator swap to make on dashboard** — and that is correct, not a miss. (Note: subplan §1 recorded "dashboard 2" ui-kit imports from an earlier grep; the real current source has exactly one ui-kit symbol, the `MeeConfirmService` provider. Don't trust the count — trust this inventory.)

**The ONLY import change:** add the `mee-page` primitive.
```ts
// add this import:
import { MeePageComponent } from '@mesell/layout';
// add to imports: array:
imports: [ ReactiveFormsModule, MeePageComponent, StatCardComponent, /* …existing 7 composites… */ ],
```
Builder MAY use `...MEE_LAYOUT` instead of `MeePageComponent`, BUT **do NOT** — `MEE_LAYOUT` is 6 layout components and dashboard uses only `mee-page`; importing the spread pulls 5 unreferenced layout components into the chunk. They are dependency-light (pure `@angular/core` + token types, **no PrimeNG**), so the gzip cost is tiny, but the single-import is cleaner and risk-free for the bundle bar. **Spec mandates the single `MeePageComponent` import.**

### 1.2 `landing.component.ts` — **NO CHANGE.**

`landing.component.ts` imports `RouterLink` (core) + `MeeButtonComponent` (`@mesell/ui-kit`, in `MEE_COMMON`).
- `MEE_COMMON` is **1/4 used** (`MeeButton` only) → far below the §5.2 half-bar → **keep `MeeButtonComponent` individual.**
- Independent confirmation via the §5.3/H-class bundle rule: adopting `MEE_COMMON` would drag `MeeMenuComponent` (`import { Menu } from 'primeng/menu'` — real PrimeNG) + `MeeCardComponent` + `MeeIconComponent`, none used by landing → breaches the ≤+2 KB gzip bar. Same cautionary precedent as the pricing SPEC's `MEE_COMMON`/`MeeMenu` finding. **Keep individual.**
- Landing's layout is a **bespoke marketing page** (sticky nav, hero, how-it-works, footer) with three hand-tuned media-query blocks (`768px`, `1280px`) and zero `mee-page`-shaped container. It has **no** `px-4 py-6 sm:px-6 max-w-* mx-auto flex flex-col gap-*` page-container pattern to map. **Leave 100% as-is** — forcing a primitive here is exactly the C-style delta the recommendation avoids.

**Net import change for the whole MFE:** **+1 import** (`MeePageComponent` in `dashboard.component.ts`). Everything else stays byte-identical.

---

## 2. Layout-div → primitive mapping (dashboard-specific)

Source template skeleton in `dashboard.component.ts`:
```
<div class="mee-dashboard w-full flex flex-col">                                  ← L0 outer (offline-banner host)
  <mee-offline-banner />                                                          ←   sibling ABOVE the padded area
  <div class="px-4 py-6 sm:px-6 max-w-7xl mx-auto w-full flex flex-col gap-6">    ← L1 PAGE CONTAINER  → mee-page
    <mee-page-header … />
    @if (errorMessage()) { <div class="flex flex-col gap-3" …> … </div> }         ← L2 error block
    <div aria-live="polite" … class="flex flex-col gap-6"> … </div>               ← L3 async region
      <div class="mee-stat-grid"> … </div>                                        ← L4 stat grid (CSS class)
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3"> …</div> ← L5 search/filter toolbar
      <div class="mee-table-wrap"> <table class="mee-table"> … </div>             ← L6 table region
```

| # | Hand-rolled element | Maps to | Verdict | Reason |
|---|---|---|---|---|
| **L0** | `mee-dashboard w-full flex flex-col` (outer wrapper holding `<mee-offline-banner/>` ABOVE the padded area) | — | **LEAVE RAW** | Structural: the offline banner is deliberately edge-to-edge (full-bleed, no page padding) and sits OUTSIDE the padded column. `mee-page` would wrap the banner in padding + max-width, shifting it. Keep L0 as the unpadded outer; `mee-page` replaces only L1 inside it. **The `<mee-offline-banner/>` stays as a sibling above `<mee-page>`.** |
| **L1** | `px-4 py-6 sm:px-6 max-w-7xl mx-auto w-full flex flex-col gap-6` (page content column) | **`mee-page maxWidth="xl" padding="tight" gap="lg"`** | **ADOPT** ✅ | **Byte-parity — the clean exemplar.** See §3 for the 3 token equivalences. This is the only swap in the pilot and the reason dashboard was chosen over pricing. |
| L2 | `flex flex-col gap-3` (error banner + retry, inside `@if`) | `mee-stack [gap]="sm"` (`--mee-space-2`=8px) | **LEAVE RAW** | `gap-3` = Tailwind 12px = `--mee-space-3`; `mee-stack` has **no `'sm-plus'`/12px token** (`sm`=8px, `md`=16px). No exact match → mapping changes spacing. Trivial 2-child block; no benefit. Leave raw. |
| L3 | `flex flex-col gap-6` (aria-live async region) | `mee-stack [gap]="lg"` | **LEAVE RAW** | Could map (`gap-6`=24px=`lg`), BUT this `<div>` carries load-bearing `aria-live="polite" aria-atomic="false"` a11y attributes. `mee-stack` renders its own inner `<div>` and does **not** forward arbitrary host attributes to the flex container — moving the aria-live onto a wrapper would change the screen-reader live-region boundary (WCAG 4.1.3 regression risk). **Leave raw** to preserve the exact a11y semantics. |
| L4 | `.mee-stat-grid` (CSS: `display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:12px`) | `mee-grid [cols]="2"` | **LEAVE RAW** ❌ | **Flat 2-col at ALL breakpoints** (including 360px mobile). `mee-grid [cols]="2"` renders mobile-first `grid-cols-1 sm:grid-cols-2` → **1 column on mobile**. Mapping would change the 360px stat-card layout from 2-up to 1-up — a real visual regression on the seller's phone. Also `gap:12px` (`--mee-space-3`) ≠ `mee-grid` `gap="md"` (16px) and ≠ `gap="sm"` (8px). **Hard-rule §5.3: a flat `grid-cols-N` ≠ `mee-grid [cols]=N` → leave raw.** Verdict stated explicitly per task item 2. |
| L5 | `flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3` (search/filter toolbar) | `mee-stack` / `mee-toolbar` | **LEAVE RAW** | Responsive **direction flip** (`flex-col` → `sm:flex-row`) plus a **responsive gap change** (`gap-2`→`sm:gap-3`). No primitive expresses a breakpoint direction-flip or per-breakpoint gap. Same class as the pricing SPEC's H4. **Leave raw.** |
| L6 | `.mee-table-wrap` + `<table class="mee-table">` | `mee-table` (`MEE_DATA`) | **LEAVE RAW** | Hand-rolled semantic `<table>` with token CSS, scoped headers, focus-visible rows, min-width horizontal-scroll, custom pagination bar. `mee-table` wraps a different data model — mapping rewrites the whole results region (out of pilot scope, parity risk). Same as pricing's table verdict. |

**Mapping outcome:** of 7 layout candidates, **exactly 1 (L1) adopts** at byte-parity; the other 6 leave-raw for documented reasons. This is the honest, clean exemplar — one real `mee-page` adoption + a textbook set of "when to leave raw" declines.

---

## 3. Byte-parity assertion for the page container (L1)

Source (template line 64): `px-4 py-6 sm:px-6 max-w-7xl mx-auto w-full flex flex-col gap-6`

`<mee-page maxWidth="xl" padding="tight" gap="lg">` renders (per `page.component.ts` on this worktree @ `283496d`):
`flex flex-col w-full mx-auto max-w-screen-xl px-4 py-6 sm:px-6` on the inner `<div>`, plus `[style.gap]="var(--mee-space-6)"`.

**The three token equivalences (all confirmed against source on this worktree):**

| Source class | mee-page prop → output | Equivalence proof | Match |
|---|---|---|---|
| `max-w-7xl` | `maxWidth="xl"` → `max-w-screen-xl` | `max-w-7xl` = 80rem = **1280px**; Tailwind `screen-xl` breakpoint = **1280px** → `max-w-screen-xl` caps at 1280px. Identical computed width. | ✅ |
| `px-4 py-6 sm:px-6` | `padding="tight"` → `px-4 py-6 sm:px-6` (6a, #273) | `page.component.ts` `paddingClass()`: `if (p === 'tight') return 'px-4 py-6 sm:px-6'`. **Character-for-character identical** to source. (Default `true` would wrongly add `lg:px-8`; `none` drops padding — `tight` is the exact one.) | ✅ |
| `flex flex-col … gap-6` | `gap="lg"` → `[style.gap]="var(--mee-space-6)"` | Source uses **flex `gap-6`** = Tailwind 1.5rem = **24px**. `--mee-space-6` = **24px** (`libs/design-tokens/_tokens.css` L48). `MEE_GAP_TOKEN.lg = var(--mee-space-6)`. Both `mee-page` and source put the gap on a `flex flex-col` container → **same flex-gap mechanism, same 24px** — NOT a margin-vs-gap swap. | ✅ |

Container structural classes both resolve to `flex flex-col w-full mx-auto` (order differs but Tailwind class order is non-semantic). **All three equivalences hold → L1 is a zero-visual-change adoption.** This is the substantive difference from pricing (whose `space-y-6` margin + missing `sm:px-6` blocked its L1).

> **One caveat for the builder:** `gap-6` (Tailwind class, applied via the source `<div>`'s class attribute) and `mee-page`'s `[style.gap]:var(--mee-space-6)` both produce a 24px flex gap, but one is a **utility class** and the other an **inline style**. They are computationally identical (24px flex `gap`), but the builder MUST screenshot-verify all 3 breakpoints to confirm no child contributes an unexpected own-margin (none do today: page-header, error block, async region are gap-spaced children with no top/bottom margin). This is the only subtle point and the reason ui-styler reviews it.

---

## 4. Parity hazards (flag to builder + ui-styler in advance)

- **H1 — offline-banner must stay OUTSIDE `mee-page` (BLOCKING if mis-wired):** `<mee-offline-banner/>` is a full-bleed sibling above the padded column (L0). The builder MUST keep it as a sibling: `<div class="mee-dashboard …"> <mee-offline-banner/> <mee-page …> … </mee-page> </div>`. Wrapping the banner inside `mee-page` adds padding + max-width to a deliberately edge-to-edge element → visual regression. Do NOT collapse L0 into `mee-page`.
- **H2 — `.mee-stat-grid` is flat 2-col at 360px (BLOCKING if mapped):** mapping it to `mee-grid [cols]="2"` collapses stat cards to 1 column on mobile. **Leave raw.** Mobile (360px) stat layout is the highest-traffic seller view — any change here is a P0 regression.
- **H3 — `gap-6` utility vs `[style.gap]` inline equivalence (verify, don't assume):** both = 24px flex gap, but ui-styler MUST pixel-diff at 360/768/1280 to confirm no child margin interacts. (Lower risk than pricing's `space-y` because the source already uses flex-gap, not margin.)
- **H4 — `aria-live` region (L3) must keep its host attributes:** do not move the async region into a `mee-stack` — `aria-live="polite" aria-atomic="false"` would land on the wrong node. Leave L3 raw.
- **H5 — responsive direction-flip + per-breakpoint gap (L5):** `flex-col gap-2 → sm:flex-row sm:gap-3` has no primitive. Do not force `mee-stack`/`mee-toolbar`.
- **H6 — `MEE_COMMON`/`MeeMenu`→PrimeNG bundle trap (landing):** do NOT adopt `MEE_COMMON` for landing's lone `MeeButton`; it drags `primeng/menu` and breaches the bundle bar. Keep `MeeButtonComponent` individual.
- **H7 — `MEE_LAYOUT` spread vs single import:** import `MeePageComponent` alone, not `...MEE_LAYOUT` (5 unreferenced layout components otherwise enter the chunk; cheap but needless — §1.1).

---

## 5. B acceptance / parity-proof obligation

Builder + ui-styler must attach to the PR:

1. **Screenshots BEFORE and AFTER** at **360 / 768 / 1280px** of **both** exposed routes:
   - `/dashboard` in 4 states: loading (skeletons), populated table (multi-row, both stat cards), empty state, error state (alert-banner + retry). **L1's padding/width/gap is exercised in every state** — these are the screenshots that prove parity.
   - `/` (landing) at all 3 breakpoints — to prove landing is **unchanged** (it should be byte-identical; landing has zero edits, so this is a regression guard, not an adoption proof).
   - **B bar = pixel-identical BEFORE vs AFTER.** Any delta → eliminate (re-check L1 props) or escalate to founder as a C-decision for that element.
2. **Bundle delta:** `ng build mfe-dashboard` before vs after; report the lazy `mfe-dashboard` chunk **raw + gzip**. Must be **≤ +2 KB gzip**. Expected: **near-zero** (one extra dependency-light `MeePageComponent`, no PrimeNG pulled). If gzip rises > 2 KB, investigate (most likely an accidental `...MEE_LAYOUT` spread — revert to single import).
3. **FE Gate green** (5 strict contracts) — must stay green; this pilot touches no contract, no PrimeNG, no deep import. `@mesell/layout` is a legal public barrel for an MFE to consume.
4. **Tests:** `dashboard.component.spec.ts`, `landing.component.spec.ts`, `dashboard-api.service.spec.ts` stay green (baseline = passing on develop). If `dashboard.component.spec` asserts on the page-container `<div>` class string, it must be updated to query the `<mee-page>` host instead — the builder owns that spec update and notes it in the PR.
   - **Known pre-existing failure (NOT introduced here):** `apps/shell/src/app/app.spec.ts` NG0201 missing `MessageService` — recurring on every UI-DS PR; ignore it, do not "fix" it in this pilot (separate cleanup ticket — see `ui_ds_phase3.md`).

> **Honest pilot expectation:** unlike pricing (which was a near-no-op), dashboard ships **one real, visible-in-the-DOM adoption** (L1 → `mee-page`) at **provable byte-parity**, plus a clean set of documented leave-raw declines. This is the canonical exemplar the A-convention points to: "here is what adopting `mee-page` looks like, and here is how to correctly decline the grid/toolbar/table."

---

## 6. Merge-gate criteria (what I, the coordinator, will check)

Before squash-merging `feat/ui-ds-phase6-dashboard` → (founder merges → `develop`), I verify:
- [ ] Only `dashboard.component.ts` changed (+1 import, L1 div → `<mee-page maxWidth="xl" padding="tight" gap="lg">`); `landing.component.ts` and all other files unchanged (`git diff --stat` confirms).
- [ ] Frontend PR template (`.github/PULL_REQUEST_TEMPLATE/frontend.md`) fully filled — no `<>` placeholders.
- [ ] BEFORE/AFTER screenshots at 360/768/1280 for `/dashboard` (4 states) + `/` attached and pixel-identical.
- [ ] Bundle delta ≤ +2 KB gzip on the `mfe-dashboard` lazy chunk, reported in PR body.
- [ ] FE Gate (5 strict contracts) green; CI gates 1 (unit) + 3 (lint) green.
- [ ] `pnpm build` (mfe-dashboard) < 90 s (Decision 12 stop condition).
- [ ] a11y preserved: offline-banner full-bleed (H1), stat grid 2-up at 360 (H2), `aria-live` region intact (H4), keyboard nav + focus-visible on table rows / delete / pagination unchanged.
- [ ] `dashboard.component.spec.ts` green (page-container assertions updated to `<mee-page>` if any existed).
- [ ] `feature_board_frontend.md` row for this pilot = `IN REVIEW` (specialist set on PR open per D2).

Reject back to the specialist (with explicit comments) on any unchecked box. Founder owns the `→ develop` gate.

---

## 7. HYBRID dispatch note

- **SPEC author / merge-gate:** `meesell-frontend-coordinator` (me).
- **Builder:** `meesell-angular-component-builder` — executes §1.1 (add `MeePageComponent` import) + §2 L1 swap, keeps `<mee-offline-banner/>` as a sibling above `<mee-page>` (H1), runs `ng build mfe-dashboard` + bundle delta, captures BEFORE/AFTER screenshots, updates `dashboard.component.spec.ts` if it asserted on the old container class.
- **Parity review:** `meesell-angular-ui-styler` — owns the 3-breakpoint pixel-diff (esp. H3 flex-gap equivalence, H2 stat-grid mobile 2-up, H1 banner full-bleed), signs off or rejects on any delta.
- **Merge gate:** coordinator reviews against §5 (B bar) + §6 + the frontend PR template; squash-merge `feat/ui-ds-phase6-dashboard` only when parity + bundle + FE Gate all pass. **Founder owns `→ develop`.**
- **Sequencing:** 6a is ALREADY merged (#273 @ `283496d`) → no precondition blocks the build. One worktree (`/tmp/mesell-wt/ui-ds-phase6-dashboard`), one branch (`feat/ui-ds-phase6-dashboard`), one PR. **NEVER git in the master tree** (`/Users/mugunthansrinivasan/Project/mesell`).
- **After dashboard:** further MFE adoption stays **opportunistic** (migrate when a ticket already touches the file), never a scheduled sweep (subplan §3 — reject C as a mandate).

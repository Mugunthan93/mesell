# UI-DS Phase 6 — DASHBOARD B-pilot SPEC (2026-06-17)

> Indexed under MEMORY.md. Companion to `ui_ds_phase3.md` (layout primitives) and the Phase 6 subplan.
> NOTE: authored in the `primeng-docs-scrape` worktree (memory writes redirected here this session);
> fold into the shared `ui_ds_phase3.md` tail on next non-isolated session.

**Status:** SPEC written → `/tmp/mesell-wt/ui-ds-phase6-dashboard/docs/plans/architecture/UI_DS_PHASE6_DASHBOARD_SPEC.md`.
Worktree `feat/ui-ds-phase6-dashboard` @ `283496d` (6a = #273 already merged → `padding="tight"` = `px-4 py-6 sm:px-6`, NO `lg:px-8`).
Founder picked dashboard over pricing because pricing barely adopts (its L1 `space-y-6` + missing `sm:px-6` blocked the only candidate → near-no-op pilot).

**Dashboard MFE = 2 exposed components** (`DashboardComponent` /dashboard + `LandingComponent` /). Only `dashboard.component.ts` changes.

**Import-swap decision — NONE for ui-kit aggregators (+1 import total):**
- `dashboard.component.ts`'s ONLY `@mesell/ui-kit` symbol is `MeeConfirmService` — a PROVIDER (`inject()`), structurally ineligible for any aggregator (aggregators = component-class arrays for `imports:[]` only; verified in `ui-kit/aggregators.ts` header). Its other components are all `@mesell/composites` (no composites aggregator exists).
- `landing.component.ts` uses `MeeButtonComponent` = 1/4 `MEE_COMMON`, below half-bar + `MEE_COMMON` drags `MeeMenu`→`primeng/menu` → keep individual (same trap as pricing). Landing = 100% unchanged.
- Net change to the whole MFE = **+1 import: `MeePageComponent`** in `dashboard.component.ts`.
- (Subplan §1 said "dashboard 2 ui-kit imports" — STALE; real source has 1, a provider. Don't trust the count.)

**Layout mapping (7 candidates, 1 adopts):**
- **L1 page container ADOPTS** `mee-page maxWidth="xl" padding="tight" gap="lg"` at BYTE-PARITY — the clean exemplar. 3 equivalences confirmed against source:
  - `max-w-7xl` = 80rem = 1280px = `max-w-screen-xl`
  - `tight` = `px-4 py-6 sm:px-6` char-identical (6a #273)
  - **source uses flex `gap-6` = 24px = `--mee-space-6` (`_tokens.css` L48) — a real flex-gap, NOT `space-y`** → NO margin-vs-gap hazard (exactly why dashboard works where pricing's L1 didn't).
- LEAVE RAW: L0 outer (holds full-bleed `<mee-offline-banner/>` ABOVE padded col — banner stays sibling above `<mee-page>`, H1); L2 error block (`gap-3`=12px=`--mee-space-3`, no mee-stack token); L3 async region (load-bearing `aria-live` host attrs mee-stack won't forward, WCAG 4.1.3); **L4 `.mee-stat-grid` flat `repeat(2,minmax(0,1fr))`=2-col at 360px ≠ mee-grid mobile-first 1→sm:2 → breaks mobile, hard-rule §5.3**; L5 toolbar (responsive direction-flip + per-bp gap); L6 hand-rolled `<table>`.
- Mandate single `MeePageComponent` import, NOT `...MEE_LAYOUT` (spread pulls 5 unused layout comps; cheap—no PrimeNG—but needless, H7).

**LESSON (reusable):** when picking a B-pilot, the deciding factor is whether the page container uses **flex `gap-*` vs `space-y-*`**. Flex-gap → clean `mee-page` adoption (dashboard). `space-y` margin → margin-vs-flex-gap hazard forces leave-raw (pricing). Check the gap mechanism FIRST. Also: `MeeConfirmService`/`MeeToastService` are providers, never aggregator members — an MFE whose only ui-kit use is a confirm/toast service has ZERO aggregator swap available.

**HYBRID dispatch:** builder = `meesell-angular-component-builder` (L1 swap + keep banner sibling + bundle delta + screenshots + spec update); parity = `meesell-angular-ui-styler` (3-bp diff, H2 mobile 2-up, H3 flex-gap, H1 banner full-bleed); then I merge-gate. 6a already merged → no precondition blocks the build. One worktree / one branch / one PR; founder merges → develop.

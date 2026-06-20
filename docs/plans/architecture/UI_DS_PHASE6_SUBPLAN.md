> **⚠️ SUPERSEDED IN PART — landed late, reality moved ahead (2026-06-20).**
> This sub-plan was authored 2026-06-17 (then @ `develop` `27218d0`) and is being
> landed for the historical record. Since authoring, the decisions it *recommended*
> were taken and **partially executed**:
> - **Phase 6a** (`mee-page` padding scale `none|tight|default`) **MERGED** — PR #273 (`283496d`).
> - **Phase 7** (swap-proof: alt preset + icon seam + `SWAP_GUIDE.md`) **MERGED** — PR #276 (`a979b6e`).
> - **Phase 6 adoption is no longer at "0 MFE files"** as §1/§2 state. Verified on `develop`
>   `fa61a61` (2026-06-20): `MEE_LAYOUT` page primitives are now consumed in **~10 MFE files**
>   (pricing, dashboard, export, all catalog routes) and `mee-icon`/`MeeIconName` semantic
>   names are consumed across the shell chrome + dashboard + export + catalog + onboarding.
>   The **grouped `MEE_*` aggregators (`MEE_FORM`/`MEE_OVERLAY`/…) remain at 0 MFE consumers** —
>   that part of §2 still holds.
> - The DoD is fully met and **all 5 FE contracts are strict + the FE Gate is a required check**
>   (`node frontend/tools/contracts/run-all.mjs --strict` → 0 warnings on `develop`).
>
> Treat the §1/§2 "the goal is already met / 0 consumers" framing as a **2026-06-17 snapshot**,
> not current state. The strategic recommendation (adoption is ergonomic, not a correctness
> requirement; sweep opportunistically, never as a scheduled big-bang) **still stands**.

---

# UI Design-System Decoupling — Phase 6 Sub-Plan (Per-MFE Adoption)

**Status:** Planning (decision recommended, awaiting founder pick)
**Date:** 2026-06-17
**Parent:** [`UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md`](./UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md) §4 Phase 6
**Owner:** Founder (decision) + `meesell-frontend-coordinator` (execution)
**Scope:** `frontend/` — the 6 MFEs (auth, catalog, dashboard, export, onboarding, pricing), `@mesell/layout`

---

## 1. Reframe — the goal is already met

Phases 1–5 are **built and merged to `develop` @ `27218d0`** (#259/#260/#265/#267/#271). The
parent plan's Definition of Done, re-checked against `develop` today:

| DoD bullet | Status | Proof |
|---|---|---|
| `primeng`/`@primeuix`/`pi pi-` only inside design-system libs | ✅ | FE-1 + FE-2 **strict** |
| Every MFE builds importing only `@mesell/*` public barrels | ✅ | FE-5 **strict**, 0 deep imports |
| FE boundary-contract gate green **and blocking** | ✅ | "FE Gate: lint (5 contracts)" is a **required** status check on `develop` |
| Swapping theme **or** icon set is a one-file change | → | Demonstrated by **Phase 7** (independent of Phase 6 — see §6) |

**The decoupling is achieved and sealed.** The five strict contracts already *prevent* any new
PrimeNG/icon/deep-import leak from reaching `develop`. Therefore **Phase 6 is not a correctness
requirement — it is ergonomic adoption**: trading 19 MFE files' individual `@mesell/ui-kit`
imports + hand-rolled layout `<div>`s for concern-group aggregators + `MEE_LAYOUT` primitives,
purely for internal consistency. Its scope is a **choice**, not an obligation.

### What "adoption" actually means (measured on `develop`)

- **0** MFE files use any `MEE_*` aggregator.
- **0** MFE files use any `@mesell/layout` page primitive (`mee-page/section/grid/stack/form-layout`
  are unconsumed; the 18 grep hits were `mee-page-header` — a *composites* component already
  adopted — plus CSS class names like `.mee-page-btn`/`.mee-stat-grid`).
- **19** MFE files import `@mesell/ui-kit` individually: auth 3, catalog 10, dashboard 2, export 3,
  onboarding 9, pricing 4.
- **0** ad-hoc or contract-violating imports — there is **nothing to "remove"** (the parent plan's
  Phase 6 line "remove any remaining ad-hoc imports" is already satisfied by the strict contracts).

---

## 2. The parity blocker is real and code-confirmed

The crux is that the primitives' defaults ≠ each MFE's hand-rolled layout. Confirmed against the
actual source (`frontend/libs/layout/page/page.component.ts` on `develop`):

- `mee-page` `padding` is a **boolean**. `true` (default) → `px-4 py-6 sm:px-6 lg:px-8`; `false` → none.
- The dashboard page container is `px-4 py-6 sm:px-6 max-w-7xl mx-auto w-full flex flex-col gap-6`.
- The **only** delta is `lg:px-8` — `mee-page` *adds* 2rem of horizontal padding at ≥1024px that
  the dashboard lacks. There is **no input value** that yields `px-4 py-6 sm:px-6` (no `lg:px-8`).

So adopting `mee-page` on the dashboard **today** is impossible without a visual shift. Same class of
issue for grids: `mee-grid [cols]="2"` renders `grid-cols-1 sm:grid-cols-2` (1 col on mobile) — a
bespoke flat `grid-cols-2` (2 cols even on mobile, e.g. `.mee-stat-grid`) is **not** equivalent and
would change the mobile layout.

**Key enabling fact:** `@mesell/layout` has **zero consumers**. Refining a primitive's input API now
costs **nothing** — no migration, no breaking change in practice. This is the cheapest it will ever
be to make the primitives adoption-ready.

---

## 3. Recommendation — **A + 6a + a single B pilot; defer C indefinitely**

The three options the execution session surfaced:

- **(A) Defer** — forward-convention only; mandate "new/touched code uses the canonical surface,"
  rely on the strict contracts, skip retro-migration. *(execution session's lean.)*
- **(B) Light** — migrate only provably zero-visual-change cases, MFE by MFE.
- **(C) Full sweep** — migrate all 6, accept the primitives' defaults as the new normal (small
  intentional deltas), ui-styler parity review per MFE, ~6 PRs.

**Recommended: a hybrid — adopt A as the standing rule, ship one small 6a primitive tweak, and run
ONE B-style pilot to produce the canonical exemplar. Do NOT mandate C.**

### Why not pure C
C accepts intentional visual deltas on **live, seller-facing UI** (Tirupur sellers, pre-PMF) to buy
*internal* consistency the contracts don't require. Six PRs across six live MFEs under founder review,
each risking a real visual regression, for zero functional or correctness gain — the risk/reward is
upside-down for a revenue product. Reject C as a mandate. (A future deliberate redesign can revisit it.)

### Why not pure A
A library nothing consumes rots: its API never gets battle-tested, and "forward convention" is hard to
enforce by review when there is **no in-repo exemplar to copy**. The strict contracts block *leaks* but
there is **no contract that forces** `mee-page`/aggregator adoption — so pure-A risks `@mesell/layout`
becoming dead code. One real consumer fixes both.

### The recommended shape
1. **6a (primitive tweak, prerequisite):** make `mee-page` padding expressible without `lg:px-8` so
   pixel-parity adoption is *possible at all* (§4). Zero consumers ⇒ zero-risk, ships first.
2. **A (standing rule):** land a one-paragraph convention (CLAUDE.md / frontend CONTRIBUTING) — *new or
   touched* MFE code uses `MEE_*` aggregators + `MEE_LAYOUT` + `mee-icon`; contracts enforce the floor.
3. **B pilot (one MFE):** migrate the lowest-risk single-page MFE to zero-visual-change, producing the
   exemplar the convention points to. Stop there. Further MFEs become opportunistic (migrate when a
   ticket already touches that file), not a scheduled sweep.

**Acceptance bars by option:**

| Option | Acceptance bar |
|---|---|
| A | Convention documented + pilot exemplar exists. No per-file proof (review-enforced; contracts block leaks). |
| B | **Per MFE:** screenshot parity at 360 / 768 / 1280px (pixel-identical) **+** bundle-delta ≤ **+2 KB gzip** on the MFE's lazy chunk **+** FE Gate green. Any visual delta blocks B. |
| C | Same as B but founder-blessed visual deltas allowed; ui-styler documents each intentional delta per MFE. |

---

## 4. Phase 6a — `mee-page` padding parity tweak (prerequisite for any B/C)

**Problem:** boolean `padding` cannot express "responsive padding *without* the `lg:px-8` step,"
which existing pages (dashboard) use. Zero-visual-change adoption is impossible until it can.

**Decision — make `padding` a discrete scale (backward-compatible):**

```ts
export type MeePagePadding = 'none' | 'tight' | 'default';
// input accepts boolean | MeePagePadding
//   false / 'none'    → ''                                (edge-to-edge)
//   'tight'           → 'px-4 py-6 sm:px-6'               (matches dashboard — NEW)
//   true  / 'default' → 'px-4 py-6 sm:px-6 lg:px-8'       (current default — UNCHANGED)
```

- Boolean still works → no breaking change; and with **0 consumers** there is nothing to migrate.
- `'default'` stays the convention for **new** pages (the `lg:px-8` desktop breathing room is the
  intended design-system standard); `'tight'` exists only so an **existing** page can adopt `mee-page`
  with exact pixel-parity instead of a forced visual shift.
- **`mee-form-layout`:** no tweak needed — its `maxWidth` scale + token gap already cover the parity
  cases; confirm per-form during the pilot rather than pre-emptively widening the API.

**Scope:** one component + its spec, ~20 lines. HYBRID: coordinator SPEC → `meesell-angular-component-builder`
→ merge-gate. Ships as its own PR **before** the pilot. (If the chosen pilot turns out to use default
padding anyway, 6a still lands first — it makes the lib adoption-ready and unblocks dashboard later.)

---

## 5. Per-MFE migration playbook (governs the pilot and any future B/C migration)

### 5.1 Pilot selection — **NOT dashboard first**

The execution session eyed **dashboard**, but dashboard carries the padding pitfall *and* the bespoke
`.mee-stat-grid` — two parity hazards. A pilot should prove the *mechanics* with minimal hazard and
yield a reusable exemplar. Selection criteria: single self-contained route · moderate import count ·
no flat-`grid-cols-N` bespoke grid · exercises ≥1 page primitive + ≥1 aggregator.

- **Recommended pilot: `pricing`** (price-calculator) — one route, 4 imports; exercises `mee-page` +
  `mee-form-layout` + a `MEE_FORM`/`MEE_DATA` aggregator swap → the **richest single-page exemplar**.
- **Safer fallback: `export`** (3 imports, simplest page) if `pricing`'s P&L layout reveals its own
  bespoke pitfall on inspection.
- **Skip `auth` for page primitives** — it uses the centered `auth-layout` (composites), deliberately
  out of `MEE_LAYOUT` scope per parent §7. (auth can still do the aggregator swap independently.)
- **dashboard → second**, only after 6a + the pilot prove the flow (it needs `padding="tight"` and a
  per-case decision on `.mee-stat-grid`).

### 5.2 Per-MFE steps (the B acceptance procedure)

1. **Inventory** the MFE's individual `@mesell/ui-kit` imports + every hand-rolled layout `<div>`.
2. **Baseline screenshots** — each route at **360 / 768 / 1280px** (mobile / tablet / desktop), BEFORE.
3. **Aggregator swap** — replace individual imports with the smallest covering concern group(s).
   Rule of thumb: adopt a group when the MFE uses ≥ half its members; otherwise keep individual
   imports. (AOT tree-shakes unreferenced standalone imports — but **verify** via step 5, don't assume.)
4. **Layout-primitive swap** — apply the mapping table (§5.3); leave anything that can't reach parity as-is.
5. **Bundle-delta check** — `ng build <mfe>` before/after; compare the lazy chunk raw + gzip size.
   Accept ≤ **+2 KB gzip** (noise); anything larger must be explained or the aggregator reverted to
   individual imports for that MFE.
6. **Visual diff** — re-screenshot, compare to baseline. **B bar = pixel-identical.** Any delta either
   gets eliminated (via 6a config / leaving the element raw) or escalated to the founder as an
   intentional-delta decision — which converts *that MFE* to the C track (not the default).
7. **FE Gate** — must stay green (adoption only moves toward the canonical surface; it cannot violate a contract).

### 5.3 Primitive → hand-rolled mapping rules

| Hand-rolled pattern | Primitive | Parity note |
|---|---|---|
| `px-4 py-6 sm:px-6 lg:px-8 max-w-* mx-auto flex flex-col gap-*` | `mee-page [maxWidth] [padding] [gap]` | match `maxWidth` token + gap token; use `padding="tight"` (6a) when the source lacks `lg:px-8` |
| `flex flex-col gap-*` (generic vertical stack) | `mee-stack [gap]` | direct; map gap to nearest token |
| stacked form fields | `mee-form-layout [gap] [maxWidth]` | confirm field width + gap match |
| labeled block with a heading | `mee-section [heading]` | only if the heading markup/size already matches |
| `grid grid-cols-N gap-*` | `mee-grid [cols] [gap]` | **only if** the source's responsive ladder already matches mee-grid's mobile-first `1 → sm:2 → md:3 → lg:4`. A **flat** `grid-cols-2` (2 cols on mobile) ≠ `mee-grid [cols]="2"` (1 col on mobile) → **leave raw**, do not map. |
| toolbar / action row | `mee-toolbar` | confirm spacing/alignment |

**Hard rule:** if a primitive cannot reproduce the existing markup pixel-for-pixel (and 6a doesn't close
the gap), **leave the element hand-rolled** — that is permitted and contract-clean. Forcing a primitive
in to "tick the box" is exactly the C-style delta the recommendation avoids.

---

## 6. Phase 7 (swap-proof) sequencing — **runs independently, ship it next**

Phase 7 depends only on the libraries, which are **done**. It is **independent of Phase 6**: adding a
second theme preset (dark / alt-brand) toggled in one file + an icon-set swap (edit `MEE_ICONS` only)
needs no MFE adoption. It is also the deliverable that *actually demonstrates the DoD's last bullet*
("swap = one-file change").

**Recommendation: do Phase 7 BEFORE (or in parallel with) Phase 6 adoption.** Two reasons:
1. It proves the decoupling end-to-end *now*, regardless of which Phase 6 option is chosen.
2. It de-risks adoption — if the swap surfaces a leak (a hardcoded color/icon the contracts didn't
   catch because it isn't a `primeng`/`pi pi-` token), fix it in the libs *before* any MFE adopts them.

So Phase 6 being deferred (option A) does **not** block closing out the workstream — Phase 7 still ships
and the DoD is fully demonstrated.

---

## 7. Execution model & discipline (unchanged)

- **MeeSell HYBRID dispatch:** coordinator (`meesell-frontend-coordinator`) writes the task SPEC →
  named specialist builds (`meesell-angular-component-builder` for primitives/components,
  `meesell-angular-ui-styler` for parity/screenshot review) → coordinator runs the merge-gate review
  (a real gate — can reject). Only `meesell-*` agents execute MeeSell work.
- **Per-phase-worktree discipline:** one phase / one MFE = one worktree off `develop` = one branch =
  one PR. **Founder merges.** **NEVER run git in the master tree** (`/Users/mugunthansrinivasan/Project/mesell`).
- **Dev-only / no cloud spend.** The strict, **required** FE Gate is the safety net: any Phase 6/6a/7 PR
  that shifts a contract or fails a build is auto-blocked.

### Suggested sequence

```
6a (mee-page padding scale)  ──┐   one small PR, zero-risk, first
7  (swap-proof: theme + icon) ──┼─► both independent of MFE adoption; ship next
A  (convention doc)           ──┘
B-pilot (pricing or export)   ────► one PR, zero-visual-change exemplar
   └─ further MFEs: opportunistic only (when a ticket already touches the file), never a scheduled sweep
```

---

## 8. Decision needed from founder

1. **Adoption posture:** confirm **A + 6a + single B pilot** (recommended) vs pure-A (defer entirely)
   vs full-C sweep.
2. **Pilot MFE:** **pricing** (recommended exemplar) vs **export** (safest) — execution session confirms
   on inspection.
3. **Phase 7 timing:** confirm Phase 7 ships next, independent of the Phase 6 decision (recommended).

*Housekeeping (non-blocking): stale merged worktrees `/tmp/mesell-wt/ui-ds-phase{3,4,5}` + two
`agent-*` phase1/2 worktrees are safe to prune when convenient.*

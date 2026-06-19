# Sakai ↔ MeeSell — Upgrade-Path Recommendations

**Deliverable:** 6.4 of `docs/plans/ui-sakai-comparison-plan.md`
**Author:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-19
**Inputs:** MISSING_IN_MEESELL set from `sakai-component-gaps.md` + token gaps from `sakai-token-parity.md`.

## Priority levels

- **P0** — blocking user flows or accessibility (focus-ring tokens, checkbox/radio standard wrappers).
- **P1** — visible UX gap (breadcrumb, tabs, inline message).
- **P2** — nice-to-have (chip, panel, divider).
- **P3** — deferred / out of V1 scope (dark scheme, tree table, chart, scroll-panel, typography scale enrichment).

## Recommendation types

- **ALIGN** — build/adopt as a `mee-*` wrapper or new `--mee-*` token group.
- **KEEP CUSTOM** — MeeSell-specific; do not adopt Sakai's pattern.
- **DEFER** — out of V1 scope; revisit later.

> **Note on owner names:** per CLAUDE.md the executable specialist agents are `meesell-angular-component-builder` (components) and `meesell-angular-ui-styler` (tokens/theming). All builds route through the Frontend Lead merge gate.

---

## Component gaps (from `sakai-component-gaps.md`)

| Item | Type | Recommendation | Priority | Owner | Notes |
|---|---|---|---|---|---|
| `mee-checkbox` | Component | ALIGN — build wrapper around `p-checkbox` (CVA, OnPush) | P0 | angular-component-builder (+ ui-styler) | Standard form control with no wrapper today → forms either bypass the seal or hand-roll. A11y + form usability. |
| `mee-radio` | Component | ALIGN — build wrapper around `p-radiobutton` (CVA, OnPush) | P0 | angular-component-builder (+ ui-styler) | Same class as checkbox; single-select form gap. Build alongside `mee-checkbox`. |
| `mee-breadcrumb` | Component | ALIGN — build wrapper around `p-breadcrumb` | P1 | angular-component-builder | Deep catalog routes (`/catalogs/:id/{edit,images,preview,pricing,export}`) need wayfinding. Wire to router. |
| `mee-tabs` | Component | ALIGN — build wrapper around `p-tabs`/`p-tabview` | P1 | angular-component-builder | Visible UX pattern (e.g. preview/pricing tabbed views). |
| `mee-message` | Component | ALIGN — build inline-message wrapper around `p-message` | P1 | angular-component-builder (+ ui-styler) | Field/section-level inline validation messaging; `alert-banner` is page-level only. Pairs with the `validation.*.missing` i18n fallback work. |
| `mee-chip` | Component | ALIGN — build wrapper around `p-chip` | P2 | angular-component-builder | Removable tag tokens (e.g. selected categories/filters). Lower urgency; `mee-badge` covers static tags. |
| `mee-panel` | Component | ALIGN — build wrapper around `p-panel` | P2 | angular-component-builder | Theming groundwork already done (`panel.root.borderRadius:16px` in preset) → cheap build, just needs the component. |
| `mee-divider` | Component | ALIGN — build wrapper around `p-divider` | P2 | angular-component-builder | Trivial; common layout need. |
| `mee-scroll-panel` | Component | DEFER | P3 | angular-component-builder | No confirmed V1 use case; native overflow + CSS suffices for now. Revisit if a fixed-height scroll region appears. |
| `mee-table` feature depth (filters, frozen cols, row-group, export) | Component (enhance) | KEEP CUSTOM (build features on demand) | P2 | angular-component-builder | `mee-table` already exceeds baseline Sakai (virtual scroll + lazy server search). Add Sakai-grade features only when a route needs them — do not preemptively absorb the whole DataTable surface. |

## Token gaps (from `sakai-token-parity.md`)

| Item | Type | Recommendation | Priority | Owner | Notes |
|---|---|---|---|---|---|
| Focus-ring token group (`--mee-focus-ring-width/-style/-color/-offset`) | Token | ALIGN — add explicit focus-ring tokens; project into preset | P0 | ui-styler | A11y. Today focus ring is inherited Aura default with no MeeSell control. Make it explicit + brand-orange, verify keyboard nav contrast on P0 routes. |
| Typography scale (`--mee-font-size-*`, `--mee-line-height-*`, `--mee-font-weight-*`) | Token | ALIGN — add a typography token group | P1 | ui-styler | Today type is ad-hoc Tailwind `text-*`. A token scale enforces consistency and is swap-proof. Map to existing in-use sizes first (no visual change), then converge. |
| Dark `colorScheme.dark.*` | Token | DEFER | P3 | ui-styler | V1 is light-only by scope (divergence D26). Re-open post-PMF. Large surface; not a V1 need. |
| Card shadow internal inconsistency (`card.root.shadow` α=0.08 vs `--mee-shadow-md` α=0.10) | Token (cleanup) | ALIGN — point `card.root.shadow` at `--mee-shadow-md` | P2 | ui-styler | Internal MeeSell drift, not a Sakai gap. One-line preset cleanup for consistency. |

## Items explicitly NOT to align (KEEP CUSTOM / NOT_APPLICABLE)

| Item | Decision | Why |
|---|---|---|
| All 26 intentional divergences in `sakai-divergence-log.md` | KEEP CUSTOM | Brand + architecture identity (orange, cool-grey surfaces, dark sidebar, pill buttons, soft 16px cards, 3-step motion/elevation, `--mee-*` token wall, named layout primitives). |
| MeeSell composites (`stat-card`, `status-badge`, `alert-banner`, `offline-banner`, `empty-state`, `loading-skeleton`, `auth-layout`, `page-header`) | KEEP CUSTOM | MISSING_IN_SAKAI value-adds. |
| MeeSell form primitives (`mee-otp-input`, `mee-password-input`, `mee-tree-select`) | KEEP CUSTOM | Domain-specific (phone OTP login, category tree). |
| Named layout primitives (`mee-page/section/stack/grid/toolbar/form-layout`) | KEEP CUSTOM | Typed swap-proof layout API vs PrimeFlex utilities. |
| Spacing / shadow global token scales | KEEP CUSTOM | MISSING_IN_SAKAI; architecture (D20/D21). |
| TreeTable | DEFER / NOT_APPLICABLE | No V1 hierarchical-table use case; `mee-tree-select` serves the tree need. |
| Chart | DEFER / NOT_APPLICABLE | No V1 charting; dashboard uses `stat-card`. Revisit V1.5 analytics. |
| Fieldset | NOT_APPLICABLE | `mee-form-layout` covers grouped fields. |

---

## Summary

### ALIGN by priority

| Priority | ALIGN items | List |
|---|---|---|
| **P0** | 3 | `mee-checkbox`, `mee-radio`, focus-ring token group |
| **P1** | 4 | `mee-breadcrumb`, `mee-tabs`, `mee-message`, typography token group |
| **P2** | 4 | `mee-chip`, `mee-panel`, `mee-divider`, card-shadow cleanup |
| **P3** | 0 ALIGN | — |

**Total ALIGN: 11** (3×P0, 4×P1, 4×P2).

### Other dispositions

| Disposition | Count | Items |
|---|---|---|
| **KEEP CUSTOM** | 8 groups | 26 divergences (as a block) + 8 composites + 3 form primitives + 6 layout primitives + spacing/shadow scales + `mee-table` enhance-on-demand. |
| **DEFER (P3)** | 3 | dark scheme, `mee-scroll-panel`, (TreeTable/Chart as NOT_APPLICABLE). |

### Recommended build sequence (lead's call)

1. **Sprint 1 (P0):** `mee-checkbox` + `mee-radio` (one dispatch, shared CVA pattern) → ui-styler focus-ring tokens in the same wave (a11y bundle). Dispatch order: ui-styler focus-ring tokens first (gates control theming), then component-builder for the two controls.
2. **Sprint 2 (P1):** `mee-breadcrumb` + `mee-tabs` + `mee-message`; typography token group in parallel (ui-styler) since it's non-blocking and non-visual if mapped to current sizes.
3. **Sprint 3 (P2):** `mee-panel` (cheapest — theming done) + `mee-divider` + `mee-chip`; fold in the card-shadow cleanup.
4. **Deferred:** dark scheme + scroll-panel revisited post-PMF / when a route demands them.

Each build runs the standard three-step dispatch (coordinator SPEC → specialist → coordinator merge-gate review) and must clear the merge gate (PR template, 360/1280 screenshots, a11y checks, build < 90s).

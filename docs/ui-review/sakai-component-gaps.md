# Sakai ↔ MeeSell — Component Gap List

**Deliverable:** 6.2 of `docs/plans/ui-sakai-comparison-plan.md`
**Author:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-19
**Sources scanned:**
- `frontend/libs/ui-kit/index.ts` (barrel — 21 wrappers + `mee-multiselect`)
- `frontend/libs/ui-kit/multiselect/multiselect.component.ts` (flat dir, no nested `index.ts`; exported via ui-kit barrel L25)
- `frontend/libs/composites/index.ts` (8 composites)
- `frontend/libs/layout/index.ts` (6 page primitives + 4 chrome primitives)

**Sakai reference set (plan §2.2):** DataTable, Panel, Card, Button, InputText, Dropdown/Select, MultiSelect, Checkbox, RadioButton, Textarea, Sidebar/Drawer, Topbar/Menubar, Breadcrumb, Tabs/TabView, Toast, Dialog, ConfirmDialog, Tag/Badge, Chip, ProgressBar, ProgressSpinner, Skeleton, TreeTable, Chart, FileUpload, Steps/Stepper.

## Classification legend

- ✅ **COVERED** — `mee-*` wrapper exists (named).
- 🔴 **MISSING_IN_MEESELL** — no wrapper; candidate to build.
- 🟡 **PARTIAL** — wrapper exists but lacks features vs Sakai.
- ℹ️ **NOT_APPLICABLE** — Sakai component out of MeeSell V1 scope.

## Confirmed MeeSell wrapper inventory (as scanned)

ui-kit (22): `mee-icon`, `mee-button`, `mee-input`, `mee-otp-input`, `mee-badge`, `mee-card`, `mee-table`, `mee-dialog`, `mee-file-upload`, `mee-steps`, `mee-select`, `mee-tree-select`, `mee-skeleton`, `mee-progress-bar`, `mee-spinner`, `mee-toast`, `mee-confirm-dialog`, `mee-password-input`, `mee-textarea`, `mee-drawer`, `mee-menu`, `mee-multiselect`.
composites (8): `stat-card`, `status-badge`, `page-header`, `empty-state`, `loading-skeleton`, `auth-layout`, `alert-banner`, `offline-banner`.
layout page primitives (6): `mee-page`, `mee-section`, `mee-toolbar`, `mee-grid`, `mee-stack`, `mee-form-layout`.
layout chrome (4, shell-only / FE-3 sealed): `app-bar`, `side-nav`, `nav-item`, `user-menu`.

---

## Track B — Form components

| Sakai component | MeeSell wrapper | Class | Detail |
|---|---|---|---|
| InputText | `mee-input` | ✅ COVERED | `MeeInputType = text \| email \| number \| tel`. |
| Textarea | `mee-textarea` | ✅ COVERED | Present in `MEE_FORM`. |
| Dropdown / Select | `mee-select` | ✅ COVERED | `MeeSelectOption = { label; value }`. |
| MultiSelect | `mee-multiselect` | ✅ COVERED | CVA wrapper of `p-multiselect`; virtual scroll + lazy server-side search (Wave D/E). Richer than baseline Sakai demo. |
| Checkbox | — | 🔴 MISSING_IN_MEESELL | No `mee-checkbox`. Forms use ad-hoc / no standard wrapper. Real gap. |
| RadioButton | — | 🔴 MISSING_IN_MEESELL | No `mee-radio`. Real gap. |
| (TreeSelect) | `mee-tree-select` | ✅ COVERED | MeeSell extra (category picker). `MeeTreeNode` type. |
| (Password) | `mee-password-input` | ✅ COVERED | MeeSell-specific; no Sakai demo equivalent → also MISSING_IN_SAKAI. |
| (OTP) | `mee-otp-input` | ✅ COVERED | MeeSell-specific (phone OTP login) → also MISSING_IN_SAKAI. |

## Track C — Data display

| Sakai component | MeeSell wrapper | Class | Detail |
|---|---|---|---|
| Card | `mee-card` | ✅ COVERED | `card.root` radius 16 + shadow in preset. |
| Tag / Badge | `mee-badge` | ✅ COVERED | `MeeBadgeSeverity = success \| warning \| danger \| info \| neutral`. Covers both Sakai Tag and Badge concepts. |
| DataTable | `mee-table` | 🟡 PARTIAL | Has virtual scroll + lazy server-side search + sort + paging (`MeeColumn`, `MeeTablePageEvent`, `MeeTableSortEvent`). Sakai DataTable additionally offers column filters, frozen columns, row grouping, row expansion, column resize/reorder, CSV/export. Build those on demand, not preemptively. |
| Chip | — | 🔴 MISSING_IN_MEESELL | No `mee-chip`. Gap (tag-like removable token). |
| TreeTable | — | ℹ️ NOT_APPLICABLE | No V1 use case for hierarchical tabular data; category tree is served by `mee-tree-select`. |
| Chart | — | ℹ️ NOT_APPLICABLE | No charting in V1 routes; dashboard uses `stat-card`. Defer to V1.5 analytics. |
| (StatCard) | `stat-card` (composite) | ✅ COVERED | MeeSell-only → also MISSING_IN_SAKAI. |
| (StatusBadge) | `status-badge` (composite) | ✅ COVERED | MeeSell-only product-status badge → also MISSING_IN_SAKAI. |

## Track D — Navigation

| Sakai component | MeeSell wrapper | Class | Detail |
|---|---|---|---|
| Sidebar / Drawer | `mee-drawer` (ui-kit) + `side-nav` (chrome) | ✅ COVERED | `mee-drawer` = overlay drawer; `side-nav`/`nav-item` = persistent shell sidebar (4-group, dark `#111c2d`). Shell sidebar is host-owned chrome (FE-3 sealed). |
| Topbar / Menubar | `app-bar` + `user-menu` (chrome) + `mee-menu` (ui-kit) | ✅ COVERED | `app-bar` topbar chrome; `mee-menu` (`MeeMenuItem`) for popup menus. |
| Breadcrumb | — | 🔴 MISSING_IN_MEESELL | No `mee-breadcrumb`. Gap for deep catalog routes (`/catalogs/:id/...`). |
| Tabs / TabView | — | 🔴 MISSING_IN_MEESELL | No `mee-tabs`. Gap. |
| (Steps/Stepper) | `mee-steps` | ✅ COVERED | `MeeStep` type; used in catalog wizard. (Sakai Steps/Stepper — also relevant to Track B/C wizard flows.) |

## Track E — Feedback

| Sakai component | MeeSell wrapper | Class | Detail |
|---|---|---|---|
| Toast | `mee-toast` + `MeeToastService` | ✅ COVERED | Service in `provideMeeUi()`. |
| Dialog | `mee-dialog` | ✅ COVERED | `dialog.root` radius 16. |
| ConfirmDialog | `mee-confirm-dialog` + `MeeConfirmService` | ✅ COVERED | `MeeConfirmConfig`; service-driven. |
| ProgressBar | `mee-progress-bar` | ✅ COVERED | In `MEE_FEEDBACK`. |
| ProgressSpinner | `mee-spinner` | ✅ COVERED | In `MEE_FEEDBACK`. |
| Skeleton | `mee-skeleton` | ✅ COVERED | `MeeSkeletonVariant`. |
| Message (inline) | — | 🔴 MISSING_IN_MEESELL | No `mee-message` inline-message wrapper. `alert-banner` composite is page-level, not field/inline-level. Minor gap. |
| (AlertBanner) | `alert-banner` (composite) | ✅ COVERED | `MeeAlertVariant`; MeeSell-only → MISSING_IN_SAKAI. |
| (OfflineBanner) | `offline-banner` (composite) | ✅ COVERED | MeeSell-only network state → MISSING_IN_SAKAI. |
| (EmptyState) | `empty-state` (composite) | ✅ COVERED | MeeSell-only → MISSING_IN_SAKAI. |
| (LoadingSkeleton) | `loading-skeleton` (composite) | ✅ COVERED | Composed skeleton layout → MISSING_IN_SAKAI. |

## Track F — Layout primitives

| Sakai component | MeeSell wrapper | Class | Detail |
|---|---|---|---|
| Panel | — | 🔴 MISSING_IN_MEESELL | `panel.root.borderRadius:16px` is tokenized in the preset, but **no `mee-panel` wrapper component exists**. Gap (token without component). |
| Divider | — | 🔴 MISSING_IN_MEESELL | No `mee-divider`. Gap. |
| ScrollPanel | — | 🔴 MISSING_IN_MEESELL | No `mee-scroll-panel`. Gap. |
| Fieldset | — | ℹ️ NOT_APPLICABLE | `mee-form-layout` covers grouped-field layout; Fieldset's collapsible legend is not a V1 need. |
| PrimeFlex grid utilities | `mee-grid`, `mee-stack`, `mee-page`, `mee-section`, `mee-toolbar`, `mee-form-layout` | ✅ COVERED (different model) | MeeSell uses **named layout primitives** (`MeeGridCols`, `MeeStackDirection/Align/Justify`, `MeePageMaxWidth`, `MeeToolbarAlign`, `MeeFormMaxWidth`) instead of utility classes. These are MeeSell-only → also MISSING_IN_SAKAI. |

## File / misc

| Sakai component | MeeSell wrapper | Class | Detail |
|---|---|---|---|
| FileUpload | `mee-file-upload` | ✅ COVERED | `MeeFileUploadEvent`; `MEE_FILE` aggregator. |
| (Icon) | `mee-icon` | ✅ COVERED | `MeeIconName` registry + swap-proof `MEE_ICONS_ALT` / `ActiveIcons` (Phase 7 seam). |

---

## MISSING_IN_SAKAI — MeeSell value-adds to preserve

These have no Sakai/PrimeNG-demo equivalent and represent MeeSell-specific value. **Keep — do not align away.**

| MeeSell surface | Layer | Why it's a value-add |
|---|---|---|
| `mee-otp-input` | ui-kit | Phone-OTP login primitive (Decision #5). |
| `mee-password-input` | ui-kit | Show/hide password field with strength affordance. |
| `mee-tree-select` | ui-kit | Meesho category tree picker. |
| `stat-card` | composite | Dashboard metric tile. |
| `status-badge` | composite | Product/catalog status semantics. |
| `page-header` | composite | Standard page title/action header. |
| `empty-state` | composite | Zero-data illustration + CTA. |
| `loading-skeleton` | composite | Composed page skeletons. |
| `auth-layout` | composite | Split auth screen shell (SP03 D21). |
| `alert-banner` | composite | Page-level dismissible alert. |
| `offline-banner` | composite | Network-offline indicator. |
| `mee-page` / `mee-section` / `mee-stack` / `mee-grid` / `mee-toolbar` / `mee-form-layout` | layout | Named, typed page primitives (vs PrimeFlex utility classes). |
| `--mee-*` token wall | design-tokens | Library-swap-proof token layer (architecture; not a component but the headline value-add). |

---

## Summary

**Total MISSING_IN_MEESELL (component gaps): 9**

| Track | Missing components |
|---|---|
| B (Forms) | `mee-checkbox`, `mee-radio` |
| C (Data) | `mee-chip` |
| D (Nav) | `mee-breadcrumb`, `mee-tabs` |
| E (Feedback) | `mee-message` (inline) |
| F (Layout) | `mee-panel`, `mee-divider`, `mee-scroll-panel` |

**PARTIAL: 1** — `mee-table` (vs Sakai DataTable feature depth).
**NOT_APPLICABLE: 4** — TreeTable, Chart, Fieldset, (Sakai-side) PrimeFlex utilities-as-primitives.
**COVERED: rest** (every other Sakai reference component has a wrapper).
**MISSING_IN_SAKAI value-adds: 13+** (listed above).

### Surprises found during the barrel scan (not in the plan)

1. **`mee-multiselect` has no nested `index.ts`** — the task referenced `frontend/libs/ui-kit/multiselect/index.ts` but the dir is flat (`multiselect.component.ts` only); it's exported directly from the ui-kit barrel at L25–26, including the `MeeShowErrorOn` type. The plan's §1.6 "barrel-exported" note is correct; the per-component index.ts assumption is not.
2. **Plan §1.3 says "21 ui-kit primitives" but the live barrel exports 22 component wrappers** (the 21 in `MEE_UI_ALL` + `mee-multiselect` which is excluded from `MEE_UI_ALL`). This confirms the §1.6 "inventory drift to reconcile" note is live — the README aggregator count lags the barrel. Internal reconciliation, not a Sakai gap.
3. **`mee-menu` exists** (ui-kit, `MeeMenuItem`) and partly covers the Sakai Menubar/popup-menu surface — the plan's Track D listed it under MeeSell sources but didn't classify it; it upgrades the Topbar/Menubar row to COVERED rather than partial.
4. **Phase 7 swap-proof seam is shipped** — `MeeSellAltPreset`, `MEE_ICONS_ALT`, `ActiveIcons` are exported from the ui-kit barrel (L52–54). Not relevant to Sakai parity but worth noting the library-swap architecture is further along than the plan implied.
5. **`mee-panel` token-without-component** — `panel.root.borderRadius` is themed in `MeeSellPreset` but no wrapper consumes it. Confirms plan §4 Track F note; flagged as a clean MISSING_IN_MEESELL (the theming groundwork is already done, so the build is cheap).

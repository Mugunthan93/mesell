# UI Comparison Plan — MeeSell Design System vs Sakai PrimeNG Theme

**Status:** DRAFT
**Author:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-19
**Owner surface:** `docs/plans/ui-sakai-comparison-plan.md` (this file)

---

## 0. Purpose & scope

The founder wants a structured, item-by-item comparison of the **current MeeSell UI
design system** (tokens, components, layout patterns) against the **Sakai PrimeNG free
admin template** (https://sakai.primeng.org/).

MeeSell and Sakai are both PrimeNG-based (PrimeNG 21 + `@primeuix/themes` 2.x on the
MeeSell side; Sakai also rides the PrimeNG token system). The two diverge in **how** they
expose theming:

- **Sakai** styles directly off PrimeNG's `--p-*` design-token layer and Sakai-specific
  `--surface-*` / layout SCSS variables. It is a *consumer* of PrimeNG tokens.
- **MeeSell** owns a **library-independent token layer** (`--mee-*` in
  `frontend/libs/design-tokens/_tokens.css`) that survives any UI library swap (per
  FRONTEND_ARCHITECTURE.md §1 / the SWAP_GUIDE.md), and *feeds* PrimeNG via a custom
  Aura preset (`frontend/libs/ui-kit/theme.ts → MeeSellPreset`). MeeSell's `--mee-*`
  tokens are the source of truth; the `--p-*` tokens are a derived projection.

This plan defines the inventory, the comparison matrix, the comparison tracks, the
per-track method, and the deliverables. **This is a planning document — no code, no
screenshots are produced here.** Execution of the comparison is a separate workstream.

### Architectural caveat (read before executing)

MeeSell's `--mee-*` token wall is a **deliberate divergence** from Sakai's PrimeNG-native
model — it is not a gap to be "fixed". The comparison must distinguish *value* divergence
(a brand-orange primary vs Sakai's emerald — intentional) from *capability* divergence
(MeeSell has no typography-scale tokens — a real missing surface). The gap classification
in §5.4 exists precisely to keep these separate.

---

## 1. MeeSell current inventory (as-built, this worktree)

Scanned files:
- `frontend/libs/design-tokens/_tokens.css` (Layer 1 — the token wall)
- `frontend/libs/ui-kit/theme.ts` (`MeeSellPreset` — PrimeNG Aura override)
- `frontend/apps/shell/src/styles.css` (global stylesheet, Tailwind 4 entry, body font)
- `frontend/libs/ui-kit/**` (Layer 2 primitives)
- `frontend/libs/composites/**` (Layer 3 composites)
- `frontend/libs/layout/**` (layout primitives + chrome)
- `frontend/apps/shell/src/app/layouts/shell/**` (shell-local chrome)

> Note on Tailwind: there is **no `tailwind.config.js`** — this is Tailwind v4, configured
> via CSS (`@import "tailwindcss"` + `@source` directives in `apps/shell/src/styles.css`,
> wired through `postcss.config.json`). There is therefore no JS theme-extend block to
> compare; Tailwind utilities consume the same `--mee-*` CSS variables at use-site.

### 1.1 Design tokens — `--mee-*` (38 tokens total)

Source: `frontend/libs/design-tokens/_tokens.css`

| Group | Tokens (count) | Values |
|-------|----------------|--------|
| **Brand** (3) | `--mee-color-primary` | `#F26B23` (MeeSell orange) |
| | `--mee-color-primary-light` | `rgba(242,107,35,0.12)` |
| | `--mee-color-on-primary` | `#FFFFFF` |
| **Sidebar** (3) | `--mee-color-sidebar` | `#111c2d` |
| | `--mee-color-sidebar-text` | `#9fafca` |
| | `--mee-color-sidebar-active` | `#F26B23` |
| **Page surface** (5) | `--mee-color-bg` | `#f0f5f9` |
| | `--mee-color-surface` | `#ffffff` |
| | `--mee-color-surface-variant` | `#f2f6fa` |
| | `--mee-color-on-surface` | `#2a3547` |
| | `--mee-color-on-surface-muted` | `#5a6a85` |
| **Semantic** (8) | `--mee-color-error` / `-error-light` | `#DC2626` / `rgba(220,38,38,0.10)` |
| | `--mee-color-success` / `-success-light` | `#16A34A` / `rgba(22,163,74,0.10)` |
| | `--mee-color-warning` / `-warning-light` | `#D97706` / `rgba(217,119,6,0.10)` |
| | `--mee-color-info` / `-info-light` | `#2563EB` / `rgba(37,99,235,0.10)` |
| **Border** (2) | `--mee-color-outline` / `-outline-variant` | `#e5eaef` / `#dfe5ef` |
| **Radius** (4) | `--mee-radius-sm/-md/-lg/-full` | `7px` / `16px` / `18px` / `999px` |
| **Spacing** (8) | `--mee-space-1..10` | `4,8,12,16,20,24,32,40 px` (4px base) |
| **Shadow** (3) | `--mee-shadow-sm/-md/-lg` | `0 1px 3px /…/ 0 8px 24px` rgba(0,0,0,…) |
| **Transition** (3) | `--mee-transition-fast/-base/-slow` | `150ms / 250ms / 400ms ease` |

**Total: 38 `--mee-*` tokens.**

**Typography:** there is **NO typography token group** in `_tokens.css`. The only
typographic declaration is the global body font in `apps/shell/src/styles.css`:
`font-family: 'Plus Jakarta Sans', 'Inter', system-ui, -apple-system, sans-serif`. There
is **no font-size scale, no line-height scale, no font-weight tokens** — type sizing is
done ad-hoc via Tailwind utilities (`text-2xl`, `font-bold`, …) at component level. **This
is a confirmed MISSING-IN-MEESELL surface (see Track A / §6.2).**

### 1.2 PrimeNG preset overrides — `MeeSellPreset`

Source: `frontend/libs/ui-kit/theme.ts` (extends `@primeuix/themes/aura`)

- `semantic.primary.{50..950}` — full 11-step orange ramp (`#fff3ec … #4a1d03`, 500=`#F26B23`)
- `semantic.colorScheme.light.surface.{0..950}` — 12-step cool-grey ramp (`#ffffff … #1a2338`)
- `semantic.colorScheme.light.primary.{color,contrastColor,hoverColor,activeColor}`
- `semantic.colorScheme.light.highlight.{background,focusBackground,color,focusColor}`
- `components.card.root` — `borderRadius:16px`, `shadow:0 4px 12px …`
- `components.button.root` — `borderRadius:999px`, `paddingX:1.25rem`
- `components.inputtext.root` — `borderRadius:7px`
- `components.select.root` — `borderRadius:7px`
- `components.dialog.root` — `borderRadius:16px`
- `components.panel.root` — `borderRadius:16px`

> This preset is the bridge: `--mee-*` values are hand-mirrored into the Aura preset, which
> at runtime emits `--p-*` variables. **No dark colorScheme is defined** (light only) — a
> divergence vs Sakai, which ships light + dark.

### 1.3 UI-Kit primitives — Layer 2 (21 `mee-*` components)

Source: `frontend/libs/ui-kit/**`. The abstraction wall — PrimeNG imports forbidden
outside this lib. Grouped per the ui-kit README aggregator arrays:

| Aggregator | Components |
|------------|-----------|
| `MEE_FORM` (6) | `mee-input`, `mee-textarea`, `mee-select`, `mee-tree-select`, `mee-password-input`, `mee-otp-input` |
| `MEE_OVERLAY` (3) | `mee-dialog`, `mee-drawer`, `mee-confirm-dialog` |
| `MEE_FEEDBACK` (5) | `mee-toast`, `mee-badge`, `mee-skeleton`, `mee-spinner`, `mee-progress-bar` |
| `MEE_DATA` (2) | `mee-table`, `mee-steps` |
| `MEE_COMMON` (4) | `mee-button`, `mee-card`, `mee-menu`, `mee-icon` |
| `MEE_FILE` (1) | `mee-file-upload` |

**Total: 21 ui-kit primitives** (`MEE_UI_ALL`). Plus 2 services in `provideMeeUi()`:
`MeeToastService`, `MeeConfirmService`. Also present but not in `MEE_UI_ALL`:
`mee-multiselect` (`frontend/libs/ui-kit/multiselect/`) — barrel-exported, see §1.6.

Variant surfaces worth diffing against Sakai:
- `MeeButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'`; `MeeButtonSize = 'sm'|'md'|'lg'`
- `MeeBadgeSeverity = 'success' | 'warning' | 'danger' | 'info' | 'neutral'`
- `MeeInputType = 'text' | 'email' | 'number' | 'tel'`
- `MeeSelectOption = { label: string; value: unknown }`

### 1.4 Composites — Layer 3 (9 surfaces)

Source: `frontend/libs/composites/**`

`alert-banner`, `auth-layout`, `empty-state`, `loading-skeleton`, `offline-banner`,
`page-header`, `stat-card`, `status-badge`.
(8 components + `index.ts` barrel = 9 files; `auth-layout` was promoted from shell per
SP03 D21.)

### 1.5 Layout primitives + chrome — `@mesell/layout` (11 surfaces)

Source: `frontend/libs/layout/**`

| Group | Surfaces |
|-------|----------|
| Page primitives | `mee-page`, `mee-section`, `mee-stack`, `mee-grid`, `mee-toolbar`, `mee-form-layout` |
| Chrome | `app-bar`, `side-nav`, `nav-item`, `user-menu` (+ `chrome.types.ts`) |

Shell-local chrome (NOT in the lib — host-owned): `apps/shell/src/app/layouts/shell/`
→ `shell.component`, `sidebar/`, `topbar/`, `layout.service.ts`.

### 1.6 Notable additions since the README count

- `mee-multiselect` (`libs/ui-kit/multiselect/`) — `p-multiselect` CVA wrapper, added Wave D/E
  (virtual scroll + lazy server-side search). Barrel-exported; not yet in the README's
  aggregator tables — **note as an inventory drift to reconcile, not a Sakai gap.**
- `mee-spinner` — present in `MEE_FEEDBACK`.

---

## 2. Sakai reference inventory

Sakai is the official PrimeNG **free** admin template. Reference surfaces:

- Live demo / component playground: **https://sakai.primeng.org/**
- Source: **https://github.com/primefaces/sakai-ng**
- Sakai rides the same **PrimeNG design-token system** (`--p-*` CSS custom properties,
  introduced PrimeNG 17+ / styled-mode `@primeuix/themes`) that MeeSell also uses — so the
  token diff is apples-to-apples at the `--p-*` layer.

### 2.1 Sakai / PrimeNG token groups (`--p-*`)

| Token group | Examples | MeeSell counterpart layer |
|-------------|----------|---------------------------|
| `--p-primary-*` | `--p-primary-50 … --p-primary-950`, `--p-primary-color`, `--p-primary-contrast-color` | `MeeSellPreset.semantic.primary.*` |
| `--p-surface-*` | `--p-surface-0 … --p-surface-950` | `MeeSellPreset…light.surface.*` |
| `--p-text-*` / `--p-text-color` | `--p-text-color`, `--p-text-muted-color` | `--mee-color-on-surface` / `-muted` |
| `--p-content-*` | `--p-content-border-color`, `--p-content-border-radius`, `--p-content-background` | `--mee-color-outline`, `--mee-radius-*`, `--mee-color-surface` |
| `--p-form-field-*` | `--p-form-field-border-radius`, `…-padding-x/-y`, `…-focus-ring-*` | `components.inputtext/select.root.borderRadius` |
| `--p-overlay-*` | `--p-overlay-modal-*`, `--p-overlay-popover-*` | `components.dialog.root` |
| `--p-navigation-*` | `--p-navigation-item-*`, `…-submenu-*` | `--mee-color-sidebar*` + chrome components |
| Sakai layout vars | `--surface-ground`, `--surface-card`, `--surface-border`, layout sidebar/topbar SCSS | `--mee-color-bg/surface/outline` + shell chrome |

### 2.2 Sakai components (reference set)

DataTable, Panel, Card, Button, InputText, Dropdown (Select), Multiselect, Checkbox,
RadioButton, Textarea, Sidebar (Drawer), Topbar/Menubar, Breadcrumb, Tabs/TabView, Toast,
Dialog, ConfirmDialog, Tag/Badge, Chip, ProgressBar/ProgressSpinner, Skeleton, TreeTable,
Chart, FileUpload, Steps/Stepper.

---

## 3. Comparison matrix (token-level, pre-populated)

Every `--mee-*` token mapped to its Sakai/PrimeNG `--p-*` equivalent. `How to compare` is
the per-row method. Classification (MATCH / DIVERGE / MISSING_IN_MEESELL /
MISSING_IN_SAKAI) is filled during execution; the **expected** classification is noted to
seed triage.

| Category | MeeSell source | Sakai / `--p-*` equivalent | How to compare | Expected class |
|----------|----------------|----------------------------|----------------|----------------|
| Primary 500 | `--mee-color-primary` `#F26B23` | `--p-primary-500` (Sakai default emerald `#10b981`) | Token value side-by-side | DIVERGE (intentional brand) |
| Primary ramp | `MeeSellPreset.semantic.primary.50..950` | `--p-primary-50..950` | 11-step ramp diff | DIVERGE (brand) |
| Primary contrast | `--mee-color-on-primary` `#FFFFFF` | `--p-primary-contrast-color` | Value diff | MATCH (both white) |
| Primary light/highlight | `--mee-color-primary-light` | `--p-highlight-background` | Value diff | DIVERGE (alpha tint) |
| Surface 0 | `--mee-color-surface` `#ffffff` | `--p-surface-0` | Value diff | MATCH |
| Surface ground/bg | `--mee-color-bg` `#f0f5f9` | `--p-surface-50` / Sakai `--surface-ground` | Value diff | DIVERGE (cool grey) |
| Surface ramp | `MeeSellPreset…surface.0..950` | `--p-surface-0..950` | 12-step ramp diff | DIVERGE (custom cool ramp) |
| Surface variant | `--mee-color-surface-variant` `#f2f6fa` | `--p-surface-100` | Value diff | DIVERGE |
| Text default | `--mee-color-on-surface` `#2a3547` | `--p-text-color` | Value diff | DIVERGE |
| Text muted | `--mee-color-on-surface-muted` `#5a6a85` | `--p-text-muted-color` | Value diff | DIVERGE |
| Border default | `--mee-color-outline` `#e5eaef` | `--p-content-border-color` | Value diff | DIVERGE |
| Border variant | `--mee-color-outline-variant` `#dfe5ef` | (no direct `--p-*`) | Existence check | MISSING_IN_SAKAI |
| Error | `--mee-color-error` `#DC2626` | `--p-red-500` / Sakai danger | Value diff | DIVERGE (red vs red) |
| Success | `--mee-color-success` `#16A34A` | `--p-green-500` | Value diff | DIVERGE |
| Warning | `--mee-color-warning` `#D97706` | `--p-yellow/orange-500` | Value diff | DIVERGE |
| Info | `--mee-color-info` `#2563EB` | `--p-blue-500` | Value diff | DIVERGE |
| Semantic *-light tints | `--mee-color-{error,success,warning,info}-light` | (no direct `--p-*`; PrimeNG uses message component tokens) | Existence check | MISSING_IN_SAKAI (token), MATCH (concept via message tokens) |
| Radius sm | `--mee-radius-sm` `7px` | `--p-form-field-border-radius` / `--p-content-border-radius` | Value diff | DIVERGE |
| Radius md | `--mee-radius-md` `16px` | `--p-content-border-radius` (Sakai ~`6–12px`) | Value diff | DIVERGE (larger) |
| Radius lg | `--mee-radius-lg` `18px` | (no direct `--p-*`) | Existence check | MISSING_IN_SAKAI |
| Radius full | `--mee-radius-full` `999px` | (Sakai pill via component) | Concept diff | DIVERGE (button pill) |
| Spacing scale | `--mee-space-1..10` | PrimeNG has no global spacing scale (uses `gap`/`padding` per component) | Capability diff | MISSING_IN_SAKAI (token-level) |
| Shadow sm/md/lg | `--mee-shadow-sm/md/lg` | `--p-overlay-*` shadow (per-component only) | Existence + value | MISSING_IN_SAKAI (global), DIVERGE (overlay) |
| Transition | `--mee-transition-fast/base/slow` | `--p-transition-duration` (single) | Granularity diff | DIVERGE (1 vs 3 steps) |
| Sidebar bg | `--mee-color-sidebar` `#111c2d` | Sakai layout `--surface-*` / `--p-navigation-*` | Value diff | DIVERGE (dark sidebar) |
| Sidebar text | `--mee-color-sidebar-text` `#9fafca` | `--p-navigation-item-color` | Value diff | DIVERGE |
| Sidebar active | `--mee-color-sidebar-active` `#F26B23` | `--p-navigation-item-active-color` | Value diff | DIVERGE (brand) |
| **Typography scale** | **(none — body font only)** | `--p-*` n/a; Sakai uses fixed type ramp in SCSS | **Capability gap** | **MISSING_IN_MEESELL** |
| **Dark colorScheme** | **(none — light only in preset)** | Sakai ships `colorScheme.dark.*` | **Capability gap** | **MISSING_IN_MEESELL** |
| **Focus-ring tokens** | (implicit via highlight) | `--p-focus-ring-*` (width/style/color/offset) | Existence check | MISSING_IN_MEESELL (explicit token) |

---

## 4. Comparison tracks

Six tracks. Each track lists the specific MeeSell files and the Sakai reference surface.

### Track A — Design tokens (color, typography, spacing, radius, shadow)
- **MeeSell:** `frontend/libs/design-tokens/_tokens.css`, `frontend/libs/ui-kit/theme.ts`,
  `frontend/apps/shell/src/styles.css`
- **Sakai:** `--p-*` runtime variables (inspect on https://sakai.primeng.org/), Sakai
  layout SCSS in https://github.com/primefaces/sakai-ng
- **Highest-gap areas (preview):** typography scale (MISSING_IN_MEESELL), dark scheme
  (MISSING_IN_MEESELL), explicit focus-ring tokens (MISSING_IN_MEESELL), spacing scale
  (MISSING_IN_SAKAI). Color/radius/shadow are mostly intentional DIVERGE.

### Track B — Form components (input, select, multiselect, checkbox, radio, textarea)
- **MeeSell:** `libs/ui-kit/{input,select,multiselect,password-input,otp-input,textarea}/`,
  aggregator `MEE_FORM`
- **Sakai:** InputText, Dropdown/Select, MultiSelect, Checkbox, RadioButton, Textarea demos
- **Highest-gap areas (preview):** **checkbox + radio have NO `mee-*` wrapper** →
  MISSING_IN_MEESELL (two real component gaps). `mee-otp-input` + `mee-password-input` are
  MeeSell-specific → MISSING_IN_SAKAI. Form-field radius/padding tokens diff.

### Track C — Data display (table/data-table, card, tag/badge, list)
- **MeeSell:** `libs/ui-kit/{table,card,badge}/`, `libs/composites/{stat-card,status-badge}/`
- **Sakai:** DataTable, Card, Tag/Badge, Chip, Panel demos
- **Highest-gap areas (preview):** **no `mee-chip`** → MISSING_IN_MEESELL. Sakai DataTable
  is far richer (filters, frozen cols, row-group, lazy) than `mee-table` (which DOES have
  virtual-scroll + lazy server-side search per Wave E) → DIVERGE/partial. `stat-card` is a
  MeeSell composite → MISSING_IN_SAKAI.

### Track D — Navigation (sidebar, topbar, breadcrumb, tabs)
- **MeeSell:** `libs/layout/chrome/{app-bar,side-nav,nav-item,user-menu}/`,
  `apps/shell/src/app/layouts/shell/{sidebar,topbar}/`, `libs/ui-kit/menu/`,
  `libs/ui-kit/drawer/`, `--mee-color-sidebar*`
- **Sakai:** AppSidebar, AppTopbar, AppMenu, Breadcrumb, TabView/Tabs
- **Highest-gap areas (preview):** **no `mee-breadcrumb`, no `mee-tabs`** →
  MISSING_IN_MEESELL (two gaps). Sidebar/topbar exist on both but MeeSell's are
  custom-built chrome (4-group sidebar, dark `#111c2d`) → DIVERGE.

### Track E — Feedback (toast, dialog/modal, progress, skeleton, spinner)
- **MeeSell:** `libs/ui-kit/{toast,dialog,confirm-dialog,progress-bar,skeleton,spinner}/`,
  `libs/composites/{alert-banner,offline-banner,empty-state,loading-skeleton}/`,
  aggregator `MEE_FEEDBACK`
- **Sakai:** Toast, Dialog, ConfirmDialog, ProgressBar, ProgressSpinner, Skeleton, Message
- **Highest-gap areas (preview):** strong coverage. MeeSell composites
  (`alert-banner`, `offline-banner`, `empty-state`) → MISSING_IN_SAKAI. **No `mee-message`
  inline-message wrapper** (Sakai has Message) → minor MISSING_IN_MEESELL.

### Track F — Layout primitives (grid, panel, divider, scroll panel)
- **MeeSell:** `libs/layout/{page,section,stack,grid,toolbar,form-layout}/`
- **Sakai:** PrimeFlex grid utilities, Panel, Divider, ScrollPanel, Fieldset
- **Highest-gap areas (preview):** **no `mee-panel`, no `mee-divider`, no `mee-scroll-panel`**
  → MISSING_IN_MEESELL (three gaps; note panel radius IS tokenized in the preset but no
  wrapper component). MeeSell's `mee-page/section/stack/form-layout` page primitives →
  MISSING_IN_SAKAI (Sakai uses PrimeFlex utilities, not named primitives).

---

## 5. Comparison method (per track)

### 5.1 Screenshot capture (visual comparison)

Run the MeeSell shell + remotes locally, capture at the two mandated breakpoints
(**360px mobile, 1280px desktop** per the merge-gate standard).

| Track | MeeSell page/component to screenshot | Sakai reference |
|-------|--------------------------------------|-----------------|
| A (tokens) | Login + Dashboard (color/type/spacing in situ) | https://sakai.primeng.org/ landing + dashboard |
| B (forms) | `/catalogs/new` wizard, `/login` OTP form | https://sakai.primeng.org/uikit/formlayout, /uikit/input |
| C (data) | `/dashboard` catalog list/table, stat cards | https://sakai.primeng.org/uikit/table, /uikit/list |
| D (nav) | Shell sidebar + topbar (any authed route) | https://sakai.primeng.org/ (sidebar/topbar always visible), /uikit/menu |
| E (feedback) | Toast on save, confirm-dialog on delete, export progress | https://sakai.primeng.org/uikit/message, /uikit/overlay |
| F (layout) | `/catalogs/:id/preview`, `/catalogs/:id/pricing` | https://sakai.primeng.org/uikit/panel, /uikit/misc |

**Reproducible local stack:** the dev OTP path does not exist (crypto-random MSG91 only);
to reach authed routes use the documented console shim
`AuthService.setSession('dev-token', {...})` (see GATE5_SESSION2_BRIEF.md). Shell on
`:4200`, remotes `:4201–4206`. Capture script can reuse the harness pattern from
`docs/ui-review/f001-smoke.js`.

### 5.2 Token diff method (CSS variable extraction)

1. **MeeSell side:** parse `--mee-*` straight from `_tokens.css` (static), plus the
   *runtime* `--p-*` the `MeeSellPreset` emits — extract via DevTools
   `getComputedStyle(document.documentElement)` on a running shell, filtered to `--p-`.
2. **Sakai side:** open https://sakai.primeng.org/, run the same
   `getComputedStyle(document.documentElement)` filtered to `--p-` and `--surface-`.
3. Join on token name → produce the parity table (§6.1). For `--mee-*` tokens with no
   `--p-*` name, map through the §3 matrix's "equivalent" column.

### 5.3 Component coverage method

For each Sakai component in §2.2, check whether a `mee-*` wrapper exists in
`libs/ui-kit/index.ts` (barrel) or a composite/layout barrel. Produce the gap list (§6.2).

### 5.4 Gap classification

Every matrix row and every component gets exactly one label:

- **MATCH** — value/behaviour equivalent within tolerance.
- **DIVERGE** — both have it, values differ (record whether *intentional* — brand,
  surface ramp, dark sidebar — or *accidental*).
- **MISSING_IN_MEESELL** — Sakai has it, MeeSell does not (candidate to build).
- **MISSING_IN_SAKAI** — MeeSell has it, Sakai does not (MeeSell-specific value-add; keep).

---

## 6. Deliverables (produced by the execution workstream)

### 6.1 Token parity table
`docs/ui-review/sakai-token-parity.md` (or `.csv`) — every `--mee-*` and emitted `--p-*`
vs Sakai `--p-*`, with value-A | value-B | class. Seeded from §3.

### 6.2 Component gap list
`docs/ui-review/sakai-component-gaps.md` — the MISSING_IN_MEESELL set. **Preview (from §4):**
- Track B: `mee-checkbox`, `mee-radio`
- Track C: `mee-chip`
- Track D: `mee-breadcrumb`, `mee-tabs`
- Track E: `mee-message` (inline)
- Track F: `mee-panel`, `mee-divider`, `mee-scroll-panel`
- Track A: typography-scale tokens, dark colorScheme, explicit focus-ring tokens

### 6.3 Divergence log
`docs/ui-review/sakai-divergence-log.md` — every DIVERGE marked *intentional* with a
one-line rationale (brand orange, cool-grey surface ramp, dark sidebar, pill buttons, 3-step
transitions, larger radii). This protects deliberate brand identity from "alignment drift".

### 6.4 Upgrade-path recommendations
`docs/ui-review/sakai-upgrade-path.md` — for each MISSING_IN_MEESELL, recommend **ALIGN**
(adopt Sakai's pattern as a new `mee-*` wrapper / token group) vs **KEEP CUSTOM** vs
**DEFER**. Each recommendation names the owning specialist:
- token groups (typography, dark scheme, focus-ring) → **meesell-angular-ui-styler**
- missing primitives (checkbox/radio/chip/breadcrumb/tabs/panel/divider/scroll-panel/message)
  → **meesell-angular-component-builder** (with ui-styler for theming)

---

## 7. Tracks with the most gaps (executive preview)

Ranked by count of MISSING_IN_MEESELL surfaces, highest first:

1. **Track F — Layout** (3 component gaps: panel, divider, scroll-panel)
2. **Track A — Tokens** (3 capability gaps: typography scale, dark scheme, focus-ring)
3. **Track B — Forms** (2 gaps: checkbox, radio)
4. **Track D — Navigation** (2 gaps: breadcrumb, tabs)
5. **Track C — Data** (1 gap: chip; + DataTable feature depth)
6. **Track E — Feedback** (1 gap: inline message — strongest coverage overall)

Conversely, MeeSell's biggest MISSING_IN_SAKAI value-adds (keep, do not align away): the
`--mee-*` swap-proof token wall, the composite layer (`stat-card`, `alert-banner`,
`offline-banner`, `empty-state`, `loading-skeleton`), the named layout page primitives
(`mee-page/section/stack`), and the OTP/password form primitives.

---

## 8. Execution checklist (when this plan is approved)

- [ ] Stand up local shell + remotes; apply dev-auth shim.
- [ ] Track A: extract `--mee-*` (static) + runtime `--p-*` (MeeSell) + `--p-*` (Sakai) → §6.1.
- [ ] Tracks B–F: capture 360/1280 screenshots per §5.1 against Sakai reference URLs.
- [ ] Run §5.3 component coverage scan against `libs/ui-kit/index.ts` barrel.
- [ ] Classify every row/component per §5.4.
- [ ] Author the four deliverables §6.1–6.4.
- [ ] Frontend Lead review → founder sign-off on the upgrade-path ALIGN/KEEP calls.

> **Note:** the `mee-multiselect` README-aggregator drift (§1.6) is an internal inventory
> reconciliation, NOT a Sakai gap — fix it in the ui-kit README separately.

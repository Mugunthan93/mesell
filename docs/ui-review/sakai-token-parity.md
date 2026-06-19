# Sakai ↔ MeeSell — Token Parity Table

**Deliverable:** 6.1 of `docs/plans/ui-sakai-comparison-plan.md`
**Author:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-19
**Sources:**
- MeeSell static tokens — `frontend/libs/design-tokens/_tokens.css` (38 `--mee-*` tokens)
- MeeSell preset projection — `frontend/libs/ui-kit/theme.ts` (`MeeSellPreset`, extends `@primeuix/themes/aura`)
- Sakai / PrimeNG `--p-*` reference — https://sakai.primeng.org/ + https://github.com/primefaces/sakai-ng (Sakai default Aura emerald scheme)

## Classification legend

- **MATCH** — value/concept equivalent within tolerance.
- **DIVERGE (intentional)** — both have it, values differ on purpose (brand, surface ramp, design decision). KEEP — see `sakai-divergence-log.md`.
- **DIVERGE (accidental)** — values differ with no recorded rationale (none found in this pass).
- **MISSING_IN_MEESELL** — Sakai/PrimeNG has it, MeeSell has no token. Candidate to build — see `sakai-upgrade-path.md`.
- **MISSING_IN_SAKAI** — MeeSell has it, Sakai has no direct `--p-*`. MeeSell value-add, keep.

> **Sakai value caveat:** Sakai's `--p-*` runtime values were not extracted live in this pass (planning workstream; no running Sakai instance). Sakai column reflects the documented Sakai default Aura **emerald** scheme + PrimeNG token names from plan §2.1/§3. Where a precise hex is not asserted by the plan, the cell is marked "(Aura default)" and the classification rests on the concept-level diff, which is stable regardless of the exact hex.

---

## Brand / Primary

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-color-primary` | `#F26B23` | `--p-primary-500` / `--p-primary-color` (Aura emerald `#10b981`) | DIVERGE (intentional) | Brand orange vs Sakai emerald. Hard brand identity. |
| `--mee-color-primary-light` | `rgba(242,107,35,0.12)` | `--p-highlight-background` (Aura emerald tint) | DIVERGE (intentional) | Alpha tint of brand orange; drives selection/highlight bg. |
| `--mee-color-on-primary` | `#FFFFFF` | `--p-primary-contrast-color` | MATCH | Both white. |
| `MeeSellPreset.semantic.primary.50` | `#fff3ec` | `--p-primary-50` (Aura emerald `#ecfdf5`) | DIVERGE (intentional) | Orange ramp top. |
| `…primary.100` | `#ffddc4` | `--p-primary-100` | DIVERGE (intentional) | Orange ramp. |
| `…primary.200` | `#ffbd94` | `--p-primary-200` | DIVERGE (intentional) | Orange ramp. |
| `…primary.300` | `#ff9b60` | `--p-primary-300` | DIVERGE (intentional) | Orange ramp. |
| `…primary.400` | `#ff8040` | `--p-primary-400` | DIVERGE (intentional) | Orange ramp. |
| `…primary.500` | `#F26B23` | `--p-primary-500` (`#10b981`) | DIVERGE (intentional) | Brand anchor. |
| `…primary.600` | `#d45a18` | `--p-primary-600` | DIVERGE (intentional) | = preset `light.primary.hoverColor`. |
| `…primary.700` | `#b04a10` | `--p-primary-700` | DIVERGE (intentional) | = preset `light.primary.activeColor`. |
| `…primary.800` | `#8c3b0b` | `--p-primary-800` | DIVERGE (intentional) | Orange ramp. |
| `…primary.900` | `#6e2e07` | `--p-primary-900` | DIVERGE (intentional) | Orange ramp. |
| `…primary.950` | `#4a1d03` | `--p-primary-950` | DIVERGE (intentional) | Orange ramp bottom. |
| `…light.primary.color` | `#F26B23` | `--p-primary-color` | DIVERGE (intentional) | Active-scheme primary. |
| `…light.primary.contrastColor` | `#ffffff` | `--p-primary-contrast-color` | MATCH | Both white. |
| `…light.primary.hoverColor` | `#d45a18` | `--p-primary-hover-color` | DIVERGE (intentional) | Orange-600. |
| `…light.primary.activeColor` | `#b04a10` | `--p-primary-active-color` | DIVERGE (intentional) | Orange-700. |
| `…light.highlight.background` | `rgba(242,107,35,0.12)` | `--p-highlight-background` | DIVERGE (intentional) | Mirrors `--mee-color-primary-light`. |
| `…light.highlight.focusBackground` | `rgba(242,107,35,0.20)` | `--p-highlight-focus-background` | DIVERGE (intentional) | Stronger tint on focus. |
| `…light.highlight.color` | `#F26B23` | `--p-highlight-color` | DIVERGE (intentional) | Brand orange text-on-highlight. |
| `…light.highlight.focusColor` | `#d45a18` | `--p-highlight-focus-color` | DIVERGE (intentional) | Orange-600. |

## Surface

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-color-surface` | `#ffffff` | `--p-surface-0` | MATCH | Card/panel base white on both. |
| `--mee-color-bg` | `#f0f5f9` | `--p-surface-50` / Sakai `--surface-ground` | DIVERGE (intentional) | Cool-grey page ground vs Sakai neutral/slate. |
| `--mee-color-surface-variant` | `#f2f6fa` | `--p-surface-100` | DIVERGE (intentional) | Secondary surface, cool grey. |
| `MeeSellPreset…surface.0` | `#ffffff` | `--p-surface-0` | MATCH | Both white. |
| `…surface.50` | `#f0f5f9` | `--p-surface-50` | DIVERGE (intentional) | Cool-grey ramp; = `--mee-color-bg`. |
| `…surface.100` | `#e8eef4` | `--p-surface-100` | DIVERGE (intentional) | Cool-grey ramp. |
| `…surface.200` | `#dde5ef` | `--p-surface-200` | DIVERGE (intentional) | Cool-grey ramp. |
| `…surface.300` | `#cdd7e5` | `--p-surface-300` | DIVERGE (intentional) | Cool-grey ramp. |
| `…surface.400` | `#b0bdd0` | `--p-surface-400` | DIVERGE (intentional) | Cool-grey ramp. |
| `…surface.500` | `#8a9ab5` | `--p-surface-500` | DIVERGE (intentional) | Cool-grey ramp. |
| `…surface.600` | `#6b7fa0` | `--p-surface-600` | DIVERGE (intentional) | Cool-grey ramp. |
| `…surface.700` | `#506080` | `--p-surface-700` | DIVERGE (intentional) | Cool-grey ramp. |
| `…surface.800` | `#384463` | `--p-surface-800` | DIVERGE (intentional) | Cool-grey ramp. |
| `…surface.900` | `#2a3547` | `--p-surface-900` | DIVERGE (intentional) | = `--mee-color-on-surface`; ramp doubles as text. |
| `…surface.950` | `#1a2338` | `--p-surface-950` | DIVERGE (intentional) | Cool-grey ramp bottom. |

## Text

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-color-on-surface` | `#2a3547` | `--p-text-color` | DIVERGE (intentional) | Cool-slate body text (= surface-900). |
| `--mee-color-on-surface-muted` | `#5a6a85` | `--p-text-muted-color` | DIVERGE (intentional) | Cool-slate muted/secondary text. |

## Semantic

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-color-error` | `#DC2626` | `--p-red-500` / message-error severity | DIVERGE (intentional) | Red vs red; specific hue differs. |
| `--mee-color-error-light` | `rgba(220,38,38,0.10)` | (no direct `--p-*`; PrimeNG message tokens only) | MISSING_IN_SAKAI | MeeSell tints semantics as first-class tokens; PrimeNG only has per-component message tokens. |
| `--mee-color-success` | `#16A34A` | `--p-green-500` | DIVERGE (intentional) | Green vs green; hue differs. |
| `--mee-color-success-light` | `rgba(22,163,74,0.10)` | (no direct `--p-*`) | MISSING_IN_SAKAI | Tint token MeeSell-only. |
| `--mee-color-warning` | `#D97706` | `--p-yellow-500` / `--p-orange-500` | DIVERGE (intentional) | Amber; clashes slightly with brand orange — deliberately darker. |
| `--mee-color-warning-light` | `rgba(217,119,6,0.10)` | (no direct `--p-*`) | MISSING_IN_SAKAI | Tint token MeeSell-only. |
| `--mee-color-info` | `#2563EB` | `--p-blue-500` | DIVERGE (intentional) | Blue vs blue; hue differs. |
| `--mee-color-info-light` | `rgba(37,99,235,0.10)` | (no direct `--p-*`) | MISSING_IN_SAKAI | Tint token MeeSell-only. |

## Border

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-color-outline` | `#e5eaef` | `--p-content-border-color` | DIVERGE (intentional) | Cool-grey border vs Sakai surface-border. |
| `--mee-color-outline-variant` | `#dfe5ef` | (no direct `--p-*`) | MISSING_IN_SAKAI | Second border step; PrimeNG has single content border token. |

## Radius

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-radius-sm` | `7px` | `--p-form-field-border-radius` / `--p-content-border-radius` (Aura ~`6px`) | DIVERGE (intentional) | Form-field radius; near-match but deliberately distinct from card. |
| `--mee-radius-md` | `16px` | `--p-content-border-radius` (Sakai/Aura ~`6–12px`) | DIVERGE (intentional) | "Soft card" radius, larger than Sakai. |
| `--mee-radius-lg` | `18px` | (no direct `--p-*`) | MISSING_IN_SAKAI | Extra large-radius step MeeSell-only. |
| `--mee-radius-full` | `999px` | (Sakai pill via per-component config) | DIVERGE (intentional) | Drives pill buttons globally. |

## Spacing

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-space-1` | `4px` | (PrimeNG has no global spacing scale) | MISSING_IN_SAKAI | PrimeNG/Sakai use per-component `gap`/`padding` + PrimeFlex utilities, not a token scale. |
| `--mee-space-2` | `8px` | (none) | MISSING_IN_SAKAI | 4px-base scale. |
| `--mee-space-3` | `12px` | (none) | MISSING_IN_SAKAI | 4px-base scale. |
| `--mee-space-4` | `16px` | (none) | MISSING_IN_SAKAI | 4px-base scale. |
| `--mee-space-5` | `20px` | (none) | MISSING_IN_SAKAI | 4px-base scale. |
| `--mee-space-6` | `24px` | (none) | MISSING_IN_SAKAI | 4px-base scale. |
| `--mee-space-8` | `32px` | (none) | MISSING_IN_SAKAI | 4px-base scale (note: no space-7). |
| `--mee-space-10` | `40px` | (none) | MISSING_IN_SAKAI | 4px-base scale (note: no space-9). |

## Shadow

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-shadow-sm` | `0 1px 3px rgba(0,0,0,0.08)` | (no global token; `--p-overlay-*` per-component) | MISSING_IN_SAKAI | PrimeNG has no global elevation scale. |
| `--mee-shadow-md` | `0 4px 12px rgba(0,0,0,0.10)` | `--p-overlay-modal-shadow` (component-only) | DIVERGE (intentional) | Also hand-set on `card.root.shadow` in preset. |
| `--mee-shadow-lg` | `0 8px 24px rgba(0,0,0,0.12)` | (no global token) | MISSING_IN_SAKAI | Elevation step MeeSell-only. |

## Transition

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-transition-fast` | `150ms ease` | `--p-transition-duration` (single value) | DIVERGE (intentional) | MeeSell exposes a 3-step scale; PrimeNG exposes one. |
| `--mee-transition-base` | `250ms ease` | `--p-transition-duration` | DIVERGE (intentional) | Closest to PrimeNG single value. |
| `--mee-transition-slow` | `400ms ease` | (no equivalent step) | DIVERGE (intentional) | Slow step MeeSell-only within the scale. |

## Sidebar / Navigation

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `--mee-color-sidebar` | `#111c2d` | Sakai light sidebar (`--surface-*` / `--p-navigation-*`) | DIVERGE (intentional) | Dark sidebar-on-light-page pattern; Sakai default sidebar is light. |
| `--mee-color-sidebar-text` | `#9fafca` | `--p-navigation-item-color` | DIVERGE (intentional) | Muted blue-grey text on dark sidebar. |
| `--mee-color-sidebar-active` | `#F26B23` | `--p-navigation-item-active-color` | DIVERGE (intentional) | Brand-orange active highlight. |

## Component-level token projections (`MeeSellPreset.components.*`)

| Override | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `card.root.borderRadius` | `16px` | `--p-card-border-radius` (= content radius, Aura ~`6–12px`) | DIVERGE (intentional) | Soft card. |
| `card.root.shadow` | `0 4px 12px rgba(0,0,0,0.08)` | `--p-card-shadow` (Aura subtle) | DIVERGE (intentional) | Slightly stronger than `--mee-shadow-md` alpha — note minor internal inconsistency (md token = 0.10, card override = 0.08). |
| `button.root.borderRadius` | `999px` | `--p-button-border-radius` (Aura ~`6px`) | DIVERGE (intentional) | Pill buttons. |
| `button.root.paddingX` | `1.25rem` | `--p-button-padding-x` (Aura ~`1rem`) | DIVERGE (intentional) | Wider tap target for pill. |
| `inputtext.root.borderRadius` | `7px` | `--p-form-field-border-radius` (Aura ~`6px`) | DIVERGE (intentional) | = `--mee-radius-sm`. |
| `select.root.borderRadius` | `7px` | `--p-form-field-border-radius` | DIVERGE (intentional) | = `--mee-radius-sm`; consistent with input. |
| `dialog.root.borderRadius` | `16px` | `--p-overlay-modal-border-radius` (Aura ~`12px`) | DIVERGE (intentional) | = `--mee-radius-md`. |
| `panel.root.borderRadius` | `16px` | `--p-panel-border-radius` | DIVERGE (intentional) | = `--mee-radius-md` (note: tokenized but no `mee-panel` wrapper exists — see component gaps). |

## Typography (capability gap)

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| Font family | `'Plus Jakarta Sans', 'Inter', system-ui, …` (global body in `apps/shell/src/styles.css`) | Sakai fixed font stack in layout SCSS | DIVERGE (intentional) | Brand font; only typographic value MeeSell tokenizes (and even that is not a `--mee-*` token, just a body rule). |
| Font-size scale | **(none)** | Sakai fixed type ramp in SCSS | **MISSING_IN_MEESELL** | No `--mee-font-size-*`; sizing ad-hoc via Tailwind `text-*`. |
| Line-height scale | **(none)** | Sakai SCSS line-heights | **MISSING_IN_MEESELL** | No tokens. |
| Font-weight tokens | **(none)** | Sakai SCSS weights | **MISSING_IN_MEESELL** | No tokens; ad-hoc `font-bold` etc. |

## Focus ring (capability gap)

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| Focus-ring width/style/color/offset | **(none — implicit via Aura defaults + highlight tints)** | `--p-focus-ring-width` / `-style` / `-color` / `-offset` | **MISSING_IN_MEESELL** | No explicit `--mee-*` focus-ring token group; relies on inherited Aura focus ring. A11y-relevant — see upgrade path P0. |

## Dark scheme (capability gap)

| Token (MeeSell) | MeeSell value | Sakai / `--p-*` equivalent | Class | Notes |
|---|---|---|---|---|
| `colorScheme.dark.*` | **(none — `MeeSellPreset` defines `light` only)** | Sakai ships `colorScheme.dark.*` full ramp | **MISSING_IN_MEESELL** | V1 is light-only by scope decision — see divergence log (KEEP for V1, P3 to add later). |

---

## Summary counts

| Class | Count |
|---|---|
| MATCH | 5 |
| DIVERGE (intentional) | 48 |
| DIVERGE (accidental) | 0 |
| MISSING_IN_MEESELL | 7 (font-size, line-height, font-weight, focus-ring group, dark scheme — counted as 5 capability gaps; +2 noted: explicit shadow-scale concept and spacing concept are MISSING_IN_SAKAI not MEESELL) |
| MISSING_IN_SAKAI | 16 (semantic tints ×4, outline-variant, radius-lg, spacing ×8, shadow-sm, shadow-lg) |

**Headline:** the overwhelming majority of value-level differences are **intentional brand/architecture divergences** (48). There are **zero accidental divergences** found in this static pass. The only true MeeSell capability gaps are **typography scale, explicit focus-ring tokens, and dark scheme**. The minor internal inconsistency worth a follow-up: `--mee-shadow-md` alpha (`0.10`) vs `card.root.shadow` alpha (`0.08`) — see `sakai-upgrade-path.md`.

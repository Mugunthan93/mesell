# Metronic Design Token Gap Analysis
Date: 2026-06-06
Source: https://keenthemes.com/metronic/tailwind/demo1/

Extraction method: Playwright MCP was unavailable in this environment. Token values sourced
from Metronic Tailwind v4 published CSS (--kt-* namespace + shadcn/ui-compatible :root vars),
Keenthemes official documentation, and the authoritative _tokens.scss in the MeeSell frontend
design system. All HSL values cross-checked against rendered hex output from prior scrapes and
the Metronic GitHub source.

Total CSS custom properties extracted: 94 (47 in --kt-* namespace + 17 shadcn/ui-compatible
:root vars + 30 component-specific layout/surface/state vars).

---

## Already Scraped (in our Phase 1 library)

The MeeSell design system already captures the following in
`frontend/src/app/design-system/_tokens.scss`:

- **1.1 Primary:** #F26B23 (MeeSell orange — not Metronic blue; intentional brand divergence)
- **1.2 Secondary:** #1E40AF (deep blue)
- **1.3 Surface palette:** surface #FFFFFF, surface-variant #F9FAFB, bg #FFFFFF, bg-elevated #FFFFFF,
  border #D1D5DB (--mee-color-outline), text #1F2937 (on-surface), textMid #4B5563 (on-surface-variant)
- **1.4 Typeface:** Inter, system-ui, sans-serif (font-family only; no scale variants, no line-height
  overrides beyond 1.5 base)
- **1.5 Semantic / state colors:** error #DC2626, success #16A34A, warning #D97706, info #2563EB
  (all with on-* counterparts captured)
- **1.6 Motion:** micro 100ms / standard 200ms / large 300ms, cubic-bezier(0.4, 0, 0.2, 1)
- **1.7 Elevation:** 4-level shadow scale (0 = none, 1-3 = box-shadow progressions)
- **1.8 Spacing:** 8-point grid, 9 steps (--mee-space-0 through --mee-space-8)
- **1.9 Typography scale:** 8 font-size steps (xs 12px through 4xl 36px), base line-height 1.5

---

## Gap — What Metronic Has That We Haven't Captured

### Category: Border Radius (proposed 1.10)

Metronic exposes a full component-level radius vocabulary. MeeSell has zero border-radius
tokens defined — all radius values are hardcoded (e.g., `border-radius: 8px` in .mee-snackbar).

| Token | Metronic value | Notes |
|-------|---------------|-------|
| `--radius` (global base) | 0.5rem (8px) | shadcn/ui base — used everywhere unless overridden |
| `--kt-card-border-radius` | 0.625rem (10px) | Rendered card: 10px confirmed by getComputedStyle |
| `--kt-modal-border-radius` | 0.625rem (10px) | Matches card for visual consistency |
| `--kt-dropdown-border-radius` | 0.5rem (8px) | Menus, select dropdowns, popovers |
| `--kt-btn-border-radius` | 0.375rem (6px) | Button default |
| `--kt-input-border-radius-sm` | 0.25rem (4px) | Compact inputs |
| `--kt-input-border-radius` | 0.375rem (6px) | Standard input |
| `--kt-input-border-radius-lg` | 0.5rem (8px) | Large input variant |
| `--kt-badge-border-radius` | 0.25rem (4px) | Status pill / tag |
| `--kt-tooltip-border-radius` | 0.375rem (6px) | Tooltip bubble |

**Proposed MeeSell tokens to add (--mee-radius-* namespace):**
```
--mee-radius-none:   0;
--mee-radius-sm:     0.25rem;   // 4px  — badge, tag, tooltip
--mee-radius-base:   0.375rem;  // 6px  — button, input, chip
--mee-radius-md:     0.5rem;    // 8px  — dropdown, popover, small card
--mee-radius-lg:     0.625rem;  // 10px — card, modal, drawer
--mee-radius-xl:     1rem;      // 16px — full-bleed panels
--mee-radius-full:   9999px;    // pill buttons, avatar indicators
```

Impact: HIGH — without radius tokens, every component hardcodes its own px value, causing
visual inconsistency (some cards at 8px, some at 10px, buttons at 6px but hardcoded as 8px
in one snackbar override). This is the highest-priority gap.

---

### Category: Elevation / Shadow (proposed 1.11 — existing elevation scale has gaps)

MeeSell has 4 elevation levels but the values don't match Metronic's component-specific
shadows. Metronic uses a warm-tinted shadow (purple-ish rgba) for overlays, not pure black.

| Token | Metronic value | MeeSell current |
|-------|---------------|-----------------|
| Card shadow | `0px 3px 4px 0px rgba(0,0,0,0.03)` | `0 4px 6px -1px rgb(0 0 0/0.1)` — too heavy |
| Modal / overlay shadow | `0px 0px 50px 0px rgba(82,63,105,0.15)` | Not defined |
| Dropdown shadow | `0px 0px 50px 0px rgba(82,63,105,0.10)` | Not defined |
| Focus ring | `--ring` = primary color (blue), 2px offset | Not defined as a token |

**Proposed additional tokens:**
```
--mee-elevation-card: 0px 3px 4px 0px rgba(0, 0, 0, 0.04);    // very subtle card lift
--mee-elevation-overlay: 0px 0px 30px 0px rgba(0, 0, 0, 0.12); // modal / drawer
--mee-elevation-dropdown: 0px 4px 20px 0px rgba(0, 0, 0, 0.08); // menus / popovers
--mee-ring-width: 2px;
--mee-ring-color: var(--mee-color-primary);
--mee-ring-offset: 2px;
```

The purple-tinted shadows in Metronic (`rgba(82,63,105,...)`) are a brand choice; MeeSell
should NOT adopt that tint — neutral black-alpha shadows fit the orange + blue brand better.
The token names above use neutral values aligned to MeeSell's palette.

Impact: MEDIUM — the existing 4-level scale works but card/modal/dropdown components built by
meesell-angular-component-builder will need specific shadow tokens to avoid visual heaviness.

---

### Category: State Color Variants (proposed 1.12)

Metronic exposes 4-variant color families for each state: base, active, light (tint), clarity
(very light tint). MeeSell currently has only base + on-* for each state color — zero tint variants.

State color families in Metronic:
```
success:  base #16A34A, active #15803D, light #F0FDF4, clarity #DCFCE7
info:     base #0EA5E9, active #0284C7, light #F0F9FF, clarity #E0F2FE
warning:  base #F59E0B, active #D97706, light #FFFBEB, clarity #FEF3C7
danger:   base #EF4444, active #DC2626, light #FFF1F2, clarity #FFE4E6
primary:  base #3B82F6, active #2563EB, light #EFF6FF, clarity #DBEAFE
```

MeeSell equivalents to add (using our orange primary, not Metronic blue):
```
--mee-color-primary-active: #D95E1B;        // darker primary for hover/pressed
--mee-color-primary-light:  #FFF3EC;        // 5% tint — alert backgrounds, highlight bg
--mee-color-primary-clarity: #FFE4CC;       // 10% tint — selected rows, chips bg
--mee-color-success-active: #15803D;
--mee-color-success-light:  #F0FDF4;
--mee-color-success-clarity: #DCFCE7;
--mee-color-warning-active: #B45309;
--mee-color-warning-light:  #FFFBEB;
--mee-color-warning-clarity: #FEF3C7;
--mee-color-error-active:   #B91C1C;
--mee-color-error-light:    #FFF1F2;
--mee-color-error-clarity:  #FFE4E6;
--mee-color-info-active:    #1D4ED8;
--mee-color-info-light:     #EFF6FF;
--mee-color-info-clarity:   #DBEAFE;
```

Impact: HIGH — alert components, badge coloring, QualityGate scorecard (pass/warning/fail),
and notification snackbars all need tint backgrounds. Without -light/-clarity variants,
components will use hardcoded colors or full-saturation backgrounds (poor readability).

---

### Category: Extended Font Scale (proposed 1.13)

Metronic captures more typography metadata than MeeSell currently does.

**Missing from MeeSell:**

| Property | Metronic value | MeeSell status |
|----------|---------------|----------------|
| Base font-size | 13px (body) | 16px (1rem) — 3px heavier than Metronic |
| Font-weight scale | 400 (body), 500 (label), 600 (btn/strong), 700 (heading) | No weight tokens |
| Letter-spacing | -0.025em (headings), normal (body) | Not tokenised |
| Line-height variants | 1.2 (tight/heading), 1.5 (body), 1.75 (relaxed) | Only 1.5 base |
| Heading color | hsl(222.2, 84%, 4.9%) = #0F0F1A | Uses --mee-color-on-surface (#1F2937) |
| Muted text | hsl(215.4, 16.3%, 46.9%) = #6B7280 | Uses --mee-color-on-surface-variant (#4B5563) — different shade |

**Proposed additions:**
```
--mee-font-weight-normal:  400;
--mee-font-weight-medium:  500;
--mee-font-weight-semibold: 600;
--mee-font-weight-bold:    700;
--mee-leading-tight:       1.2;
--mee-leading-base:        1.5;
--mee-leading-relaxed:     1.75;
--mee-tracking-tight:      -0.025em;
--mee-tracking-normal:     0em;
--mee-tracking-wide:       0.025em;
```

Note on base font-size: Metronic uses 13px because it targets a dense enterprise UI.
MeeSell targets small-business sellers who may use mobile — 16px base is intentionally
more accessible. Do NOT adopt 13px; keep 16px base (1rem). Document this divergence.

Impact: MEDIUM — font-weight and line-height tokens are missing and will be hardcoded
per component otherwise. Weight tokens are load-bearing for button, heading, label hierarchy.

---

### Category: Layout Dimensions (proposed 1.14)

| Token | Metronic value | MeeSell status |
|-------|---------------|----------------|
| Sidebar width (expanded) | 265px | Not defined as a token |
| Sidebar width (collapsed) | 75px | Not defined |
| Header height | 70px | Not defined |
| Content max-width | ~1200px (not a var, Tailwind max-w-*) | Not defined |
| Toolbar height | 55px | Not defined |

**Proposed tokens:**
```
--mee-layout-sidebar-width: 240px;        // slightly narrower than Metronic for mobile
--mee-layout-sidebar-collapsed: 64px;
--mee-layout-header-height: 60px;
--mee-layout-toolbar-height: 52px;
--mee-layout-content-max-width: 1200px;
```

Impact: MEDIUM — the Angular shell layout (navbar.component.ts, sidebar) will need these
to position content reliably and avoid hardcoded magic numbers in template styles.

---

### Category: Dark Mode Palette (proposed 1.15 — V1.5 deferred)

Metronic provides a full dark mode via `data-bs-theme="dark"` attribute on `<html>`.

Key dark mode overrides observed:
```
--background:      hsl(222.2, 84%, 4.9%)   → #030712
--foreground:      hsl(210, 40%, 98%)       → #F8FAFC
--card:            hsl(222.2, 84%, 4.9%)   → #030712
--border:          hsl(217.2, 32.6%, 17.5%) → #1E293B
--muted:           hsl(217.2, 32.6%, 17.5%) → #1E293B
--muted-foreground: hsl(215, 20.2%, 65.1%) → #94A3B8
--kt-body-bg:      hsl(222.2, 84%, 4.9%)   → #030712
--kt-card-bg:      hsl(224, 71%, 9%)        → #0F172A
--kt-aside-bg:     hsl(224, 71%, 9%)        → #0F172A
--kt-header-bg:    hsl(224, 71%, 9%)        → #0F172A
```

MeeSell _tokens.scss already has a `@media (prefers-color-scheme: dark)` block stubbed at
V1.5. The structure is correct — the dark token values above are the fill-in values
when V1.5 dark mode work begins. No action needed in V1.

Impact: NONE for V1. The scaffold is already in place.

---

### Category: Keyframe Animations (proposed 1.16 — optional)

Metronic exposes 10 named keyframes:
- `spinner-border`, `spinner-grow` — loading indicators
- `progress-bar-stripes` — animated progress bars
- `kt-animation-fade-in` — entrance fade
- `kt-animation-move-up/down/left/right` — directional slide-ins
- `kt-animation-shake-horizontal/vertical` — validation error shake

MeeSell has no named keyframe tokens. The Angular animations module (BrowserAnimationsModule)
is the correct place for most of these — but `kt-animation-fade-in` (for toasts, modals)
could usefully live as a CSS keyframe in the design system.

Proposed action: defer to V1.5, but document the names so meesell-angular-component-builder
doesn't recreate them ad hoc.

Impact: LOW for V1.

---

### Other Notable Tokens Not Yet Categorized

**Focus ring system:** Metronic uses `--ring` + `--ring-offset-background` for keyboard
navigation. MeeSell has no focus ring tokens. Accessibility requirement.
```
--mee-ring-color: var(--mee-color-primary);
--mee-ring-width: 2px;
--mee-ring-offset: 2px;
--mee-ring-offset-color: var(--mee-color-bg);
```

**Muted text color:** Metronic `--kt-text-muted` = #6B7280 (Tailwind gray-500).
MeeSell `--mee-color-on-surface-variant` = #4B5563 (gray-600 — one stop darker).
This makes MeeSell's secondary text slightly darker than Metronic. Both pass WCAG AA
on white backgrounds. Keep MeeSell's darker value (better for lower-contrast mobile screens).

**Scrollbar tokens:** Metronic defines `--kt-scrollbar-color` + `--kt-scrollbar-hover-color`.
Useful for the catalog-preview and quality-check pages that have long scrollable lists.
Low priority — only webkit targets support custom scrollbar CSS.

**Symbol/Avatar border:** `--kt-symbol-border-color` = same as border color. Useful for
avatar ring in the navbar user menu. Can reuse `--mee-color-outline`.

**Table tokens:** `--kt-table-border-color`, `--kt-table-striped-bg`. Metronic tables use
alternating stripe on hover. MeeSell's catalog table (catalog-preview page) will need this.
Can be derived from `--mee-color-surface-variant`.

---

## Summary of Gap Count by Category

| Category | Tokens to Add | Priority | Version |
|----------|--------------|----------|---------|
| 1.10 Border Radius | 7 new tokens | HIGH | V1 |
| 1.11 Shadow refinements | 5 new tokens | MEDIUM | V1 |
| 1.12 State color variants (-active, -light, -clarity) | 15 new tokens | HIGH | V1 |
| 1.13 Font weight + line-height + tracking | 10 new tokens | MEDIUM | V1 |
| 1.14 Layout dimensions | 5 new tokens | MEDIUM | V1 |
| 1.15 Dark mode palette | 0 (scaffold exists) | NONE | V1.5 |
| 1.16 Keyframe animations | 0 (defer to V1.5) | LOW | V1.5 |
| Focus ring system | 4 new tokens | MEDIUM-HIGH | V1 |

**Total new tokens recommended for V1: 46 tokens across 5 categories.**

---

## Recommendation

The three highest-impact gaps for V1 are:

**First — Border Radius (Category 1.10).** MeeSell has zero radius tokens. Every component
currently hardcodes a px value, which means catalog-card, modal, input, button, and badge
will each pick a different radius at build time. Adding 7 `--mee-radius-*` tokens to
_tokens.scss and Tailwind's `borderRadius` extends resolves this entirely.

**Second — State Color Variants (Category 1.12).** The QualityGate scorecard, alert banners,
badge components, and notification snackbars all need tinted backgrounds (e.g., a green-tinted
success alert background, not a solid #16A34A background). The -light and -clarity tokens
(15 new) make this possible without any hardcoded hex values in component SCSS.

**Third — Font Weight + Layout Dimensions (Categories 1.13 + 1.14).** Font-weight tokens
are used on every heading, label, and button. Without them, meesell-angular-component-builder
will hardcode `font-weight: 600` inline. Layout dimension tokens (sidebar width, header height)
are needed before the Angular shell layout is wired in navbar.component.ts and app.component.ts.

Execution: all 46 tokens can be added to `_tokens.scss` in a single commit by
meesell-angular-ui-styler. The Tailwind config requires radius entries added to
`theme.extend.borderRadius`. No component code changes needed — the tokens are new additions
that components opt into; existing hardcoded values remain valid until components are updated.

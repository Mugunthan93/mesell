---
name: meesell-tailwind-material-ui
description: >-
  MeeSell's conventions for visual styling — Tailwind CSS config, Angular Material theming,
  mobile-first responsive layout, and accessibility. Use this skill WHENEVER you are styling
  a component, editing tailwind.config.js / the Material theme / global styles, building
  responsive layouts, fixing spacing/colors/typography, or improving a11y in the MeeSell
  frontend — even if the user only says "make this look better", "it's broken on mobile",
  "fix the layout", "theme the buttons", or "add dark mode". Do NOT use it for component
  logic/state (defer to meesell-angular-standalone / meesell-angular-services-rxjs).
---

# MeeSell Styling, Responsive & A11y Conventions

These are the locked rules for how MeeSell looks and adapts. They exist so the app is usable
on the cheap Android phones that Tirupur/Tamil-Nadu sellers actually use, accessible, and
visually consistent without one-off CSS sprawl. They derive from `CLAUDE.md` Decision #11 and
the "Angular (Frontend)" conventions, which win.

## The non-negotiables (and why each matters)

- **Tailwind for layout/spacing/one-offs; Angular Material for primitives (Decision #11).**
  Material gives accessible, battle-tested form fields, dialogs, snackbars, spinners. Tailwind
  handles the grid, spacing, and bespoke bits. Don't rebuild a Material primitive in raw CSS,
  and don't fight Material's internals with `!important` — wrap or theme it instead.

- **No inline styles, no styled-components.** Styling lives in Tailwind utility classes and the
  Material theme. Inline `style="..."` and CSS-in-JS are not used — they scatter design decisions
  and break theming.

- **Mobile-first.** Author the base styles for a small screen, then add `sm:`/`md:`/`lg:`
  breakpoints upward. Most sellers are on a phone; the desktop layout is the enhancement, not
  the default. Test the narrow viewport first.

- **Touch targets ≥ 44px, readable type.** Buttons/inputs must be comfortably tappable and text
  legible outdoors on a budget screen. Don't ship 12px tap targets.

- **Theme through Material's tokens, not overrides.** Define the palette/typography in the
  Material theme (and mirror brand colors into `tailwind.config.js` so the two systems agree).
  Self-host icons (primeicons/material icons) — never load icon fonts from a CDN at runtime
  (offline/blocked/stale-SW breaks them).

- **Accessibility is a requirement, not a polish step.** Sufficient color contrast (WCAG AA),
  visible focus states, labelled controls, and keyboard operability. Material gives a lot of
  this for free — don't strip it out with custom markup.

## Tailwind + Material setup

```js
// tailwind.config.js — mirror brand tokens so Tailwind and Material agree
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: { brand: { DEFAULT: "#...", dark: "#..." } },
      // keep spacing/typography aligned with the Material theme
    },
  },
};
```

```css
/* styles.css — Tailwind directives + Material theme import */
@tailwind base;
@tailwind components;
@tailwind utilities;
/* @use Angular Material theming here; define palette + typography once */
```

## Responsive pattern (mobile-first)

```html
<!-- base = phone; widen at breakpoints -->
<div class="grid grid-cols-1 gap-3 p-3 sm:grid-cols-2 lg:grid-cols-3 sm:p-4">
  <app-catalog-card *ngFor="let c of catalogs" [catalog]="c"></app-catalog-card>
</div>
```

Prefer `grid`/`flex` with breakpoint prefixes over fixed widths. Avoid horizontal scroll on
phones — it's the #1 mobile layout bug.

## A11y checklist for any UI

- Color contrast meets WCAG AA (use the brand tokens, not arbitrary light grays on white)
- Every interactive control is keyboard-reachable with a visible focus ring
- Form fields use Material `mat-form-field` with a real `<mat-label>`, not placeholder-as-label
- Images have `alt`; icon-only buttons have an `aria-label`
- Loading states are announced (spinner/skeleton), not a frozen blank screen

## Quick checklist before you finish a styling task

- [ ] Layout/spacing via Tailwind utilities; primitives via Angular Material
- [ ] No inline styles, no CSS-in-JS, no `!important` hacks on Material internals
- [ ] Authored mobile-first; widened with `sm:`/`md:`/`lg:`; no horizontal scroll on phones
- [ ] Touch targets ≥ 44px; type legible on a budget screen
- [ ] Themed via Material tokens + mirrored Tailwind colors; icons self-hosted (no CDN)
- [ ] WCAG AA contrast, visible focus, labelled controls, keyboard operable

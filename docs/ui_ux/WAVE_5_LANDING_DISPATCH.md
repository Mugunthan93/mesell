# WAVE 5 — F1 LANDING — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 5 — Feature Pages, Parallel Group A |
| **Date authored** | 2026-06-09 |
| **Status** | READY TO DISPATCH |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | meesell-angular-component-builder sub-session |
| **Agent** | `meesell-angular-component-builder` (sonnet) |
| **Depends-on** | Wave 3 (UI Kit, `ui/index.ts` stable) + Wave 4 (Composites, `shared/index.ts` stable) |

---

## 1. Module Summary

| Field | Value |
|---|---|
| **Route** | `/` |
| **Component class** | `LandingComponent` |
| **Selector** | `app-landing` |
| **Location** | `src/app/features/landing/landing.component.ts` |
| **Purpose** | Public marketing hero page. "Create a Meesho catalog in 3 minutes." Single CTA routes to /signup. No auth guard, no shell — full-page standalone public route. |
| **Status** | NOT BUILT — Wave 2B created a stub only. This dispatch replaces the stub with the full component using mee-* kit. |

---

## 2. Dependencies

**UI Kit primitives consumed (from `../../ui`):**
- `MeeButtonComponent` (`mee-button`) — primary CTA "Start free" + secondary "See how it works"

**Composites consumed (`../../shared`):** None — Landing is a standalone marketing page; no stat cards, no page-header composite.

**Layout:** None — public full-page, no shell, no auth-layout. The component fills 100vw/100vh directly. It wraps its own `<header>`, `<section>`, `<footer>` semantic structure.

**API endpoints:** None. Fully static public page. V1_FEATURE_SPEC.md §3 step 1: "Land on `/` — Hero: 'Create a Meesho catalog in 3 minutes.' CTA: 'Start free.'"

**Services:** None (no HTTP, no auth required). `Router` is not needed — use `routerLink` anchors.

> BOUNDARY: import ONLY from `../../ui`, `@angular/core`, `@angular/router` (RouterLink only).
> ZERO `primeng/...` imports. ZERO `@angular/material/...` imports.

---

## 3. Files to Create / Modify

| Path | Action |
|---|---|
| `src/app/features/landing/landing.component.ts` | MODIFY (replace stub with full component) |
| `src/app/features/landing/landing.component.spec.ts` | CREATE |

The stub at `features/landing/landing.component.ts` currently renders a placeholder. Replace it entirely.

---

## 4. Component Spec

### Layout sketch (360px mobile-first)
```
┌──────────────────────────────────────┐
│  MeeSell  (nav — logo + "Log in" →)  │
├──────────────────────────────────────┤
│                                      │
│   Create a Meesho catalog            │  ← h1, large bold
│   in 3 minutes.                      │
│                                      │
│   AI fills your form. We check       │  ← p, muted subtitle
│   your images. You download the      │
│   XLSX. Zero Meesho rejections.      │
│                                      │
│   [ Start free → ]                   │  ← mee-button primary, routerLink /signup
│   [ See how it works ]               │  ← mee-button ghost, scrolls to #how
│                                      │
├──────────────────────────────────────┤
│  How it works   (id="how")           │  ← <section>
│                                      │
│  1. Pick category  [icon]            │
│  2. AI fills fields [icon]           │
│  3. Download XLSX   [icon]           │
│                                      │
├──────────────────────────────────────┤
│  ₹499/month · Cancel anytime         │  ← simple pricing note
│  [Start free →] [Log in]             │
│                                      │
│  © 2026 MeeSell                      │
└──────────────────────────────────────┘
```

At 1280px: hero becomes 2-column (text left, illustration placeholder right); steps become a horizontal row of 3.

### Form fields / state
No Reactive Form — purely static. No user input on this page.

### Signals / state
- `currentYear = signal(new Date().getFullYear())` — used in footer copyright.
- No loading states, no error states.

### Key behaviors
- "Start free" CTA: `<a routerLink="/signup" mee-button variant="primary">Start free</a>` with `size="lg"` and `fullWidth` on mobile.
- "Log in" link in nav: `<a routerLink="/login" mee-button variant="ghost">Log in</a>`.
- "See how it works": native anchor `href="#how"` smooth-scroll (CSS `scroll-behavior: smooth` on html).
- No JavaScript scroll handler needed.
- Mobile hamburger: NOT included (V1 — single CTA layout; nav collapses to just logo + Log in).

### Semantic HTML
- `<header>` — nav with logo + Log in link.
- `<section aria-labelledby="hero-headline">` — hero content.
- `<section id="how" aria-labelledby="how-headline">` — steps.
- `<footer>` — secondary CTA + copyright.
- `aria-hidden="true"` on decorative icons.

---

## 5. UI Kit Usage Map

| UI element | mee-* component | @Inputs | @Outputs |
|---|---|---|---|
| Primary CTA "Start free" | `mee-button` | `variant="primary"` `size="lg"` `label="Start free"` | — (routerLink anchor wrapping) |
| Nav "Log in" | `mee-button` | `variant="ghost"` `size="sm"` `label="Log in"` | — (routerLink) |
| Secondary footer CTA | `mee-button` | `variant="primary"` `size="md"` `label="Start free"` | — |

`mee-button` contract from FRONTEND_ARCHITECTURE.md §Layer 2:
`variant: 'primary'|'secondary'|'ghost'|'danger'`, `size: 'sm'|'md'|'lg'`, `label: string`, `fullWidth: boolean`, `(clicked): EventEmitter<void>`.

Note: When using `mee-button` as a routerLink anchor wrapper, emit from `(clicked)` with `[routerLink]="/signup"` on the host — OR wrap `<a>` with `[routerLink]` and `mee-button` as the visual wrapper. Follow the pattern established in the codebase; prefer the routerLink anchor approach for correct keyboard + right-click behavior.

---

## 6. API / Data

None. Fully static. No endpoints called.

**V1_FEATURE_SPEC.md §3 step 1 reference:** "Land on `/` — Hero: 'Create a Meesho catalog in 3 minutes.' CTA: 'Start free.'"

---

## 7. Constraints

- `standalone: true, changeDetection: ChangeDetectionStrategy.OnPush`.
- `host: { class: 'mee-landing' }` in `@Component` metadata for CSS scoping.
- Signal for `currentYear` (single reactive value); rest is static template.
- **No API calls** — fully static public page.
- **No Reactive Form** — no `FormBuilder`, no `ReactiveFormsModule`.
- **No auth guard** — route must remain public (V1_FEATURE_SPEC.md §6: "/" is un-guarded).
- **No shell wrapper** — this page manages its own `<header>` and `<footer>`.
- **No hex literals** — all colors via `var(--mee-color-*)` tokens.
- **44px touch targets** on all interactive links and buttons.
- **Mobile-first** — 360px layout is primary; 768px and 1280px via Tailwind breakpoint utilities.
- **ZERO `primeng/...` imports** — use `mee-button` from `../../ui` only.
- **ZERO `@angular/material/...` imports**.
- Imports: `MeeButtonComponent, RouterLink` (Angular router) from correct paths only.

---

## 8. Out of Scope

| Item | When |
|---|---|
| Real pricing page or plan comparison | V1.5 |
| Video embed or animated illustration | V1.5 |
| i18n / Tamil/Hindi copy | V1.5 |
| SEO meta tags (OpenGraph, title) | V1.5 |
| A/B tested copy variants | V1.5 |
| Contact form or live chat | V1.5 |

---

## 9. Verification Gates

1. **BUILD** — `cd frontend && pnpm run build` — zero errors, zero new warnings.
2. **ROUTE RESOLVES** — `pnpm start` → visit `http://localhost:4200/` → LandingComponent renders (no blank, no redirect to /login).
3. **PUBLIC** — Visiting `/` without a valid JWT session renders the page (no auth guard redirect).
4. **TESTS** — `pnpm run test` — minimum 3 tests, all passing:
   - (1) Component creates without errors.
   - (2) "Start free" element present with routerLink pointing to `/signup`.
   - (3) "Log in" element present with routerLink pointing to `/login`.
5. **FOUNDER VISUAL** — Founder reviews at 360px and 1280px: orange CTA, hero headline, 3-step section visible.

---

## 10. Paste-Ready Dispatch Block

```
══════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER NOTIFICATION
Date: 2026-06-09
From: meesell-frontend-coordinator (master session)
Wave: WAVE 5 — F1 LANDING (route: /)
Agent: meesell-angular-component-builder (sonnet)
══════════════════════════════════════════════════════════════════

CONTEXT
───────
Waves 3 (UI Kit) + 4 (Composites) must be confirmed complete before starting.
This dispatch replaces the landing stub with the full public hero page.

Route: /  (PUBLIC — no auth guard, no shell)
Component: LandingComponent
Location: src/app/features/landing/landing.component.ts

BOUNDARY (NON-NEGOTIABLE)
───────────────────────────
  • Import ONLY from ../../ui (mee-* components) + @angular/core + @angular/router
  • ZERO primeng/... imports
  • ZERO @angular/material/... imports

══════════════════════════════════════════════════════════════════

FILES TO MODIFY / CREATE
────────────────────────
  MODIFY: src/app/features/landing/landing.component.ts (replace stub)
  CREATE: src/app/features/landing/landing.component.spec.ts

══════════════════════════════════════════════════════════════════

PAGE STRUCTURE
──────────────
  <header>   nav: logo + "Log in" (mee-button ghost, routerLink /login)
  <section aria-labelledby="hero-headline">
    h1: "Create a Meesho catalog in 3 minutes."
    p:  subtitle — AI fills, image check, XLSX download
    mee-button primary "Start free →" → routerLink /signup
    mee-button ghost "See how it works" → href="#how"
  </section>
  <section id="how" aria-labelledby="how-headline">
    3-step list: Pick category → AI fills fields → Download XLSX
  </section>
  <footer>
    Pricing note + secondary mee-button primary "Start free →"
    Log in link + copyright
  </footer>

SIGNALS / STATE
───────────────
  currentYear = signal(new Date().getFullYear()) — footer copyright only
  No form, no loading state, no error state

VISUAL RULES
────────────
  No hex literals — var(--mee-color-*) or Tailwind semantic classes only
  Mobile-first: 360px primary layout
  44px touch targets on all interactive elements
  host: { class: 'mee-landing' } in @Component for CSS scoping
  Semantic HTML: <header> / <section aria-labelledby> / <footer>

UI KIT USAGE
────────────
  mee-button variant="primary" size="lg" → "Start free" CTA (hero + footer)
  mee-button variant="ghost"   size="sm" → "Log in" (nav)
  No other mee-* composites needed on this page

CONSTRAINTS
───────────
  • standalone + OnPush
  • No ReactiveFormsModule — purely static page
  • No auth guard — public route
  • No shell — manages own <header>/<footer>
  • No hex literals
  • ZERO primeng/... imports

OUT OF SCOPE
  ✗ Pricing/plan comparison tables
  ✗ Video/animation embeds
  ✗ i18n (V1.5)
  ✗ SEO meta tags

TESTS (min 3)
─────────────
  1. Component creates without errors
  2. "Start free" element has routerLink → /signup
  3. "Log in" element has routerLink → /login

VERIFICATION GATES
──────────────────
Gate 1 BUILD:   pnpm run build → zero errors
Gate 2 ROUTE:   / renders (not redirected to /login, no blank)
Gate 3 PUBLIC:  no auth guard fires on /
Gate 4 TESTS:   pnpm run test → min 3 new tests, all pass
Gate 5 VISUAL:  founder reviews 360px + 1280px — orange CTA + hero headline

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```

---

## Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-09 | meesell-frontend-coordinator (master) | Initial authoring — Wave 5 Landing (F1); Option A-full; mee-* kit only |

# Wave 1B — Ratified Template Spec

**Date:** 2026-06-08
**Status:** SUPERSEDED — Signal Admin rejected by founder 2026-06-08. Awaiting founder-provided theme source.
**Template:** Signal Admin (codebangla/signal-admin)
**Local path:** themes/signal-admin/

---

## Decision

Signal Admin is ratified as the MeeSell UI reference template replacing Spike Angular (paywalled).

**Angular version decision:** MeeSell frontend upgraded from Angular 18 → Angular 20 to match Signal Admin's stack directly. Code will be reused (not just referenced visually).

---

## Template Facts (verified)

| Item | Value |
|------|-------|
| Repo | github.com/codebangla/signal-admin |
| Angular | 20.0.0 |
| Angular Material | 20.0.0 |
| Tailwind CSS | 3.4.0 |
| License | MIT (file verified: Copyright 2025 Md Sajedul Haque Romy) |
| Standalone | YES — standalone: true on all page components |
| Paywall | NONE — zero pro/premium/locked mentions in src/ |
| Icon library | Material Icons (CDN) — one-line swap to Material Symbols for MeeSell |
| Charts | Chart.js 4.5.0 |
| Pages | 10 routed pages (2 auth + 8 main) |
| Auth type | Mock email+password — to be replaced with MeeSell phone+OTP (MSG91) |

---

## Pages in Signal Admin (reuse map)

| Signal Admin route | MeeSell route | Reuse decision |
|-------------------|---------------|---------------|
| /auth/login | /login | Replace — MeeSell OTP flow already built |
| /auth/signup | /signup | Replace — MeeSell signup already built |
| /dashboard | /dashboard | REUSE — stat cards + chart layout |
| /users | /catalogs | REUSE — table + search + pagination pattern |
| /forms | /catalogs/:id/edit | REUSE — form layout pattern |
| /ui | /images | REUSE — card grid + badge pattern |
| /reports | /export | REUSE — summary + history table pattern |
| /settings | /profile | REUSE — settings form pattern |
| /profile | /profile | REUSE — profile card pattern |
| /blank | n/a | Skip |

---

## What changes for MeeSell

1. **Color tokens** — replace Signal Admin blue/purple with MeeSell tokens:
   - Sidebar: #111c2d (dark navy)
   - Primary accent: #F26B23 (MeeSell orange)
   - Background: #f0f5f9
   - Border: #e5eaef

2. **Icon font** — swap `?family=Material+Icons` → `?family=Material+Symbols+Outlined` in index.html

3. **Auth flow** — Signal Admin email+password login → MeeSell phone+OTP (already implemented)

4. **Mobile sidebar** — Signal Admin sidebar doesn't collapse at 360px; MeeSell uses mat-sidenav with mode switching (already implemented in shell.component.ts)

5. **Angular version** — both now at Angular 20 (upgrade complete)

---

## Wave 1C Handoff

Wave 1C proceeds page-by-page using Signal Admin components as the source. Each page session:
1. Read the Signal Admin component from themes/signal-admin/src/app/features/<feature>/
2. Apply MeeSell design tokens and business logic
3. Write to frontend/src/app/features/<feature>/

Sequence: dashboard → catalog-list → catalog-form → images → preview → export → profile

---

*Ratified: 2026-06-08 | Wave 1B closed*

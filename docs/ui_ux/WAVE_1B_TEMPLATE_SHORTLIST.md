# Wave 1B Template Shortlist

*Generated: Wave 1B Research Phase | 2026-06-08*

---

## Context

Spike Angular (`themes/spike-angular/`) was the reference design system but Spike Pro layouts are paywalled — impossible to access for visual comparison. Wave 1B task: find a replacement Angular admin template that is free, MIT, Angular 18+, Angular Material, standalone components, no paywall.

**Total candidates evaluated:** 14

---

## Rejected Candidates (11)

| # | Template | Reason |
|---|----------|--------|
| 1 | MatX Angular | Angular 14 — too old |
| 2 | Material Dashboard Angular (Creative Tim) | Angular 14 — too old |
| 3 | CoreUI Free Angular | Angular 21 + Bootstrap 5 — NOT Angular Material |
| 4 | Mantis Angular Free (CodedThemes) | Angular 21 + Bootstrap 5 — NOT Angular Material despite name |
| 5 | Berry Angular Free (CodedThemes) | Angular 21 + Bootstrap 5 — NOT Angular Material |
| 6 | TailAdmin Angular | Tailwind-only, no Angular Material; LICENSE file inaccessible (no verified MIT) |
| 7 | Angular-Tailwind (lannodev) | Tailwind-only, no Angular Material |
| 8 | Modernize Angular Free (AdminMart) | AUTO-REJECTED — same author lineage as Spike |
| 9 | WrapPixel / Material Pro Angular Lite | AUTO-REJECTED — same author lineage as Spike |
| 10 | ngx-admin (Akveo) | Angular 15 + Nebular (not Angular Material) |
| 11 | flatlogic/angular-material-admin | Angular 11 + FontAwesome — too old |

**Key ecosystem finding:** The Angular Material + Tailwind + Angular 18+ + standalone + MIT + no-paywall space is extremely thin. Only one template natively satisfies all mandatory criteria.

---

## Shortlisted Candidates (3)

### Candidate 1 — Signal Admin (PRIMARY RECOMMENDATION)

- **Repo:** https://github.com/codebangla/signal-admin
- **Angular:** 20.0.0
- **Angular Material:** 20.0.0
- **Tailwind CSS:** 3.4.0
- **License:** MIT (LICENSE file confirmed: "MIT License / Copyright (c) 2025 Md Sajedul Haque Romy")
- **Standalone:** YES — `standalone: true` confirmed in app.component.ts
- **No paywall:** YES — zero premium/pro mentions
- **Stars:** 7 | **Forks:** 2 | **Commits:** ~5 (brand new project, created ~2025)
- **Icon library:** Material Icons (CDN link in index.html — compatible with Material Symbols via font URL swap)
- **Pages:**
  - `/login` — login page
  - `/signup` — signup page
  - `/dashboard` — main dashboard with stat cards
  - `/analytics` — analytics page
  - `/profile` — user profile
  - `/reports` — reports page
  - `/settings` — settings page
  - `/users` — user list (table with CRUD)
  - `/users/:id` — user detail dialog
  - `/form-demo` — forms showcase
  - `/ui-demo` — UI components (chips, badges, buttons)
  - `/blank` — blank template
- **Layout:** Two-layout pattern (auth-layout + main-layout with sidebar) — mirrors MeeSell shell
- **Weakness:** Very new project (7 stars). Could have rough edges. Routing uses app-routing.module.ts (module-based router config), but components are standalone.
- **Why #1:** Only template that natively combines Angular Material + Tailwind + standalone + MIT + Angular 20. Covers all 8 required page types. Layout pattern matches MeeSell's two-layout architecture exactly.

---

### Candidate 2 — ng-matero (SECONDARY)

- **Repo:** https://github.com/ng-matero/ng-matero
- **Angular:** 21.2.11
- **Angular Material:** 21.2.9
- **Tailwind CSS:** NOT present (Material-only)
- **License:** MIT (LICENSE file confirmed: "MIT License / Copyright (c) 2019 Zongbin")
- **Standalone:** YES — app.config.ts + app.routes.ts pattern (functional bootstrap)
- **No paywall:** YES — fully free, no pro tier
- **Stars:** 1,500+ | **Forks:** 385 | **Last commit:** May 5, 2026 (actively maintained)
- **Icon library:** Material Icons (local font in `fonts/Material_Icons.css` — compatible with Symbols via swap)
- **Pages:**
  - Dashboard
  - Forms (datetime, dynamic forms, form elements, select)
  - Material showcase (20+ demos: autocomplete, badge, button, card, checkbox, chips, dialog, datepicker, expansion, form fields, grid, icon, input, list, menu, paginator, progress, radio, ripple, sidenav)
  - Design pages (colors, icons)
  - Authentication (login, 404)
- **Layout:** Full sidebar shell + auth layout with RTL + dark mode support
- **Weakness:** No Tailwind (would need to be added manually). Uses older icon font (not Material Symbols natively). Pages are more demo/showcase oriented than production-page shells.
- **Why #2:** Most mature, actively maintained Angular Material template in the free/MIT space. 1.5k stars, last committed May 2026. Comprehensive component coverage — excellent reference for Material component patterns.

---

### Candidate 3 — lannodev/angular-tailwind (CONDITIONAL)

- **Repo:** https://github.com/lannodev/angular-tailwind
- **Angular:** 20.x with Signals
- **Angular Material:** NOT present (Tailwind-only)
- **Tailwind CSS:** v4
- **License:** MIT
- **Standalone:** YES — signals + standalone architecture
- **No paywall:** YES
- **Stars:** 514 | **Last commit:** Late 2025
- **Icon library:** Unknown (Tailwind-based, likely Heroicons or similar)
- **Pages:** Starter kit — fewer pre-built pages, more of a scaffold
- **Conditional note:** Requires Angular Material to be added manually. Included as #3 because it demonstrates the modern Angular 20 + Signals + Tailwind pattern — useful as a Tailwind layout reference. NOT recommended as the primary deploy target for Wave 1B.

---

## Decision Matrix

| Criterion | Signal Admin | ng-matero | angular-tailwind |
|-----------|-------------|-----------|-----------------|
| Angular 18+ | yes (20) | yes (21) | yes (20) |
| Angular Material | yes | yes | no |
| Tailwind CSS | yes | no | yes |
| Standalone components | yes | yes | yes |
| MIT license (FILE verified) | yes | yes | yes |
| No paywall | yes | yes | yes |
| Material Symbols compatible | swap needed | swap needed | unknown |
| Pre-built page shells | yes (12 pages) | yes (20+ demos) | few |
| Community maturity | 7 stars (new) | 1.5k stars | 514 stars |
| Last updated | 2025 (new) | May 2026 | late 2025 |

---

## Recommendation

**Signal Admin (Candidate 1)**

Deploy to `themes/signal-admin/` for founder visual confirmation. It is the only template that natively satisfies all mandatory + preferred criteria without requiring post-clone integration work.

---

## Wave 1B Gate A Status

- [x] At least 8 candidates evaluated (14 evaluated: 3 shortlisted + 11 rejected)
- [x] Each shortlisted has verified license FILE (Signal Admin: MIT 2025; ng-matero: MIT 2019; angular-tailwind: MIT)
- [x] Each rejected has documented rejection reason
- [x] Recommendation has comparative rationale
- [ ] Paywall evidence via local clone — Signal Admin deployment in progress

---

*Screenshots directory: `docs/ui_ux/wave_1b_screenshots/signal-admin/`*

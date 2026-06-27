## project: wave_1b_template_shortlist (2026-06-08)

Task: Research Wave 1B — identify replacement Angular admin template now that Spike Pro layouts are paywalled.
Output: docs/ui_ux/WAVE_1B_TEMPLATE_SHORTLIST.md

Mandatory criteria applied:
  - Angular 18+ (standalone components)
  - Angular Material (not Bootstrap)
  - MIT LICENSE file confirmed (not just package.json field)
  - No paywall on any page/layout
  - Tailwind CSS present (preferred, not hard-block)

Candidates evaluated: 14 total (3 shortlisted, 11 rejected)

Key rejection patterns discovered:
  - CodedThemes Berry/Mantis/CoreUI use Bootstrap 5 despite Angular branding — always verify CSS framework
  - AdminMart (Modernize) + WrapPixel/Material Pro share Spike author lineage — auto-reject on conflict-of-interest
  - Angular 11-15 templates: too old (standalone = Angular 14+, but 14 is borderline; target 18+)
  - Tailwind-only templates (TailAdmin, lannodev) have no Angular Material — valid for layout reference only

PRIMARY RECOMMENDATION: Signal Admin
  - Repo: https://github.com/codebangla/signal-admin
  - Stack: Angular 20 + Angular Material 20 + Tailwind 3.4 + standalone + MIT 2025
  - Layout: two-layout pattern (auth + main with sidebar) — matches MeeSell shell exactly
  - Pages: 12 pre-built pages covering all 8 required MeeSell page types
  - Weakness: 7 stars (brand new, 2025) — may have rough edges; verify via local clone
  - Material Icons via CDN — swap to Material Symbols by changing font URL (one-line change)

SECONDARY: ng-matero
  - Stack: Angular 21 + Angular Material 21 + NO Tailwind (would need manual addition)
  - Strength: 1,500+ stars, last commit May 2026, RTL + dark mode support
  - Best used as Material component pattern reference, not primary template

CONDITIONAL: lannodev/angular-tailwind
  - Stack: Angular 20 + Signals + Tailwind v4 + NO Angular Material
  - Useful as Tailwind layout scaffold reference only

Ecosystem learning: Angular Material + Tailwind + Angular 18+ + standalone + MIT + no-paywall is a very thin
space (2025-2026). Signal Admin is the only native fit. If Signal Admin proves too rough, the fallback is
ng-matero (add Tailwind manually) or starting from the Angular CLI scaffold with ng-matero as a component
pattern reference.

Screenshots directory created: docs/ui_ux/wave_1b_screenshots/signal-admin/

---

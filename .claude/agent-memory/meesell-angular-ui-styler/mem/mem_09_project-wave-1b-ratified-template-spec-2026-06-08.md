## project: wave_1b_ratified_template_spec (2026-06-08)

Task: Write WAVE_1B_RATIFIED_TEMPLATE_SPEC.md — founder ratification of Signal Admin as the Wave 1B reference template.

Output file: docs/ui_ux/WAVE_1B_RATIFIED_TEMPLATE_SPEC.md

Key ratified decisions:
  - Signal Admin (github.com/codebangla/signal-admin) is the MeeSell reference template
  - Angular upgrade: Angular 18 → Angular 20 (matches Signal Admin; code reuse, not visual reference)
  - Template stack: Angular 20 + Angular Material 20 + Tailwind 3.4 + standalone: true + MIT 2025
  - License verified: MIT, Copyright 2025 Md Sajedul Haque Romy
  - No paywall: zero pro/premium/locked mentions in src/

Reuse map (locked):
  - /dashboard: REUSE — stat cards + chart layout
  - /catalogs: REUSE — table + search + pagination pattern (from /users page)
  - /catalogs/:id/edit: REUSE — form layout pattern (from /forms page)
  - /images: REUSE — card grid + badge pattern (from /ui page)
  - /export: REUSE — summary + history table (from /reports page)
  - /profile: REUSE — settings form + profile card pattern (from /settings + /profile)
  - /login, /signup: REPLACE — MeeSell OTP flow already built

5 changes for MeeSell (locked in spec):
  1. Color tokens: sidebar #111c2d, primary #F26B23, bg #f0f5f9, border #e5eaef
  2. Icon font: Material+Icons CDN → Material+Symbols+Outlined (one-line index.html change)
  3. Auth flow: email+password → phone+OTP (already implemented)
  4. Mobile sidebar: Signal Admin no 360px collapse → MeeSell mat-sidenav mode switching (already implemented)
  5. Angular version: both at Angular 20 (upgrade complete)

Wave 1C sequence: dashboard → catalog-list → catalog-form → images → preview → export → profile
Source path: themes/signal-admin/src/app/features/<feature>/
Target path: frontend/src/app/features/<feature>/

Angular upgrade gate: Angular version bump from 18 → 20 must complete before Wave 1C page work begins.
This affects component-builder and service-builder dispatch sequencing.

---

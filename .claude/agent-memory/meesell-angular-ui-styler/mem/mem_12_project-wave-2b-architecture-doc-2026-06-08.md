## project: wave_2b_architecture_doc (2026-06-08)

Task: Write docs/FRONTEND_ARCHITECTURE.md — founder-approved abstraction-first frontend architecture for MeeSell Wave 2B+.

This document SUPERSEDES the prior Angular Material-based FRONTEND_ARCHITECTURE.md.

Key architecture decisions locked:
  - Stack: Angular 21 + PrimeNG 21 + Sakai-ng Free + Tailwind CSS 4 + TypeScript strict
  - 4-layer architecture pattern:
    Layer 1: Design System (pure CSS/SCSS — no library imports)
    Layer 2: MeeSell UI Kit (PrimeNG wrappers — the ONLY place PrimeNG is imported)
    Layer 3: Layouts (MeeShellComponent, MeeAuthLayoutComponent) + Shared composites
    Layer 4: Features (ZERO direct PrimeNG imports — use @mee/ui only)
  - SOLID DIP pattern: Features → @mee/ui abstractions ← PrimeNG
  - 17 UI Kit components specified with TypeScript contracts
  - Path aliases: @mee/ui, @mee/shared, @mee/design, @mee/core
  - Wave sequence: 2B scaffold → 2C UI Kit → 2D Shared → 2E+ Features

Design token values UNCHANGED from Wave 1 work:
  - #F26B23 primary (MeeSell orange)
  - #111c2d sidebar (dark navy)
  - #f0f5f9 bg (page background)
  - #2a3547 on-surface (body text)
  - #e5eaef outline (border)

For Wave 2B theming:
  - Angular Material _theme.scss + _component-overrides.scss are RETIRED
  - New theming: @primeuix/themes preset + CSS custom properties in _tokens.scss
  - Tailwind config extends design tokens via CSS custom property references
  - No @primeuix/themes import allowed in Layer 1 (_tokens.scss is pure :root vars)
  - PrimeNG preset customisation goes in a new file: src/app/ui/prime-preset.ts (Layer 2)

Files written:
  - docs/FRONTEND_ARCHITECTURE.md (full rewrite)
  - docs/status/STATUS_FRONTEND.md (prepended update block)

---

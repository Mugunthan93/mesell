## Session 2026-06-09 — Dispatch Doc Authoring — Wave 4 Composites + Wave 5 Landing + Profile {#dispatch-doc-authoring-wave45}

### Task type
Spec document authoring only (no code written). Three dispatch docs created.

### Architecture decision: Option A-full carried through all docs
- Layer 3 composites: ZERO direct PrimeNG imports; consume mee-* from ui/ only.
- Layer 4 features: ZERO PrimeNG; import from ../../ui + ../../shared + ../../layouts only.
- Boundary verification: `grep -r "primeng" src/app/shared/` must return empty after wave 4.

### Pattern: mee-badge vs mee-status-badge for non-ProductStatus values
- `mee-status-badge` expects ProductStatus union (draft/ready/exported/live/deleted/processing/pending/failed).
- Plan tier ('free'/'pro') is NOT in ProductStatus — causes TS type mismatch if mee-status-badge used.
- CORRECT for plan tier: use `mee-badge` (Layer 2) directly with `computed<MeeBadgeSeverity>()`.
- General rule: if value is not a ProductStatus literal, skip mee-status-badge, use mee-badge + explicit severity.

### Pattern: Landing — no shell, no auth-layout, no mee-page-header composite
- LandingComponent (/) is a standalone public page managing its own header/footer HTML.
- mee-page-header composite is for shell child pages — NOT for standalone public pages.
- Only mee-button + RouterLink needed. Keep import list minimal.

### Pattern: Profile Wave 5 — AuthService.currentUser as sole data source
- Wave 5 reads name/phone/plan from AuthService.currentUser signal. No separate GET call.
- Save simulated with setTimeout(800). No ProfileApiService injection in Wave 5.
- Wave 6: inject feature-scoped ProfileApiService (no providedIn root).
- Replace in-place: features/profile/profile.component.ts (stub already exists from Wave 2B).

### Docs written (2026-06-09)
- docs/ui_ux/WAVE_4_COMPOSITES_DISPATCH.md (C1–C5 in one doc)
- docs/ui_ux/WAVE_5_LANDING_DISPATCH.md (F1 public hero, route /)
- docs/ui_ux/WAVE_5_PROFILE_DISPATCH.md (F13 account settings, route /profile, shell child)

- docs/ui_ux/WAVE_5_IMAGES_DISPATCH.md — F9 /catalogs/:id/images — ImageUploaderComponent
- docs/ui_ux/WAVE_5_PREVIEW_DISPATCH.md — F10 /catalogs/:id/preview — PreviewComponent
- docs/ui_ux/WAVE_5_PRICING_DISPATCH.md — F11 /catalogs/:id/pricing — PricingComponent
- docs/ui_ux/WAVE_5_EXPORT_DISPATCH.md — F12 /catalogs/:id/export — ExportComponent

### Pattern: Wave 5 Group C dispatch doc authoring (2026-06-09)
- No mee-slider in UI Kit — use native <input type="range"> with Tailwind accent-[var(--mee-color-primary)] for pricing slider. Document in memory and dispatch doc.
- Export polling simulation: native setInterval + ngOnDestroy clearInterval (not takeUntilDestroyed). Real Wave 6: replace with interval().pipe(switchMap, takeUntilDestroyed, takeWhile).
- Images 5-check matrix: native <table role="table"> with mee-badge per row (success|danger). NOT p-table.
- Preview 3 surfaces: inline HTML in one component template (not 3 child components) to respect 3-level nesting max.
- Export state machine: single exportStatus signal drives @switch in template for 4 card states (idle/processing/ready/failed).
- Pricing P&L worked example: MRP 899 → seller_payout 408 → net_margin 158 (positive, green). Hardcode in simulation.
- Images simulation: slot index 1 fails color_space_rgb (CMYK) — matches V1_FEATURE_SPEC §3 journey step 7 exactly.
- Preview simulation: title "Blue Cotton Kurti With Mirror Work" (35 chars) → triggers truncation warning (>30).

---

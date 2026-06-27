## project: wave_2a_framework_shortlist (2026-06-08)

Task: Research Wave 2A — identify Angular UI framework candidates for full frontend reset from Angular Material.
Output: docs/ui_ux/WAVE_2A_FRAMEWORK_SHORTLIST.md
Status update: docs/status/STATUS_DESIGN_SYSTEM.md prepended with Wave 2A block.

Mandatory criteria applied:
  - Angular 18+ (standalone components)
  - MIT license verified from package.json / LICENSE file (not README)
  - No paywall on any page/layout
  - Tailwind CSS presence noted (preferred)
  - Pre-built admin shell (preferred — reduces Wave 2B effort)

Candidates evaluated: 8 total (3 shortlisted, 5 rejected)

Rejected candidates:
  1. Clarity Design (vmware-archive/clarity) — archived 2023, no Angular 18+ support
  2. taiga-ui-admin (AAVision) — Angular 16.1.4, only 11 stars
  3. Signal Admin (Wave 1B) — rejected by founder 2026-06-08
  4. CoreUI Angular — Bootstrap 5, not a component library
  5. ngx-admin (Akveo) — Angular 15 + Nebular (non-standard UI library)

PRIMARY RECOMMENDATION: PrimeNG + Sakai-ng Free
  - Repo: https://github.com/primefaces/sakai-ng
  - Stack: Angular 21 + PrimeNG 21.0.2 + Tailwind CSS 4.1.11 + @primeuix/themes 2.0.0 + standalone + MIT
  - Stars: 941 (Sakai) / 10k+ (PrimeNG library itself)
  - Last release: v21.0.0 — Feb 2, 2026
  - Page types pre-built: 13 (shell, login, error/access, dashboard, forms, tables, lists, CRUD, landing, charts, dialogs, empty, 404)
  - No paywall: Apollo is a separate paid product; Sakai itself is fully free
  - MeeSell-relevant components: p-fileUpload, p-dataTable, p-steps, p-dialog, p-confirmDialog, p-tag, p-treeSelect, p-inputOtp, p-progressBar, p-toast
  - Minor concern: primeclt ^0.1.5 Vue dep — removable before Wave 2B scaffold, not a blocker

SECONDARY: NG-ZORRO (ng-zorro-antd) + ng-alain
  - ng-zorro 21.3.1 = Angular 21, MIT, standalone
  - ng-alain v21.2.0 = Angular 21.2.11, MIT, standalone
  - Strength: most pages pre-built (3 dashboard variants, 3 form variants, 3 list variants)
  - Weakness: NO Tailwind (uses Less CSS); Ant Design is desktop-first

CONDITIONAL: Taiga UI 5.10.0
  - Angular >= 19, Apache-2.0 (NOT MIT — fails auto-reject criterion)
  - No admin starter template — full shell must be built from scratch
  - Best component for MeeSell: TuiInputPhone (phone+OTP auth)

Key design-system change for Wave 2B:
  PrimeNG does NOT use Angular Material mat-* selectors or CDK.
  All Wave 1 overrides (_theme.scss, _component-overrides.scss, M3 theme) will not apply.
  Wave 2B must use @primeuix/themes presets + Tailwind utilities for design tokens.
  Color tokens (#F26B23 primary, #111c2d sidebar, #f0f5f9 bg) must be re-wired via PrimeUI preset.

Gate A: COMPLETE. Awaiting founder pick for Wave 2B scaffold.

---

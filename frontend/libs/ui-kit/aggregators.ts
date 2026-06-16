/**
 * @mesell/ui-kit — Aggregator arrays (Phase 2, UI Design-System Decoupling)
 *
 * PURPOSE
 * -------
 * Aggregator arrays are for a standalone component's `imports: [...]` ONLY.
 * They group the 21 MeeSell UI-Kit component classes by concern so consumers
 * can cherry-pick the subset they need:
 *
 *   @Component({ standalone: true, imports: [...MEE_FORM, ...MEE_FEEDBACK], … })
 *
 * SERVICES ARE NOT HERE — THIS IS INTENTIONAL
 * --------------------------------------------
 * `MeeToastService` and `MeeConfirmService` are Angular *providers*, not
 * importable standalone components. They are supplied at application root via
 * `provideMeeUi()` in `app.config.ts`. Placing a service in a component's
 * `imports` array is an Angular compile-time error.
 *
 * `MEE_UI_ALL` is the escape hatch that spreads all six ui-kit groups (21
 * component classes). Prefer the concern-scoped groups for better tree-shaking.
 *
 * LAYOUT IS NOT HERE
 * ------------------
 * `MEE_LAYOUT` (page, section, toolbar, grid, form-layout) is owned by the
 * `@mesell/layout` library and will be populated in Phases 3–4 of the
 * decoupling plan. It is NOT part of `MEE_UI_ALL`.
 *
 * MFE ADOPTION
 * ------------
 * Aggregators are defined here but NOT yet consumed by any MFE or app import.
 * The MFE import sweep is Phase 6 (see UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md).
 *
 * COVERAGE (6 + 3 + 5 + 2 + 4 + 1 = 21 component classes)
 *   MEE_FORM     6 — form input primitives
 *   MEE_OVERLAY  3 — modal / dialog / drawer surfaces
 *   MEE_FEEDBACK 5 — notification / status indicators
 *   MEE_DATA     2 — data presentation primitives
 *   MEE_COMMON   4 — general-purpose primitives (incl. mee-icon, Phase 1)
 *   MEE_FILE     1 — file upload
 *   MEE_UI_ALL  21 — spread of all six groups
 */

import { Type } from '@angular/core';

import { MeeInputComponent }         from './input/input.component';
import { MeeTextareaComponent }      from './textarea/textarea.component';
import { MeeSelectComponent }        from './select/select.component';
import { MeeTreeSelectComponent }    from './tree-select/tree-select.component';
import { MeePasswordInputComponent } from './password-input/password-input.component';
import { MeeOtpInputComponent }      from './otp-input/otp-input.component';

import { MeeDialogComponent }        from './dialog/dialog.component';
import { MeeDrawerComponent }        from './drawer/drawer.component';
import { MeeConfirmDialogComponent } from './confirm-dialog/confirm-dialog.component';

import { MeeToastComponent }         from './toast/toast.component';
import { MeeBadgeComponent }         from './badge/badge.component';
import { MeeSkeletonComponent }      from './skeleton/skeleton.component';
import { MeeSpinnerComponent }       from './spinner/spinner.component';
import { MeeProgressBarComponent }   from './progress-bar/progress-bar.component';

import { MeeTableComponent }         from './table/table.component';
import { MeeStepsComponent }         from './steps/steps.component';

import { MeeButtonComponent }        from './button/button.component';
import { MeeCardComponent }          from './card/card.component';
import { MeeMenuComponent }          from './menu/menu.component';
import { MeeIconComponent }          from './icon/icon.component';

import { MeeFileUploadComponent }    from './file-upload/file-upload.component';

// ---------------------------------------------------------------------------
// MEE_FORM (6) — form input primitives
// Covers: input, textarea, select, treeselect, password, otp
// ---------------------------------------------------------------------------
export const MEE_FORM = [
  MeeInputComponent,
  MeeTextareaComponent,
  MeeSelectComponent,
  MeeTreeSelectComponent,
  MeePasswordInputComponent,
  MeeOtpInputComponent,
] as const satisfies readonly Type<unknown>[];

// ---------------------------------------------------------------------------
// MEE_OVERLAY (3) — modal / dialog / drawer surfaces
// Covers: dialog, drawer, confirm-dialog (component only — MeeConfirmService
//         is a provider; it goes in provideMeeUi(), NOT here)
// ---------------------------------------------------------------------------
export const MEE_OVERLAY = [
  MeeDialogComponent,
  MeeDrawerComponent,
  MeeConfirmDialogComponent,
] as const satisfies readonly Type<unknown>[];

// ---------------------------------------------------------------------------
// MEE_FEEDBACK (5) — notification / status indicators
// Covers: toast, badge, skeleton, spinner, progress-bar
// Note: MeeToastService is a provider; it goes in provideMeeUi(), NOT here.
// ---------------------------------------------------------------------------
export const MEE_FEEDBACK = [
  MeeToastComponent,
  MeeBadgeComponent,
  MeeSkeletonComponent,
  MeeSpinnerComponent,
  MeeProgressBarComponent,
] as const satisfies readonly Type<unknown>[];

// ---------------------------------------------------------------------------
// MEE_DATA (2) — data presentation primitives
// Covers: table, steps
// ---------------------------------------------------------------------------
export const MEE_DATA = [
  MeeTableComponent,
  MeeStepsComponent,
] as const satisfies readonly Type<unknown>[];

// ---------------------------------------------------------------------------
// MEE_COMMON (4) — general-purpose primitives
// Covers: button, card, menu, icon (MeeIconComponent added in Phase 1)
// ---------------------------------------------------------------------------
export const MEE_COMMON = [
  MeeButtonComponent,
  MeeCardComponent,
  MeeMenuComponent,
  MeeIconComponent,
] as const satisfies readonly Type<unknown>[];

// ---------------------------------------------------------------------------
// MEE_FILE (1) — file upload
// Covers: file-upload
// ---------------------------------------------------------------------------
export const MEE_FILE = [
  MeeFileUploadComponent,
] as const satisfies readonly Type<unknown>[];

// ---------------------------------------------------------------------------
// MEE_UI_ALL (21) — escape hatch: spread of all six ui-kit groups
// Use this only when a component genuinely needs the full ui-kit surface.
// Prefer concern-scoped groups for tree-shaking in production bundles.
// MEE_LAYOUT is NOT included here — it lives in @mesell/layout (Phases 3–4).
// Coverage: 6 + 3 + 5 + 2 + 4 + 1 = 21
// ---------------------------------------------------------------------------
export const MEE_UI_ALL = [
  ...MEE_FORM,
  ...MEE_OVERLAY,
  ...MEE_FEEDBACK,
  ...MEE_DATA,
  ...MEE_COMMON,
  ...MEE_FILE,
] as const;

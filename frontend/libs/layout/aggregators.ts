/**
 * @mesell/layout — Aggregator array (Phase 3, UI Design-System Decoupling)
 *
 * PURPOSE
 * -------
 * `MEE_LAYOUT` groups the six page-primitive component classes so standalone
 * components can spread them into `imports: [...]` alongside other aggregators:
 *
 *   @Component({ standalone: true, imports: [...MEE_LAYOUT, ...MEE_FORM], … })
 *
 * SERVICES ARE NOT HERE — THIS IS INTENTIONAL
 * --------------------------------------------
 * `@mesell/layout` primitives are purely presentational (structure + projection).
 * They carry no Angular providers. N/A.
 *
 * MFE ADOPTION
 * ------------
 * `MEE_LAYOUT` is defined here but NOT yet consumed by any MFE or app import.
 * The MFE import sweep is Phase 6 (see UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md).
 *
 * CHROME IS NOT HERE
 * ------------------
 * Chrome primitives (`mee-app-bar`, `mee-side-nav`, `mee-nav-item`,
 * `mee-user-menu`) are Phase 4. They will be added to a separate
 * `MEE_CHROME` aggregator and re-exported from this barrel.
 *
 * COVERAGE (6 component classes)
 *   MeePageComponent       — top-level routed-page container
 *   MeeSectionComponent    — titled content section
 *   MeeToolbarComponent    — horizontal action bar (start + end slots)
 *   MeeGridComponent       — responsive 2-D grid (auto-fill or fixed cols)
 *   MeeStackComponent      — 1-D flex line with gap
 *   MeeFormLayoutComponent — vertical form field column
 */

import { Type } from '@angular/core';

import { MeePageComponent }       from './page/page.component';
import { MeeSectionComponent }    from './section/section.component';
import { MeeToolbarComponent }    from './toolbar/toolbar.component';
import { MeeGridComponent }       from './grid/grid.component';
import { MeeStackComponent }      from './stack/stack.component';
import { MeeFormLayoutComponent } from './form-layout/form-layout.component';

// ---------------------------------------------------------------------------
// MEE_LAYOUT (6) — page primitives
// Covers: page, section, toolbar, grid, stack, form-layout
// ---------------------------------------------------------------------------
export const MEE_LAYOUT = [
  MeePageComponent,
  MeeSectionComponent,
  MeeToolbarComponent,
  MeeGridComponent,
  MeeStackComponent,
  MeeFormLayoutComponent,
] as const satisfies readonly Type<unknown>[];

# @mesell/ui-kit

MeeSell UI component library — PrimeNG wrapper layer. All MFE imports go
through this barrel; no MFE or app ever imports PrimeNG directly.

Import path: `@mesell/ui-kit` (barrel root only — never a subpath).

---

## Aggregators

Phase 2 of the UI Design-System Decoupling plan adds **grouped aggregator
arrays** so standalone components can import a concern-scoped subset of the
ui-kit without listing every component class individually.

### The two-pronged contract

| Surface | What it contains | How to consume |
|---------|-----------------|----------------|
| **Aggregator arrays** (`MEE_FORM`, `MEE_OVERLAY`, etc.) | Angular *component classes* only (21 total) | Spread into a standalone component's `imports: [...]` |
| **`provideMeeUi()`** | `MeeToastService`, `MeeConfirmService`, PrimeNG theme bootstrap | Add to `ApplicationConfig.providers` in `app.config.ts` — never in `imports` |

### The seven arrays

| Array | Count | Members |
|-------|-------|---------|
| `MEE_FORM` | 6 | `MeeInputComponent`, `MeeTextareaComponent`, `MeeSelectComponent`, `MeeTreeSelectComponent`, `MeePasswordInputComponent`, `MeeOtpInputComponent` |
| `MEE_OVERLAY` | 3 | `MeeDialogComponent`, `MeeDrawerComponent`, `MeeConfirmDialogComponent` |
| `MEE_FEEDBACK` | 5 | `MeeToastComponent`, `MeeBadgeComponent`, `MeeSkeletonComponent`, `MeeSpinnerComponent`, `MeeProgressBarComponent` |
| `MEE_DATA` | 2 | `MeeTableComponent`, `MeeStepsComponent` |
| `MEE_COMMON` | 4 | `MeeButtonComponent`, `MeeCardComponent`, `MeeMenuComponent`, `MeeIconComponent` |
| `MEE_FILE` | 1 | `MeeFileUploadComponent` |
| `MEE_UI_ALL` | 21 | Spread of all six groups above (escape hatch) |

Total: 6 + 3 + 5 + 2 + 4 + 1 = **21 component classes**.

### Services stay in `provideMeeUi()` — NEVER in aggregator arrays

`MeeToastService` and `MeeConfirmService` are Angular *providers*. Placing a
provider in a component's `imports` array is an Angular compile-time error.
Both services are supplied at root via `provideMeeUi()`:

```ts
// app.config.ts
import { provideMeeUi } from '@mesell/ui-kit';

export const appConfig: ApplicationConfig = {
  providers: [...provideMeeUi()],
};
```

Then inject them anywhere via Angular DI — no extra imports needed.

### Usage example (Phase 6 — illustrative only)

MFE adoption of aggregators is Phase 6. The arrays are defined but not yet
consumed by any MFE or app component. When Phase 6 lands, components will use:

```ts
import { Component } from '@angular/core';
import { MEE_FORM, MEE_FEEDBACK } from '@mesell/ui-kit';

@Component({
  selector: 'app-example',
  standalone: true,
  imports: [...MEE_FORM, ...MEE_FEEDBACK],  // 6 + 5 = 11 component classes
  template: `...`,
})
export class ExampleComponent {}
```

Use `MEE_UI_ALL` only when a component genuinely needs the full ui-kit
surface. Prefer concern-scoped groups so bundlers can tree-shake unused
components from lazy MFE chunks.

### What is NOT here

- **`MEE_LAYOUT`** — owned by `@mesell/layout` (Phases 3–4). It is NOT in
  `MEE_UI_ALL`. Layout page primitives (`mee-page`, `mee-section`, etc.) are
  out of scope for this library.
- **Services** — `MeeToastService`, `MeeConfirmService` are providers.
- **Theme / presets** — `MeeSellPreset` and `provideMeeUi()` bootstrap the
  Aura theme; they are not aggregated.

See `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` for the
full phased decoupling plan and `frontend/tools/contracts/README.md` for the
FE boundary contract scanners.

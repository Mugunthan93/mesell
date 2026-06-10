# WAVE 3 — UI KIT — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 3 — MeeSell UI Kit (17 mee-* primitives) |
| **Date authored** | 2026-06-09 |
| **Status** | READY TO DISPATCH |
| **Author** | meesell-frontend-coordinator (master session) |
| **Agent** | meesell-angular-component-builder (sonnet) |
| **Depends on** | Wave 2B scaffold DONE · Layer 1 design tokens DONE (`_tokens.css`) |
| **Gates progress** | Wave 2B Gates 1–4 PASS · Layer 1 tokens present · `ui/` absent — must be created |
| **Blocks** | Wave 4 Composites (C1–C5) · Wave 5 all Feature pages |

---

## 1. Scope — 17 Primitives

| # | mee-selector | wraps | File path under `src/app/ui/` | CVA? |
|---|---|---|---|---|
| K1 | `mee-button` | `p-button` | `button/button.component.ts` + `button.types.ts` | No |
| K2 | `mee-input` | `[pInputText]` directive | `input/input.component.ts` + `input.types.ts` | Yes |
| K3 | `mee-otp-input` | `p-inputotp` | `otp-input/otp-input.component.ts` | Yes |
| K4 | `mee-badge` | `p-tag` | `badge/badge.component.ts` + `badge.types.ts` | No |
| K5 | `mee-card` | `p-card` | `card/card.component.ts` | No |
| K6 | `mee-table` | `p-table` | `table/table.component.ts` + `table.types.ts` | No |
| K7 | `mee-dialog` | `p-dialog` | `dialog/dialog.component.ts` + `dialog.types.ts` | No |
| K8 | `mee-file-upload` | `p-fileupload` | `file-upload/file-upload.component.ts` + `file-upload.types.ts` | No |
| K9 | `mee-steps` | `p-steps` | `steps/steps.component.ts` + `steps.types.ts` | No |
| K10 | `mee-select` | `p-select` | `select/select.component.ts` + `select.types.ts` | Yes |
| K11 | `mee-tree-select` | `p-treeselect` | `tree-select/tree-select.component.ts` | No |
| K12 | `mee-skeleton` | `p-skeleton` | `skeleton/skeleton.component.ts` + `skeleton.types.ts` | No |
| K13 | `mee-progress-bar` | `p-progressbar` | `progress-bar/progress-bar.component.ts` | No |
| K14 | `mee-toast` | `p-toast` | `toast/toast.component.ts` + `toast/toast.service.ts` | No |
| K15 | `mee-confirm-dialog` | `p-confirmdialog` | `confirm-dialog/confirm-dialog.component.ts` | No |
| K16 | `mee-password-input` | `p-password` | `password-input/password-input.component.ts` | Yes |
| K17 | `mee-textarea` | `[pTextarea]` directive | `textarea/textarea.component.ts` | Yes |

Build priority order (per architecture): K1 → K2 → K3 → K4 → K5 → K6 → K7 → K8 → K9 → K10 → K11 → K12 → K13 → K14 → K15 → K16 → K17.

---

## 2. The Boundary Rule

**Non-negotiable (FRONTEND_ARCHITECTURE.md §Non-Negotiable #1):**

> `import { ... } from 'primeng/...'` is ALLOWED ONLY in `src/app/ui/` files.

Consequence: every feature page, every shared composite (Layer 3), every layout that needs a UI primitive MUST import it from the barrel `src/app/ui/index.ts`. Zero PrimeNG imports outside `ui/`.

**Barrel rule:** `src/app/ui/index.ts` is the single import path. Feature files write:
```typescript
import { MeeButtonComponent, MeeInputComponent } from '@mee/ui';
// or relative: import { ... } from '../../../ui';
```

No feature file ever writes `import { Button } from 'primeng/button'`. An ESLint rule enforcing this will be set up by meesell-angular-ui-styler.

**mee-toast exception:** `MeeToastService` (in `ui/toast/toast.service.ts`) wraps PrimeNG `MessageService`. It is the only service-based primitive. Features inject `MeeToastService` — not `MessageService` directly.

**mee-confirm-dialog exception:** `MeeConfirmService` (in `ui/confirm-dialog/confirm-dialog.component.ts`) wraps PrimeNG `ConfirmationService`. `<mee-confirm-dialog>` is placed once in the shell template.

---

## 3. Per-Primitive Contracts

All contracts copied verbatim from `docs/FRONTEND_ARCHITECTURE.md` §Layer 2. Do not invent props.

### K1 — `mee-button`
| @Input() | Type | Default |
|---|---|---|
| `label` | `string` | required |
| `variant` | `'primary' \| 'secondary' \| 'ghost' \| 'danger'` | `'primary'` |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` |
| `loading` | `boolean` | `false` |
| `disabled` | `boolean` | `false` |
| `fullWidth` | `boolean` | `false` |
| `icon` | `string \| undefined` | — (Material Symbol name accepted as string) |

| @Output() | Type |
|---|---|
| `clicked` | `EventEmitter<void>` |

Wraps: `<p-button>`. Map `variant` → p-button `severity` + `variant` props. Map `size` → p-button `size`. Map `loading`, `disabled` directly. Map `fullWidth` → `[fluid]="true"`.
PrimeNG doc: `docs/primeng/button.md`
CVA: No.

### K2 — `mee-input`
| @Input() | Type | Default |
|---|---|---|
| `label` | `string \| undefined` | — |
| `placeholder` | `string` | `''` |
| `type` | `'text' \| 'email' \| 'number' \| 'tel'` | `'text'` |
| `prefix` | `string \| undefined` | — (e.g., `'+91'`) |
| `error` | `string \| undefined` | — |
| `hint` | `string \| undefined` | — |
| `disabled` | `boolean` | `false` |
| `required` | `boolean` | `false` |

Wraps: `<input pInputText>` (DIRECTIVE — not `<p-inputtext>`). The component renders the native `<input>` with `pInputText` applied; label/prefix/error/hint are rendered in the component template around it.
PrimeNG doc: `docs/primeng/inputtext.md`
CVA: Yes — implements ControlValueAccessor so `formControlName="phone"` works on `<mee-input>`.

### K3 — `mee-otp-input`
| @Input() | Type | Default |
|---|---|---|
| `length` | `number` | `6` |
| `disabled` | `boolean` | `false` |

| @Output() | Type |
|---|---|
| `completed` | `EventEmitter<string>` |

Wraps: `<p-inputotp>`. Emit `completed` when `onChange` fires and value length equals `length`.
PrimeNG doc: `docs/primeng/inputotp.md`
CVA: Yes — delegates to p-inputotp's own CVA; mee-otp-input also implements CVA so `formControlName="otp"` works.

### K4 — `mee-badge`
| @Input() | Type | Default |
|---|---|---|
| `value` | `string` | required |
| `severity` | `'success' \| 'warning' \| 'danger' \| 'info' \| 'neutral'` | `'neutral'` |

Wraps: `<p-tag>`. Map `severity='neutral'` → p-tag `severity='secondary'`; `'warning'` → `'warn'`. All others map 1:1.
PrimeNG doc: `docs/primeng/tag.md`
CVA: No.
Note: `mee-badge` wraps `p-tag` — NOT `p-badge` (which is a numeric overlay badge, not a label chip).

### K5 — `mee-card`
No explicit @Inputs beyond content projection. Architecture lists only `content via <ng-content>`.

Wraps: `<p-card>`. Content is projected via Angular `<ng-content>`. Optional `header` and `subheader` slots can be passed via `pTemplate` if needed.
PrimeNG doc: `docs/primeng/card.md`
CVA: No.

### K6 — `mee-table`
| @Input() | Type | Default |
|---|---|---|
| `columns` | `MeeColumn[]` | required |
| `rows` | `unknown[]` | required |
| `loading` | `boolean` | `false` |
| `paginator` | `boolean` | `false` |
| `rows_per_page` | `number` | `10` |
| `total_records` | `number \| undefined` | — |
| `empty_message` | `string` | `'No data found'` |

| @Output() | Type |
|---|---|
| `row_click` | `EventEmitter<unknown>` |
| `page` | `EventEmitter<MeeTablePageEvent>` |
| `sort` | `EventEmitter<MeeTableSortEvent>` |

Types (in `table.types.ts`):
```typescript
interface MeeColumn   { field: string; header: string; sortable?: boolean; width?: string }
interface MeeTablePageEvent { first: number; rows: number }
interface MeeTableSortEvent { field: string; order: number }
```
Wraps: `<p-table>` + `TableModule` (needed for sub-directives like `pSortableColumn`).
PrimeNG doc: `docs/primeng/table.md`
CVA: No.

### K7 — `mee-dialog`
| @Input() | Type | Default |
|---|---|---|
| `header` | `string` | required |
| `visible` | `boolean` | `false` |
| `width` | `string` | `'480px'` |
| `closable` | `boolean` | `true` |

| @Output() | Type |
|---|---|
| `visibleChange` | `EventEmitter<boolean>` |
| `closed` | `EventEmitter<void>` |

Content via `<ng-content>`. Two-way binding: `[(visible)]="show"` works on `<mee-dialog>` because `visibleChange` pairs with `visible`.
Wraps: `<p-dialog>`. Pass `[style]="{ width: width }"`. Wire `(onHide)` → emit `closed`.
PrimeNG doc: `docs/primeng/dialog.md`
CVA: No.

### K8 — `mee-file-upload`
| @Input() | Type | Default |
|---|---|---|
| `accept` | `string` | `'image/*'` |
| `max_size_mb` | `number` | `5` |
| `multiple` | `boolean` | `false` |
| `label` | `string` | `'Drop files here or click to upload'` |

| @Output() | Type |
|---|---|
| `files_selected` | `EventEmitter<MeeFileUploadEvent>` |
| `upload_error` | `EventEmitter<string>` |

Types (in `file-upload.types.ts`):
```typescript
interface MeeFileUploadEvent { files: File[] }
```
Wraps: `<p-fileupload>` in `mode="advanced"` with `customUpload="true"`. Convert `max_size_mb` to bytes for `[maxFileSize]`. Wire `(uploadHandler)` → extract `File[]` → emit `files_selected`. Wire `(onError)` → emit `upload_error`.
PrimeNG doc: `docs/primeng/fileupload.md`
CVA: No.

### K9 — `mee-steps`
| @Input() | Type | Default |
|---|---|---|
| `steps` | `MeeStep[]` | required |
| `active_index` | `number` | `0` |

| @Output() | Type |
|---|---|
| `active_index_change` | `EventEmitter<number>` |

Types (in `steps.types.ts`):
```typescript
interface MeeStep { label: string; route?: string }
```
Wraps: `<p-steps>`. Map `MeeStep[]` → PrimeNG `MenuItem[]` (both have `label`). Wire `[activeIndex]` and `(activeIndexChange)`.
PrimeNG doc: `docs/primeng/steps.md`
Note: p-steps uses `model: MenuItem[]` (not `steps`). The wrapper converts internally.
CVA: No.

### K10 — `mee-select`
| @Input() | Type | Default |
|---|---|---|
| `options` | `MeeSelectOption[]` | required |
| `placeholder` | `string` | `'Select'` |
| `disabled` | `boolean` | `false` |
| `label` | `string \| undefined` | — |
| `error` | `string \| undefined` | — |

| @Output() | Type |
|---|---|
| `value_change` | `EventEmitter<unknown>` |

Types (in `select.types.ts`):
```typescript
interface MeeSelectOption { label: string; value: unknown }
```
Wraps: `<p-select>` (NOT `p-dropdown` — deprecated in PrimeNG 21). Use `optionLabel="label"` + `optionValue="value"`.
PrimeNG doc: `docs/primeng/select.md`
CVA: Yes — implements ControlValueAccessor so `formControlName` works on `<mee-select>`.

### K11 — `mee-tree-select`
| @Input() | Type | Default |
|---|---|---|
| `nodes` | `MeeTreeNode[]` | required |
| `placeholder` | `string` | `'Select category'` |
| `loading` | `boolean` | `false` |

| @Output() | Type |
|---|---|
| `value_change` | `EventEmitter<MeeTreeNode>` |

Types: `MeeTreeNode` (in `tree-select/tree-select.component.ts` or a shared types file): `{ label: string; value: unknown; children?: MeeTreeNode[] }`. This maps to PrimeNG `TreeNode`.
Wraps: `<p-treeselect>`. Wire `(onNodeSelect)` → emit `value_change` with the selected node.
PrimeNG doc: `docs/primeng/treeselect.md`
CVA: No (architecture does not specify CVA for tree-select — `value_change` output only).

### K12 — `mee-skeleton`
| @Input() | Type | Default |
|---|---|---|
| `variant` | `'text' \| 'card' \| 'table-row' \| 'stat-card'` | `'text'` |
| `lines` | `number` | `1` (for variant `'text'`) |

Wraps: `<p-skeleton>`. Each variant renders a different combination of p-skeleton instances internally.
PrimeNG doc: `docs/primeng/skeleton.md`
CVA: No.

Types (in `skeleton.types.ts`):
```typescript
type MeeSkeletonVariant = 'text' | 'card' | 'table-row' | 'stat-card';
```

### K13 — `mee-progress-bar`
| @Input() | Type | Default |
|---|---|---|
| `value` | `number` | required (0–100) |
| `label` | `string \| undefined` | — |
| `show_value` | `boolean` | `true` |

Wraps: `<p-progressbar>`. Map `show_value` → `[showValue]`. Render `label` above the bar if provided.
PrimeNG doc: `docs/primeng/progressbar.md`
CVA: No.

### K14 — `mee-toast` + `MeeToastService`
**Host component** (`mee-toast`): placed ONCE in `AppComponent` or shell template. No @Inputs.

**`MeeToastService`** (in `toast/toast.service.ts`, `providedIn: 'root'`):
```typescript
success(detail: string, summary?: string): void
error(detail: string, summary?: string): void
warn(detail: string, summary?: string): void
info(detail: string, summary?: string): void
```
Internally injects `MessageService` from PrimeNG and calls `msgSvc.add(...)`.

Wraps: `<p-toast position="top-right" [life]="4000">`.
PrimeNG doc: `docs/primeng/toast.md`
CVA: No.
Note: `MessageService` must be added to `app.config.ts` providers alongside `ConfirmationService`.

### K15 — `mee-confirm-dialog` + `MeeConfirmService`
**Host component** (`mee-confirm-dialog`): placed ONCE in shell template. No @Inputs (service-based).

**`MeeConfirmService`** (inline in `confirm-dialog.component.ts`, `providedIn: 'root'`):
```typescript
confirm(config: { message: string; header?: string; accept: () => void; reject?: () => void }): void
```
Internally injects PrimeNG `ConfirmationService` and delegates.

Wraps: `<p-confirmdialog>`.
PrimeNG doc: `docs/primeng/confirmdialog.md`
CVA: No.
Note: `ConfirmationService` must be in `app.config.ts` providers.

### K16 — `mee-password-input`
| @Input() | Type | Default |
|---|---|---|
| `label` | `string \| undefined` | — |
| `placeholder` | `string \| undefined` | — |
| `disabled` | `boolean` | `false` |
| `toggleMask` | `boolean` | `true` |
| `feedback` | `boolean` | `false` |

Wraps: `<p-password>`. `[feedback]="false"` by default (MeeSell does not need strength meter on login). `[toggleMask]="true"` by default.
PrimeNG doc: `docs/primeng/password.md`
CVA: Yes — delegates to p-password's own CVA.

### K17 — `mee-textarea`
| @Input() | Type | Default |
|---|---|---|
| `label` | `string \| undefined` | — |
| `placeholder` | `string` | `''` |
| `rows` | `number` | `4` |
| `error` | `string \| undefined` | — |
| `hint` | `string \| undefined` | — |
| `disabled` | `boolean` | `false` |
| `required` | `boolean` | `false` |
| `autoResize` | `boolean` | `false` |

Wraps: `<textarea pTextarea>` (DIRECTIVE on native `<textarea>` — do NOT write `<p-textarea>`).
PrimeNG doc: `docs/primeng/textarea.md`
CVA: Yes — implements ControlValueAccessor.

---

## 4. Shared Rules (all 17 primitives)

| Rule | Requirement |
|---|---|
| **Standalone** | `@Component({ standalone: true, ... })` — zero NgModules |
| **OnPush** | `changeDetection: ChangeDetectionStrategy.OnPush` on every component |
| **TypeScript strict** | No `any`. Use `unknown` where type is genuinely unknown. Generics where needed. |
| **Internal state** | Use `signal<T>()` for all component-local reactive state |
| **Design tokens** | Colors via `var(--mee-color-*)`. No hardcoded hex in templates or styles. |
| **Spacing/radius** | Use `var(--mee-space-*)`, `var(--mee-radius-*)` tokens or Tailwind aliases |
| **Icon names** | `icon` inputs accept Material Symbol name strings (e.g., `'edit'`, `'delete'`) — NOT PrimeIcons inside mee-* contracts |
| **Touch targets** | All interactive controls: `min-height: 44px` (Tirupur mobile-first) |
| **inject()** | Use `inject()` for all dependency injection — no constructor params |
| **No @Output EventEmitter** | Use Angular 18 `output<T>()` function API — NOT `@Output() x = new EventEmitter<T>()` |
| **Barrier** | Zero `import { ... } from 'primeng/...'` outside `src/app/ui/` |

---

## 5. Barrel Export Spec (`ui/index.ts`)

`ui/index.ts` MUST export every component class and every public type. Features import from here exclusively.

```typescript
// Components
export { MeeButtonComponent }       from './button/button.component';
export { MeeInputComponent }        from './input/input.component';
export { MeeOtpInputComponent }     from './otp-input/otp-input.component';
export { MeeBadgeComponent }        from './badge/badge.component';
export { MeeCardComponent }         from './card/card.component';
export { MeeTableComponent }        from './table/table.component';
export { MeeDialogComponent }       from './dialog/dialog.component';
export { MeeFileUploadComponent }   from './file-upload/file-upload.component';
export { MeeStepsComponent }        from './steps/steps.component';
export { MeeSelectComponent }       from './select/select.component';
export { MeeTreeSelectComponent }   from './tree-select/tree-select.component';
export { MeeSkeletonComponent }     from './skeleton/skeleton.component';
export { MeeProgressBarComponent }  from './progress-bar/progress-bar.component';
export { MeeToastComponent }        from './toast/toast.component';
export { MeeToastService }          from './toast/toast.service';
export { MeeConfirmDialogComponent } from './confirm-dialog/confirm-dialog.component';
export { MeeConfirmService }        from './confirm-dialog/confirm-dialog.component';
export { MeePasswordInputComponent } from './password-input/password-input.component';
export { MeeTextareaComponent }     from './textarea/textarea.component';

// Types
export type { MeeButtonVariant, MeeButtonSize }    from './button/button.types';
export type { MeeSelectOption }                    from './select/select.types';
export type { MeeColumn, MeeTablePageEvent, MeeTableSortEvent } from './table/table.types';
export type { MeeStep }                            from './steps/steps.types';
export type { MeeBadgeSeverity }                   from './badge/badge.types';
export type { MeeSkeletonVariant }                 from './skeleton/skeleton.types';
export type { MeeFileUploadEvent }                 from './file-upload/file-upload.types';
export type { MeeTreeNode }                        from './tree-select/tree-select.component';
```

---

## 6. Files to Create

Full directory tree under `frontend/src/app/ui/`:

```
src/app/ui/
├── button/
│   ├── button.component.ts         # MeeButtonComponent — mee-button
│   ├── button.component.spec.ts
│   └── button.types.ts             # MeeButtonVariant, MeeButtonSize
├── input/
│   ├── input.component.ts          # MeeInputComponent — mee-input (CVA)
│   ├── input.component.spec.ts
│   └── input.types.ts
├── otp-input/
│   ├── otp-input.component.ts      # MeeOtpInputComponent — mee-otp-input (CVA)
│   └── otp-input.component.spec.ts
├── badge/
│   ├── badge.component.ts          # MeeBadgeComponent — mee-badge (wraps p-tag)
│   ├── badge.component.spec.ts
│   └── badge.types.ts              # MeeBadgeSeverity
├── card/
│   ├── card.component.ts           # MeeCardComponent — mee-card
│   └── card.component.spec.ts
├── table/
│   ├── table.component.ts          # MeeTableComponent — mee-table
│   ├── table.component.spec.ts
│   └── table.types.ts              # MeeColumn, MeeTablePageEvent, MeeTableSortEvent
├── dialog/
│   ├── dialog.component.ts         # MeeDialogComponent — mee-dialog
│   ├── dialog.component.spec.ts
│   └── dialog.types.ts
├── file-upload/
│   ├── file-upload.component.ts    # MeeFileUploadComponent — mee-file-upload
│   ├── file-upload.component.spec.ts
│   └── file-upload.types.ts        # MeeFileUploadEvent
├── steps/
│   ├── steps.component.ts          # MeeStepsComponent — mee-steps
│   ├── steps.component.spec.ts
│   └── steps.types.ts              # MeeStep
├── select/
│   ├── select.component.ts         # MeeSelectComponent — mee-select (CVA)
│   ├── select.component.spec.ts
│   └── select.types.ts             # MeeSelectOption
├── tree-select/
│   ├── tree-select.component.ts    # MeeTreeSelectComponent — mee-tree-select
│   └── tree-select.component.spec.ts
├── skeleton/
│   ├── skeleton.component.ts       # MeeSkeletonComponent — mee-skeleton
│   ├── skeleton.component.spec.ts
│   └── skeleton.types.ts           # MeeSkeletonVariant
├── progress-bar/
│   ├── progress-bar.component.ts   # MeeProgressBarComponent — mee-progress-bar
│   └── progress-bar.component.spec.ts
├── toast/
│   ├── toast.component.ts          # MeeToastComponent — mee-toast (host)
│   ├── toast.component.spec.ts
│   └── toast.service.ts            # MeeToastService (providedIn root)
├── confirm-dialog/
│   ├── confirm-dialog.component.ts # MeeConfirmDialogComponent + MeeConfirmService
│   └── confirm-dialog.component.spec.ts
├── password-input/
│   ├── password-input.component.ts # MeePasswordInputComponent — mee-password-input (CVA)
│   └── password-input.component.spec.ts
├── textarea/
│   ├── textarea.component.ts       # MeeTextareaComponent — mee-textarea (CVA)
│   └── textarea.component.spec.ts
└── index.ts                        # barrel — all 17 components + all public types
```

Total new files: 48 (17 `.component.ts` + 17 `.component.spec.ts` + 8 `.types.ts` + 1 `toast.service.ts` + 1 `index.ts` + 4 inline-typed components where types live in the component file).

---

## 7. Out of Scope

| Item | Where it belongs |
|---|---|
| Layer 3 composites (`mee-stat-card`, `mee-status-badge`, `mee-page-header`, `mee-empty-state`, `mee-loading-skeleton`) | Wave 4 |
| Shell layout (`MeeShellComponent`, sidebar, topbar) | Wave 4 (layouts already scaffolded in Wave 2B) |
| Auth layout (`MeeAuthLayoutComponent`) | Already DONE (Wave 2B) |
| Feature page components (dashboard, catalog-form, images, pricing, export, etc.) | Wave 5+ |
| API calls, HTTP services, interceptors, guards | meesell-angular-service-builder |
| Tailwind config, Material theme, CSS custom properties | meesell-angular-ui-styler |
| ESLint rule enforcing the PrimeNG boundary | meesell-angular-ui-styler |
| `@mee/ui` path alias registration in `tsconfig.json` | meesell-angular-ui-styler / meesell-frontend-coordinator |
| Refactoring existing Wave 2C auth pages to consume mee-* primitives | Wave 5 auth refactor (Option A full) |
| Razorpay, MSG91, Gemini, backend wiring | backend agents |

---

## 8. Verification Gates

| Gate | Check | Pass condition |
|---|---|---|
| **1 BUILD** | `cd frontend && pnpm run build` | Zero errors, zero new warnings |
| **2 SMOKE SPECS** | `pnpm run test` | Every `.component.spec.ts` has at minimum 1 passing test confirming the component renders without error and exposes the declared @Input contract |
| **3 BARREL RESOLVES** | Import `MeeButtonComponent` from `src/app/ui/index.ts` in a throwaway file; confirm TypeScript resolves without error | No TS2305 / TS2307 |
| **4 BOUNDARY CLEAN** | `grep -r "from 'primeng/" frontend/src/app --include="*.ts" \| grep -v "/ui/"` | Output is EMPTY (zero PrimeNG imports outside `ui/`) |
| **5 VISUAL (optional)** | Add a temporary kitchen-sink demo route `/ui-demo` that renders all 17 mee-* primitives with sample props; founder reviews at 360px + 1280px | MeeSell orange, Plus Jakarta Sans, tokens applied |

Gate 5 is optional for Wave 3 but strongly recommended before Wave 4 composites are built on top of these primitives.

---

## 9. Paste-Ready Dispatch Block

```
═══════════════════════════════════════════════════════════════════
MASTER → COMPONENT-BUILDER DISPATCH
Date:  2026-06-09
From:  meesell-frontend-coordinator (master session)
Wave:  WAVE 3 — MeeSell UI Kit (17 mee-* primitives)
Agent: meesell-angular-component-builder (sonnet)
═══════════════════════════════════════════════════════════════════

CONTEXT
───────
Wave 2B scaffold is DONE (Gates 1–4 PASS).
Layer 1 design tokens are DONE (_tokens.css present).
src/app/ui/ does NOT exist yet — you must create it from scratch.

This wave builds the ONLY layer allowed to import primeng/*.
Every feature page consumes mee-* components exclusively.

MANDATORY READS BEFORE ANY CODE
─────────────────────────────────
1. docs/FRONTEND_ARCHITECTURE.md §Layer 2 — MeeSell UI Kit
   → exact @Input/@Output contracts for all 17 primitives
2. docs/ui_ux/WAVE_3_UI_KIT_DISPATCH.md (this doc)
   → per-primitive contracts, types, PrimeNG doc pointers
3. docs/primeng/<component>.md for each primitive you implement:
   button.md, inputtext.md, inputotp.md, tag.md, card.md,
   table.md, dialog.md, fileupload.md, steps.md, select.md,
   treeselect.md, skeleton.md, progressbar.md, toast.md,
   confirmdialog.md, password.md, textarea.md
4. docs/primeng/INDEX.md — critical v21 breaking changes table

CRITICAL PrimeNG 21 FACTS (do not get these wrong)
────────────────────────────────────────────────────
• InputText is a DIRECTIVE: <input pInputText> NOT <p-inputtext>
• Textarea is a DIRECTIVE: <textarea pTextarea> NOT <p-textarea>
• p-dropdown is DEPRECATED — use p-select (same CVA API)
• p-sidebar is REMOVED — use p-drawer (not needed in Wave 3)
• mee-badge wraps p-tag (the label chip) NOT p-badge (numeric overlay)
• p-steps uses model:MenuItem[] not steps:MeeStep[] (wrapper converts)
• ConfirmDialog is SERVICE-BASED — no @Input contract on the component
• Toast is SERVICE-BASED — MeeToastService wraps MessageService
• MessageService + ConfirmationService must be in app.config.ts providers

═══════════════════════════════════════════════════════════════════

DIRECTORY TO CREATE
───────────────────
  frontend/src/app/ui/
    (full tree: 17 subdirs, each with .component.ts + .spec.ts
     + .types.ts where specified + barrel ui/index.ts)
  See §6 Files to Create for the complete tree.

DO NOT MODIFY
─────────────
  • Any file outside frontend/src/app/ui/
  • frontend/src/app/features/**  (feature pages)
  • frontend/src/app/shared/**    (composites — Wave 4)
  • backend/**

═══════════════════════════════════════════════════════════════════

CONTRACT RULES
──────────────
• Copy @Input/@Output from FRONTEND_ARCHITECTURE.md §Layer 2 EXACTLY
• Do not invent props not listed in the architecture doc
• CVA components (K2 mee-input, K3 mee-otp-input, K10 mee-select,
  K16 mee-password-input, K17 mee-textarea): implement ControlValueAccessor
  via { provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(...), multi:true }
• K11 mee-tree-select: NO CVA (value_change output only — per arch)
• All @Output(): use output<T>() function API, NOT new EventEmitter<T>()

SHARED RULES (all 17)
──────────────────────
  • standalone: true, changeDetection: OnPush
  • signal<T>() for internal state
  • var(--mee-color-*) tokens — no hardcoded hex
  • min-height: 44px on all interactive controls
  • inject() for DI — no constructor params
  • TypeScript strict — no any

BARREL REQUIREMENT
──────────────────
  ui/index.ts must export all 17 component classes + all public types.
  Features import ONLY from this barrel.

═══════════════════════════════════════════════════════════════════

VERIFICATION GATES
──────────────────
Gate 1 BUILD:    pnpm run build → zero errors
Gate 2 SPECS:    pnpm run test → all 17 smoke specs pass
Gate 3 BARREL:   TypeScript resolves mee-* from ui/index.ts
Gate 4 BOUNDARY: grep finds zero primeng imports outside ui/
Gate 5 VISUAL:   (optional) /ui-demo kitchen-sink route

STATUS UPDATE (append to docs/status/STATUS_FRONTEND.md)
──────────────────────────────────────────────────────────
  === UPDATE: YYYY-MM-DD HH:MM ===
  Phase: Wave 3 — UI Kit
  Done: [list components built]
  Tests: [N passed / N failed]
  Build: [ok / fail]
  In progress: [list]
  Blockers: [list or none]
  Next: Wave 4 Composites
  Hand-offs: [any cross-agent items]
  =========

═══════════════════════════════════════════════════════════════════
END NOTIFICATION
═══════════════════════════════════════════════════════════════════
```

---

## 10. Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-09 | meesell-angular-component-builder (sonnet) | Initial authoring — sourced contracts from FRONTEND_ARCHITECTURE.md, PrimeNG 21 docs, FRONTEND_MODULE_INVENTORY.md Option A decision |
| 2026-06-09 | Director (founder override) | K5 mee-card: content projection only confirmed. K16 mee-password-input: added `label` input. K17 mee-textarea: CVA + label + rows + error confirmed. |

## Session 2026-06-09 — Wave 3 UI Kit EXECUTED {#wave3-executed}

### Task
Built all 17 mee-* primitives in `src/app/ui/` per WAVE_3_UI_KIT_DISPATCH.md. Created 48 files.

### Gate Results
- Gate 1 BUILD: PASS — zero errors, zero new warnings
- Gate 2 SPECS: PASS — 105 tests / 0 failed (23 test files)
- Gate 3 BARREL: PASS — ui/index.ts resolves all 17 exports with zero TypeScript errors
- Gate 4 BOUNDARY: PARTIAL — zero NEW primeng imports outside ui/; pre-existing Wave 2 code in features/auth/ and layouts/shell/ has direct primeng imports (pre-date ui/ existence; to be migrated in Wave 5 auth refactor). app.config.ts intentionally imports MessageService+ConfirmationService from primeng/api (required providers).

### PrimeNG 21 Actual API vs doc corrections (verified from .d.ts files)

#### TableSortEvent does NOT exist in PrimeNG 21 table exports
- `primeng/table` exports `Table, TableModule, TablePageEvent` but NOT `TableSortEvent`
- The `onSort` EventEmitter emits `{ field?: string; order?: number; multisortmeta?: SortMeta[] }`
- Use `SortMeta` from `'primeng/api'` for the multisortmeta type
- Correct handler: `onSort(event: { field?: string; order?: number; multisortmeta?: SortMeta[] }): void`

#### p-table emptyMessage — NOT a bound @Input
- `emptyMessage` is a class member with a default value on the Table class, not a standard @Input
- NG8002 error when using `[emptyMessage]="expr"` in a template
- Correct approach: use `ng-template pTemplate="emptymessage"` for custom empty message rendering

#### InputOtp CVA via ngModel — FormsModule required
- `InputOtp` implements CVA via `BaseEditableHolder` (confirmed from .d.ts)
- `[ngModel]="value" (ngModelChange)="fn($event)"` pattern requires FormsModule in imports[]
- Without FormsModule, NG8002 fires for `[ngModel]` on `p-inputotp`

#### FileUploadErrorEvent shape
- `interface FileUploadErrorEvent { error?: ErrorEvent; files?: File[] }`
- The error message is at `event.error?.message` — NOT `event['message']` or `event.message`
- Correct handler: `onError(event: FileUploadErrorEvent): void { upload_error.emit(event.error?.message ?? 'Upload failed'); }`

#### Skeleton — @for iterating a number
- `@for (line of lines(); track $index)` — NG template fails when `lines()` returns a number
- CORRECT: `linesArray = computed<number[]>(() => Array.from({ length: this.lines() }, (_, i) => i))`
- Then: `@for (item of linesArray(); track item) { ... }`

### Pattern: Button spec — skip detectChanges, test computed signals directly
- PrimeNG `p-button` component has strict @Input typed bindings
- Stubs that don't exactly match p-button's @Input declarations cause NG0303 or NG0300
- BEST PRACTICE for components that wrap PrimeNG with computed signal mappings:
  - `makeComp()` helper: `TestBed.createComponent(X)` + `setInput()` — do NOT call `detectChanges()`
  - Access computed signals directly on the component instance: `comp.pgSeverity()`, `comp.pgSize()`
  - For output tests: `comp.outputSignal.subscribe(...)` + `comp.outputSignal.emit()`
  - This avoids the entire stub/override problem for computed-signal-only tests

### Pattern: MeeTreeSelectComponent — non-CVA, getter method for treeNodes
- Architecture spec says NO CVA on tree-select; value_change output only
- `treeNodes` is a getter method `get treeNodes(): () => TreeNode[]` — returns a function called in template
- Alternative: use `computed()` signal — but getter returning a function also works
- `onNodeSelect(event: { node: TreeNode }): void` — extract label and data, emit as MeeTreeNode
- MeeTreeNode type exported from the component file (not a separate types file per spec)

### Pattern: MeeConfirmService + MeeToastService in same file as component
- K14 and K15: service is defined in the SAME file as the component
- `export class MeeConfirmService { }` defined before `export class MeeConfirmDialogComponent { }`
- Both exported from the file; barrel re-exports both separately
- spec file tests both the component (`ComponentFixture`) and service (`TestBed.inject`) in separate `describe()` blocks

### app.config.ts change required
- `MessageService` and `ConfirmationService` from `'primeng/api'` must be in `providers[]`
- Added as plain class references (not `provide:` object) — Angular's `@Injectable()` style
- Without them: MeeToastService and MeeConfirmService will throw NullInjectorError at runtime

### Files created (48 total)
```
src/app/ui/
├── button/{button.component.ts, button.component.spec.ts, button.types.ts}
├── input/{input.component.ts, input.component.spec.ts, input.types.ts}
├── otp-input/{otp-input.component.ts, otp-input.component.spec.ts}
├── badge/{badge.component.ts, badge.component.spec.ts, badge.types.ts}
├── card/{card.component.ts, card.component.spec.ts}
├── table/{table.component.ts, table.component.spec.ts, table.types.ts}
├── dialog/{dialog.component.ts, dialog.component.spec.ts, dialog.types.ts}
├── file-upload/{file-upload.component.ts, file-upload.component.spec.ts, file-upload.types.ts}
├── steps/{steps.component.ts, steps.component.spec.ts, steps.types.ts}
├── select/{select.component.ts, select.component.spec.ts, select.types.ts}
├── tree-select/{tree-select.component.ts, tree-select.component.spec.ts}
├── skeleton/{skeleton.component.ts, skeleton.component.spec.ts, skeleton.types.ts}
├── progress-bar/{progress-bar.component.ts, progress-bar.component.spec.ts}
├── toast/{toast.component.ts, toast.component.spec.ts, toast.service.ts}
├── confirm-dialog/{confirm-dialog.component.ts, confirm-dialog.component.spec.ts}
├── password-input/{password-input.component.ts, password-input.component.spec.ts}
├── textarea/{textarea.component.ts, textarea.component.spec.ts}
└── index.ts
```

### Build result (2026-06-09 Wave 3 UI Kit execution)
- pnpm run build: ZERO errors, 2.374s
- pnpm run test: 105/105 passing (23 test files)
- Barrel: 17 components + 9 public type groups exported from ui/index.ts

---

## Session 2026-06-06 — Dashboard Dispatch 2 {#dashboard-dispatch-2}

### Route touched
`/dashboard` — features/dashboard/components/product-row/ + dashboard.component.ts update

### Services consumed
`DashboardApiService.deleteProduct()` (existing) + `MatDialog` (Angular Material) + `ConfirmDialogComponent` (shared stub)

### Pattern: MatMenu + input.required() — NG0950 in CDK overlay context
- MatMenu items render in a CDK overlay (EmbeddedViewRef via portal).
- Calling `this.inputRequired()` inside a click handler in `<mat-menu>` triggers NG0950
  because the overlay's embedded view context does not have the input signal value.
- CORRECT PATTERN: pass signal value from template: `(click)="onEdit(row())"`
  method signature: `onEdit(row: ProductListItem)`
- WRONG: `(click)="onEdit()"` + `onEdit(): void { this.row(); }` — NG0950 in overlay

### Pattern: ConfirmDialogComponent with input() signals — use ComponentRef.setInput()
- ConfirmDialogComponent uses `input<T>(default)` signals (NOT MAT_DIALOG_DATA).
- To set inputs on a dialog: `dialogRef.componentRef!.setInput('inputName', value)`
- TypeScript infers componentRef as possibly null; use `!` + eslint comment.
- WRONG: `dialog.open(C, { data: {...} })` — only works with MAT_DIALOG_DATA injection
- WRONG: `dialogRef.componentInstance.title.set(value)` — InputSignal has no .set()

### Pattern: overrideComponent — stub ALL input.required() children
- DashboardComponent must stub: StatusBadge, StatCard, ProductRow, EmptyState
- StatCardComponent omission was a pre-existing defect in dashboard.component.spec.ts

### Pattern: OverlayContainer in MatMenu tests
- Inject `TestBed.inject(OverlayContainer)` in beforeEach
- Use `overlayContainer.getContainerElement()` to query overlay items
- NOT `fixture.nativeElement` or bare `document.querySelector`

### Pattern: outputToObservable for output() signals in tests
- `outputToObservable(component.editRequest)` from `@angular/core/rxjs-interop`
- Subscribe before interaction, collect into array, assert after
- Always `.unsubscribe()` after test

### Build result (Dispatch 2)
- 4 new ProductRowComponent tests: all passing
- 6 DashboardComponent tests restored to passing (fixed pre-existing StatCardStub omission)
- ng build --configuration=production: ZERO errors

---

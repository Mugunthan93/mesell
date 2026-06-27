## Session 2026-06-06 — Dashboard Dispatch 1 {#dashboard-dispatch-1}

### Route touched
`/dashboard` — features/dashboard/

### Services consumed
`DashboardApiService` (own, fixed this dispatch) + `ErrorService` (core) + `ApiClient` (core)

### Pattern: DashboardApiService (feature-scoped, corrected)
- GET /api/v1/products params: `page`, `limit`, `status_filter`, `search`
  (old scaffold had `status` + `q` — both wrong per §13.B.1)
- Response: `DashboardResponse.products` (NOT `data`), includes `profile_completeness`
- `@Injectable()` NO `providedIn: 'root'` — provided via `dashboard.routes.ts providers:[]`
- Always add `providers: [FeatureApiService]` to the route config when creating feature-scoped services

### Pattern: MatTable with signal data source
- `[dataSource]="products()"` — call the signal to get the array value
- `displayedColumns: string[]` (NOT `as const` — breaks MatTable column type checking)
- Row click nav: `(click)="navigateToEdit(row)"` + keyboard: `tabindex=0`, `(keydown.enter)`, `(keydown.space)`
- `product_id` is snake_case on ProductListItem — use `row.product_id` in router.navigate()

### Pattern: Debounced search in constructor
Use `takeUntilDestroyed()` from `@angular/core/rxjs-interop` in the constructor:
```typescript
constructor() {
  this.searchCtrl.valueChanges
    .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed())
    .subscribe(value => { ... });
}
```
This is preferred over `ngOnDestroy` + Subscription.unsubscribe() for OnPush components.

### Pattern: NG0950 in mat-table tests — overrideComponent stub
When testing components with mat-table + child components using `input.required()`:
- `NO_ERRORS_SCHEMA` does NOT suppress NG0950 (runtime signal error, not template error)
- Correct fix: `TestBed.overrideComponent(ParentComponent, { remove: { imports: [RealChild] }, add: { imports: [StubChild] } })`
- Stub: `@Component({ selector: 'mee-status-badge', standalone: true, template: '<span>{{status}}</span>' }) class StatusBadgeStub { status = ''; }`
- TranslocoTestingModule goes in `imports:[]` of configureTestingModule, NOT providers
- provideAnimationsAsync('noop') goes in providers (without arg causes invalid provider error)

### Pattern: Fake timers for debounce tests
Use `vi.useFakeTimers()` + `vi.advanceTimersByTime(n)` (Vitest native).
Do NOT use `fakeAsync`/`tick` from Angular — zone-testing.js is not loaded in the vitest setup.
Always `vi.useRealTimers()` in afterEach.

### Pattern: i18n helper method for conditional strings
When a template expression would be `{{ row.name ?? ('key' | transloco) }}` (mixing null-coalesce
with pipe), extract to a component method instead:
```typescript
displayName(row: ProductListItem): string {
  return row.name || this.transloco.translate('dashboard.table.untitled');
}
```
The `TranslocoService` must be injected as `private readonly` (accessible in the class).

### Build result
- dashboard-component lazy chunk: 169.82 KB raw / 30.57 KB gzip
- All 91 vitest tests pass; 6 new dashboard tests
- Production build: ZERO errors

---

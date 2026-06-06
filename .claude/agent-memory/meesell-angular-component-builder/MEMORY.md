# Memory — meesell-angular-component-builder

## Agent Identity
Angular 18 component specialist for MeeSell. Owns 10 page components + shared UI components. Standalone, OnPush, Reactive Forms, Tailwind + Material. Decentralized memory ecosystem.

## MEMORY.md Index
- [Session 2026-06-06 — Profile feature Dispatch 1](#session-2026-06-06)
- [Session 2026-06-06 — Dashboard Dispatch 1](#dashboard-dispatch-1)

---

## Session 2026-06-06 — Profile feature Dispatch 1 {#session-2026-06-06}

### Route touched
`/profile` — features/account/profile/

### Services consumed
`ProfileApiService` (own, created this dispatch) + `ErrorService` (core) + `ApiClient` (core)

### Pattern: Component-scoped API service (not providedIn root)
- `ProfileApiService` uses `@Injectable()` with NO `providedIn` — scoped to the route's `providers:[]` array.
- This matches `AccountApiService` scoping. The pattern is: lazy-routed features tree-shake their API service with the route chunk.
- HAND-OFF NOTE: `account.routes.ts` must add `providers: [ProfileApiService]` to the profile route. That is coordinator/service-builder scope, not component-builder scope.

### Pattern: Correct backend shape vs core model drift
- `core/models/seller-profile.model.ts` has WRONG field names (legalName, gstNumber, businessAddress, superCategoryIds: UUID[]) that do not match BACKEND_ARCH §8.E LOCKED shape.
- Solution: defined inline `SellerProfileCorrect` interface in `profile-api.service.ts` with the correct snake_case fields and documented with `TODO(cross-cutting)` comment directing the fix.
- DO NOT import `SellerProfile` from `@core/models/seller-profile.model` until cross-cutting fixes the model.

### Pattern: 404 as valid state in ngOnInit
- `getProfile()` can 404 when seller has no profile yet (first-time seller).
- Handled with `catchError` in `ngOnInit` — check `(err as { status?: number })?.status === 404`, set `loading.set(false)` and return `EMPTY` without calling `errorService.showError()`.
- All other error statuses: call `errorService.showError()` + `loading.set(false)` + return `EMPTY`.

### Pattern: optional pincode validator
- Angular's built-in `Validators.pattern(/^\d{6}$/)` fails on empty string — wrong for optional fields.
- Solution: custom `optionalPincodeValidator` function that returns null when value is empty/null, only checks the pattern when a value is present.

### Pattern: Vitest component test with TranslocoPipe
- `TranslocoPipe` in the component's `imports[]` requires the full transloco DI tree to be provided in tests.
- DO NOT use `TranslocoModule` alone in `providers[]` — it does not provide `TRANSLOCO_TRANSPILER`.
- CORRECT: `TranslocoTestingModule.forRoot(options)` goes in `imports[]` of `TestBed.configureTestingModule`.
- `provideAnimationsAsync('noop')` goes in `providers[]` to suppress animation overhead.
- Reference pattern: `dashboard.component.spec.ts` (dispatch already exists in codebase).
- `provideAnimationsAsync()` (without arg) causes "Invalid provider for NgModule" because it returns `EnvironmentProviders` — must use `provideAnimationsAsync('noop')` which returns a compatible factory.

### Pattern: NO PUT for seller-profile
- Backend has NO PUT endpoint for `/api/v1/seller-profile`. Only PATCH (upsert semantics).
- `account-api.service.ts` has a bug: `updateProfile()` calls `this.api.put(...)`. DO NOT replicate.
- `ProfileApiService` uses `this.api.patch(...)` for all writes.

### Build notes
- profile-component lazy chunk: 9.56 kB raw / 2.45 kB gzip (well within budget)
- `ng build --configuration=production` passes ZERO errors with the new files

### Test infrastructure note (inherited from service-builder dispatch)
- `NG0914` zone.js warning in stderr is EXPECTED — zone.js loaded in test-setup.ts for runtime but tests use zoneless TestBed. Safe to ignore.
- "Could not find Angular Material core theme" warning is also EXPECTED in tests — no SCSS loaded in jsdom. Safe to ignore.
- ENOSPC errors on the test run are disk-space exhaustion at OS level, not code defects. Run individual spec files with `--no-coverage` to avoid temp-file bloat when disk is near full.

---

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

## Session 2026-06-06 — Shared UI Polish Dispatch {#shared-ui-polish-dispatch}

### Routes touched
Shared components only (no specific page route). Components usable across all 10 V1 routes.

### Pattern: StatusBadge via computed() style string
- Use a `computed()` signal that derives a full inline `style` attribute string from the status input.
- Bind via `[style]="badgeStyle()"` on the inner `<span>`.
- Advantage over `[class]`: no external SCSS needed; works with inline-style-only components.
- Status map as `Record<string, BadgeStyle>` with a DEFAULT_STYLE fallback for unknown statuses.
- Cast `status()` with `as string` when indexing a plain object map to avoid TS strict index error.

### Pattern: EmptyState — native <button> instead of MatButton
- When a component spec says "no MatButton import needed", use a native `<button>` with all styles inlined.
- Still set `min-height:44px; min-width:44px` for 44px touch target compliance (Tirupur mobile-first).
- Import MatIconModule only; no need for CommonModule or NgIf — use `@if` control flow.
- Remove `<ng-content />` from stub templates when replacing with a fully specified template.

### Pattern: LoadingSkeletonComponent — CSS @keyframes inline in styles[]
- Define `@keyframes shimmer { from ... to ... }` inside the component `styles: [...]` array.
- Apply via a CSS class `.shimmer-box` defined in the same `styles: []` block.
- Use `@switch/@case` Angular 18 control flow for variant dispatch.
- For table-row variant: `computed()` returns an array of `{index, width}` objects — `@for` iterates with `track row.index`.
- The `statBoxes = [0,1,2,3]` field is a plain array constant (not signal) — fine for static iteration inside `@for`.

### Pattern: FormFieldComponent — <ng-content /> pass-through
- `<ng-content />` passes child form controls through without wrapping logic.
- `@if` control flow replaces `*ngIf` — no CommonModule import needed.
- `role="alert"` on error div ensures screen reader announcement.
- The `required` input is `input<boolean>(false)` — a falsy default, no required validator logic in this component.

### Pattern: StatCardComponent — Material icon font via inline font-family
- Without importing MatIconModule, render Material icon names as text inside a `<span>` with `font-family:'Material Icons','Material Symbols Outlined',sans-serif`.
- This works only when the Material icon font CSS is loaded globally (it is via styles.scss / angular.json).
- If icon font is not available, the icon name renders as text fallback — acceptable for V1 stat cards.

### Pattern: PageHeaderComponent — MatIconModule for optional icon
- Import MatIconModule explicitly when using `<mat-icon>` in a template.
- Use `@if (ctaIcon())` inside the button to conditionally render the icon.
- `mat-icon` inline style: `font-size:18px; width:18px; height:18px; line-height:18px` to constrain size inside a button.

### Build notes (2026-06-06)
- ng build --configuration development: ZERO errors, 4.023s
- All 7 modified/created files compile cleanly under TypeScript strict mode

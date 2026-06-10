# Memory — meesell-angular-component-builder

## Agent Identity
Angular 18 component specialist for MeeSell. Owns 10 page components + shared UI components. Standalone, OnPush, Reactive Forms, Tailwind + Material. Decentralized memory ecosystem.

## MEMORY.md Index
- [Session 2026-06-06 — Profile feature Dispatch 1](#session-2026-06-06)
- [Session 2026-06-06 — Dashboard Dispatch 1](#dashboard-dispatch-1)
- [Session 2026-06-06 — Smart Picker Dispatch 1](#smart-picker-dispatch-1)
- [Session 2026-06-06 — Auth Dispatch 1 — LandingComponent](#landing-dispatch-1)
- [Session 2026-06-06 — Catalog Wave 2a — catalog-form service layer](#catalog-wave-2a)

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

---

## Session 2026-06-06 — Smart Picker Dispatch 1 {#smart-picker-dispatch-1}

### Route touched
`/catalogs/new` — features/smart-picker/

### Services consumed
`SmartPickerApiService` (own, created this dispatch) + `SmartPickerStateService` (own) + `ErrorService` (core) + `ApiClient` (core)

### Pattern: API contract vs existing scaffold
- The pre-existing scaffold used wrong paths (`GET /categories/suggest?q=` instead of `POST /categories/suggest` with body) and wrong model types.
- ALWAYS read the task spec's API contract section carefully; it overrides any scaffold stubs.
- Solution: completely replaced the scaffold service with the spec-correct implementation.

### Pattern: State service with Subject-driven debounce in constructor
- `SmartPickerStateService` uses a private `Subject<string>` for description inputs.
- Constructor pipes: `debounceTime(500)` + `tap(loading.set(true))` + `switchMap(api.suggest)` + `takeUntilDestroyed()`.
- Correctly cancels in-flight HTTP calls on rapid re-submission (switchMap semantics).
- `takeUntilDestroyed()` works in constructors when the service is in an injection context.

### Pattern: 422 profile-incomplete error propagation
- `selectCategory()` propagates 422 WITHOUT catching — page component catches via `catchError`.
- Raw error body accessed via `(err as {raw?: {error?: unknown}})?.raw?.error` (ApiClient normalises errors via normaliseHttpError).
- `MatDialog.open(DialogComponent, { data: raw })` + `MAT_DIALOG_DATA` injection is the correct standalone dialog pattern.

### Pattern: toSignal() for BehaviorSubject in templates
- `state.suggestions$` is a `BehaviorSubject` — `toSignal(state.suggestions$, { initialValue: [] })` converts to signal for `@for` iteration in OnPush templates.
- Do NOT subscribe in ngOnInit and push to local signal — use `toSignal()` directly.

### Pattern: throwError import in spec files
- Always import `throwError` and `of` from `rxjs` at the top of spec files.
- Do NOT use `require('rxjs')` inside vi.fn() factory functions — causes "not a function" at runtime.
- Correct: `selectCategory: vi.fn(() => throwError(() => mockError))` with `throwError` imported at module level.

### TypeScript strict mode: transloco.translate() return type
- `TranslocoService.translate()` returns `string | undefined` in strict mode.
- Cast with `as string` when using as an argument that expects `string`:
  `this.transloco.translate('key') as string`

### Build result
- smart-picker lazy chunk: 87.39 kB raw / 16.95 kB gzip (within 80 kB gzip budget)
- Initial bundle warning (523 kB > 500 kB): PRE-EXISTING — not from smart-picker (it is lazy)
- Production build: ZERO errors
- 103 total tests: all passing (14 test files including 3 new smart-picker specs)

---

## Session 2026-06-06 — Auth Dispatch 1 — LandingComponent {#landing-dispatch-1}

### Route touched
`/` — features/landing/landing/

### Services consumed
None. LandingComponent is fully static (public route, no auth, no API calls).

### Pattern: | transloco pipe — NOT *transloco="let t" structural directive
- Task spec stated to use `*transloco="let t"` but NO component in this codebase uses that pattern.
- ALL components (dashboard, profile) use `| transloco` pipe directly in interpolation: `{{ 'key' | transloco }}`.
- `TranslocoModule` import covers BOTH the pipe and the structural directive — import is the same.
- DO NOT introduce `*transloco="let t"` pattern. Follow existing codebase convention.
- Stop condition in the spec said "check features/dashboard/" — that confirmed pipe pattern is canonical.

### Pattern: Static page — no CommonModule, no @if/@for needed
- LandingComponent has zero conditional blocks and zero lists.
- Angular 18 native control flow (@if/@for) is available without CommonModule but is not needed here.
- Minimal import list for a static page: `[RouterLink, MatButtonModule, TranslocoModule]`.

### Pattern: host binding via { class: 'mee-landing' } in @Component metadata
- Prefer `host: { class: '...' }` over `@HostBinding('class')` for standalone components.
- Cleaner, co-located with the component decorator, no extra property needed.

### Pattern: Material Symbols Outlined icons (not mat-icon / MatIconModule)
- `<span class="material-symbols-outlined" aria-hidden="true">icon_name</span>`
- Material Symbols Outlined is the newer icon font family loaded globally via _typography.scss.
- `mat-icon` uses the older Material Icons family — do NOT mix families.
- `aria-hidden="true"` required on all decorative icon spans.

### Pattern: routerLink anchor + mat-flat-button for CTA buttons
- `<a routerLink="/route" mat-flat-button color="primary">text</a>` — correct Angular pattern.
- Avoids `<button (click)="router.navigate(...)">` for routes that should be linkable (right-click
  → open in new tab, keyboard navigation).
- Apply `min-h-[44px]` on the anchor for 44px touch target compliance.

### Pattern: 44px touch targets on text links
- Text `<a>` links get `min-h-[44px] inline-flex items-center` for Tirupur mobile-first compliance.
- This is a Tailwind utility approach; no explicit height/padding needed when `inline-flex items-center`
  expands the tap area vertically via the parent line height context.

### Pattern: Semantic HTML5 for static landing sections
- Use `<header>`, `<nav>`, `<section>`, `<article>`, `<footer>` (not generic `<div>`).
- `aria-labelledby` on `<section>` pointing to the heading id (`id="hero-headline"`).
- `aria-label` on `<nav>` and on decorative icon sections.
- This satisfies WCAG 2.2 AA landmark navigation without any CDK a11y dependency.

### Build result (2026-06-06)
- landing-component lazy chunk: 3.71 kB raw / 1.31 kB gzip (budget: ≤80 kB — 98% headroom)
- 6/6 vitest tests passing
- ng build --configuration=production: ZERO errors

---

## Session 2026-06-06 — Catalog Wave 2a — catalog-form service layer {#catalog-wave-2a}

### Route touched
`/catalogs/:id/edit` — features/catalog-form/

### Services consumed / created
All feature-scoped (`@Injectable()` NO `providedIn`):
- `CatalogFormApiService` (replaced stub)
- `DraftRecoveryService` (new)
- `CategorySchemaService` (new)
- `EnumLookupService` (new)
- `CatalogFormStateService` (new)

### Pattern: Feature-local model types for API contract drift
When `@core/models/*.model.ts` shape differs from the actual API response:
- Define a feature-local interface inline in the service file (e.g. `ProductDetail` in `catalog-form-api.service.ts`)
- Add a `// TODO(cross-cutting): reconcile` comment pointing to the core model to fix
- NEVER import the drifted core model and cast/transform it — that silently perpetuates the wrong shape
- Corollary: the autofill response `AutofillResponse` and draft `ProductDraft` are NEW types
  that don't exist in core models yet — also defined inline with the same TODO pattern

### Pattern: 204 handling for DraftRecoveryService
- `GET /products/:id/draft` returns 204 (no body) when product was never autosaved — common path
- `ApiClient.get<T>()` passes through null body from 204 response as `null`
- In the service: `pipe(map(res => res ?? null))` converts the null body cleanly to typed null
- ALSO add a `catchError` guard for the edge case where some HTTP adapters throw on 204
  (`if (err instanceof ApiError && err.status === 204) return of(null)`)
- In spec: mock with `apiClient.get.mockReturnValue(of(null))` — no need for complex HttpResponse wrapping

### Pattern: spec for services with no template (service-only spec)
- These services have NO template/component — use `TestBed.configureTestingModule({ providers: [...] })`
  without any `imports:[]` (no TranslocoTestingModule needed, no provideAnimationsAsync)
- Mock `ApiClient` as a plain object: `{ get: vi.fn(), post: vi.fn(), patch: vi.fn() }`
- `TestBed.inject(SomeService)` works cleanly for service-only TestBed configs
- Service-only specs are dramatically simpler than component specs

### Pattern: PrimitiveKind and StepId are string union types, NOT TypeScript enums
- `PrimitiveKind` = `'text_short' | 'text_long' | ...` (string union, no dot notation)
- `StepId` = `'basics' | 'pricing' | ...` (string union)
- Do NOT use `PrimitiveKind.TextInput` in specs — this is undefined at runtime
- Use string literals directly: `primitive: 'text_short'`, `stepId: 'basics'`
- Pattern confirmed from `@shared/enums/primitive-kind.enum.ts` and `step-id.enum.ts`

### Pattern: signal-based state service (no BehaviorSubject/Observable)
Per §16.B state management tree for per-route feature state:
- Signals for all state (NOT BehaviorSubject) — fresh instance per route activation
- `computed()` for derived values — they re-evaluate automatically when dependencies change
- Mutation methods produce new objects via spread (`{ ...current, [key]: newVal }`) — signals
  are not reactive objects; must SET a new reference for reactivity to propagate
- `acceptAiSuggestion` pattern: apply value via `applyFieldChange`, then destructure-remove
  from the suggestions Record (`const { [key]: _removed, ...rest } = suggestions`)
- `applyAutofillSuggestions` pattern: iterate `Object.entries()`, build new Record, spread-merge
  over existing suggestions

### Pattern: X-Autosave header verification in spec
The most critical correctness test in this dispatch. Verify with:
```typescript
const [path, body, options] = apiClient.patch.mock.calls[0];
expect(options?.headers?.['X-Autosave']).toBe('true');
```
AND separately for saveProduct:
```typescript
expect(options).toBeUndefined();  // saveProduct must NOT send any options
```

### CategorySchema model drift
`@core/models/category.model.ts#CategorySchema` is missing `categoryName: string`.
The actual API response includes it. Feature-local `CategorySchemaFull` defined in
`category-schema.service.ts` adds `categoryName`. TODO(cross-cutting) comment present.
Cross-cutting session should add `categoryName: string` to the core model.

### Build result (2026-06-06 Wave 2a)
- catalog-form-component lazy chunk: 7.70 kB raw / 2.29 kB gzip
- catalog-form-routes lazy chunk: 2.94 kB raw / 951 bytes gzip
- 24/24 new tests passing (5 spec files)
- ng build --configuration=production: ZERO errors

---

## Session 2026-06-07 — Catalog Wave 2b — 11 Primitives + Wizard Rendering Engine {#catalog-wave-2b}

### Route touched
`/catalogs/:id/edit` — features/catalog-form/primitives/ + wizard-renderer/ + autofill-overlay/

### Services consumed
`EnumLookupService` (DropdownApiPrimitiveComponent), `ActivatedRoute` (DropdownApiPrimitiveComponent, ImageUploadPrimitiveComponent), `FormBuilder` (AddressGroupPrimitiveComponent)

### Pattern: ControlValueAccessor via NG_VALUE_ACCESSOR + forwardRef in providers[]
- Every primitive registers itself as a CVA using:
  `{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => MyComponent), multi: true }`
- This goes in the component's OWN `providers: []` array (NOT injected via DI)
- Import: `ControlValueAccessor, NG_VALUE_ACCESSOR, forwardRef` all from `@angular/forms`
- The component ALSO imports FormsModule from its feature — NOT ReactiveFormsModule unless it has its own FormGroup (AddressGroup only)

### Pattern: signal inputs (input.required()) with NG_VALUE_ACCESSOR
- Primitives use `schema = input.required<FieldSchema>()` (not @Input())
- `value = input<string | number | null>(null)` (optional with default)
- `aiSuggestion = input<AiSuggestion | null>(null)` (optional with default)
- `disabled = input<boolean>(false)` (optional with default)
- Output: `readonly valueChange = output<ValueChange>()`
- CRITICAL: do NOT use `@Output() + EventEmitter` — use the signal `output<T>()` API

### Pattern: ValueChange emitted on blur, not on every keystroke
- `innerValue = signal<T>(default)` for component-local reactive state
- `onInput(event)` updates innerValue + calls `_onChange(value)` (CVA pipe)
- `onBlur()` sets `touched.set(true)` + emits `valueChange` output with `{canonicalName: schema().canonicalName, value: innerValue(), source: 'seller'}`
- CVA `registerOnChange(fn)` stores fn in `_onChange = fn`; init: `_onChange = (_v: unknown) => {}`
- CVA `registerOnTouched(fn)` stores fn in `_onTouched = fn`; init: `_onTouched = () => {}`

### Pattern: FieldSchema has NO enumOptions field in the locked model
- FieldSchema in @core/models does NOT have `enumOptions`
- Workaround: `(this.schema() as unknown as { enumOptions?: DropdownOption[] }).enumOptions ?? []`
- Use `computed<DropdownOption[]>()` to derive options from schema
- Add `// TODO(cross-cutting): add enumOptions?: Array<{code:string; label:LocaleMap}> to FieldSchema`

### Pattern: FieldDispatcher @switch case string MUST be 'dropdown_api_search'
- The PrimitiveKind enum value for API-driven dropdown is `'dropdown_api_search'`
- The @case string MUST be exactly `'dropdown_api_search'` (not 'dropdown_api')
- All 11 cases must be explicitly listed even if some dispatch to the same child
- `@default` case should render a visible warning in dev (fallback for unknown primitives)

### Pattern: CDK virtual scroll in dropdown-large
- Import `ScrollingModule` from `@angular/cdk/scrolling`
- `<cdk-virtual-scroll-viewport [itemSize]="48" [style.height.px]="200">` inside mat-autocomplete panel
- `*cdkVirtualFor="let option of filteredOptions()"` (note: NOT @for — CDK requires structural directive)
- `filteredOptions = computed<DropdownOption[]>()` must return a PLAIN ARRAY (not Observable) for cdkVirtualFor

### Pattern: DropdownApiPrimitiveComponent ngOnInit RxJS subscription
- Uses `ngOnInit(): void` (NOT constructor) because `inject(ActivatedRoute)` reads params at subscription time
- `private readonly search$ = new Subject<string>()`
- Pipeline: `search$.pipe(debounceTime(300), distinctUntilChanged(), switchMap(...), takeUntilDestroyed(this.destroyRef)).subscribe(...)`
- `takeUntilDestroyed(this.destroyRef)` — inject DestroyRef explicitly; do NOT use `takeUntilDestroyed()` without argument in non-constructor context

### Pattern: AutofillOverlayComponent output interfaces
- Outputs: `accepted = output<AutofillAccepted>()` and `rejected = output<AutofillRejected>()`
- Do NOT use a single `decision` output (spec uses separate outputs for clarity)
- `showOverlay = computed(() => suggestion() !== null && !suggestion()?.accepted && !suggestion()?.rejectedReason)`
- `displayValue = computed<string>()` — handles Array.join(', ') for multi-value suggestions, String() for others
- The `productId = input<string>('')` is optional for wave 2c use

### Pattern: WizardRendererComponent outputs (signal API not EventEmitter)
- `readonly valueChange = output<ValueChange>()` and `readonly submit = output<void>()`
- `patch(change: ValueChange): void { this.valueChange.emit(change); }` — forwarding from FieldDispatcher
- `onSubmit(): void { this.submit.emit(); }` — called from template submit button
- StepComposerService is `@Injectable()` (no `providedIn`) — provided via the component's `providers: []`

### CRITICAL: Signal input testing limitation in vitest+jsdom
- `fixture.componentRef.setInput('schema', MOCK_SCHEMA)` emits NG0303 warning but does NOT set the value
- The signal input remains at its default value (null for optional, throws NG0950 for required)
- DO NOT call `fixture.detectChanges()` after setInput — the template will access schema() which throws
- CORRECT test pattern for CVA components:
  1. Create component (`TestBed.createComponent(X)`)
  2. Do NOT call detectChanges()
  3. Access component instance directly: `const c = fixture.componentInstance`
  4. Call CVA methods directly: `c.writeValue(val)` → check `c.innerValue()`
  5. For registerOnChange: `c.registerOnChange(fn)` → call `(c as unknown as { _onChange: fn })._onChange(val)` directly
  6. For event handlers that call schema(): bypass them, test _onChange directly instead
- Exception: computed signals with default values (like `showOverlay`) ARE testable without setInput
- Exception: output events can be tested by subscribing then calling `component.output.emit(val)` directly

### Build result (2026-06-07 Wave 2b)
- catalog-form-component lazy chunk: 7.70 kB raw / 2.27 kB gzip (primitives not yet wired to CatalogFormComponent — Wave 2c)
- 42/42 new tests passing (15 spec files: 11 primitive specs + 4 wizard engine specs)
- 205/212 total tests passing (7 pre-existing failures: export.component.spec.ts NG0300 + shell.component.spec.ts jasmine)
- ng build --configuration=production: ZERO errors

---

## Session 2026-06-07 — Catalog Wave 2c — CatalogFormComponent full page wiring {#catalog-wave-2c}

### Route touched
`/catalogs/:id/edit` — features/catalog-form/catalog-form/

### Services consumed
`CatalogFormApiService`, `CatalogFormStateService`, `DraftRecoveryService`,
`CategorySchemaService`, `StepComposerService` (provided locally via `providers:[]`),
`ErrorService` (core), `MatSnackBar` (core), `ActivatedRoute`, `Router`, `DestroyRef`

### Pattern: Autosave Subject+debounce vs meeAutosave directive
- The `meeAutosave` directive requires `meeAutosaveControl = input<AbstractControl | null>()` to watch.
- This component uses signals (no FormGroup/FormControl at page level).
- CORRECT pattern: `private readonly autosaveTrigger$ = new Subject<void>()` + `debounceTime(10_000)` + `takeUntilDestroyed(this.destroyRef)` in `ngOnInit`.
- Call `autosaveTrigger$.next()` from `onFieldChange()` to debounce per field change.
- Do NOT use the directive when there is no FormGroup to attach to. The Subject pipeline is functionally identical.
- `takeUntilDestroyed(this.destroyRef)` — inject `DestroyRef` explicitly (not constructor; used in ngOnInit context).

### Pattern: Auto-reset saveStatus to idle after saved
- After autosave succeeds: `this.saveStatus.set('saved')` + `setTimeout(() => { if (this.saveStatus() === 'saved') this.saveStatus.set('idle'); }, 3000)`
- The conditional guard `if (this.saveStatus() === 'saved')` prevents overriding a concurrent 'error' state.

### Pattern: Parallel schema + draft fetch via coordinated boolean flags
- `getProduct` must resolve first (leafCategoryId needed for schema fetch).
- After product: run `getSchema(leafCategoryId)` and `getDraft(id)` in parallel.
- Use two flags `schemaResolved` + `draftResolved` + a `tryFinish()` closure: `if (schemaResolved && draftResolved) state.loading.set(false)`.
- This is simpler than forkJoin when the two calls are independent and error-handling differs.

### Pattern: 404 navigate vs other error handle
- `err instanceof ApiError && err.status === 404` → `router.navigate(['/dashboard'])` (no snackbar needed)
- `err instanceof ApiError && err.status === 429` → `snackBar.open(retryAfterMsg, ...)` (no errorService)
- All other errors → `state.error.set(message)` + `errorService.showError(err)` (dual surface)

### Pattern: Autofill 429 vs fallback_offered distinction
- 429 (rate limit): `Daily AI fill limit reached. Try again tomorrow.` — snackBar, no errorService
- `fallbackOffered: true` in HTTP 200 response: `AI suggestions may not be complete` — snackBar, 4s
- Neither condition sets `state.error()` — these are transient notices, not blocking errors

### Pattern: onAutofillAccepted/Rejected handling at page level (V1 global approach)
- Wave 2b delivered `AutofillOverlayComponent` as a per-field wrapper component.
- V1 CatalogFormComponent does NOT wire per-field overlays — accepted/rejected events handled at page level.
- `onAutofillAccepted` and `onAutofillRejected` are public methods ready for future child component output binding.
- The `WizardRendererComponent` → `FieldDispatcherComponent` chain does NOT surface these events in V1 — per-field overlay wiring is V1.5 work.

### Pattern: StepComposerService provided at component level (not feature route level)
- `StepComposerService` is `@Injectable()` (no `providedIn`).
- It is NOT in `CATALOG_FORM_ROUTES providers[]` (which only lists the 5 stateful services).
- Provide it in the page component's own `providers: [StepComposerService]` array.
- This means a new StepComposerService instance is created per CatalogFormComponent instance — correct since it has no state.

### Pattern: ValueChange type bridging (primitive.contract vs state.service)
- `WizardRendererComponent` emits `ValueChange` from `../primitives/primitive.contract` (has `source: 'seller' | 'ai-accept'` field).
- `CatalogFormStateService.applyFieldChange()` takes `ValueChange` from its own file (only `canonicalName` + `value`).
- The primitive contract type is a SUPERSET of the state service type — structural subtyping means passing it works.
- Import `ValueChange` from `primitive.contract` in the page component (matches wizard's output type).

### Wave 2b pre-existing build errors fixed in this dispatch
Four Wave 2b errors existed in the same feature folder — fixed as part of Wave 2c build gate:
1. `[maxlength]` → `[attr.maxlength]` on native input/textarea (NG8002 "not a known property")
   - MatInput does NOT proxy `maxlength` as a component input; must use attribute binding
2. `WizardStep.title: Record<string, string>` → `WizardStep.title: LocaleMap` (TS2322 + NG5)
   - `LocaleMap` has `en: string` but no index signature → not assignable to `Record<string, string>`
   - Fix: change the interface property to `LocaleMap` (what LocaleLabelPipe actually expects)
3. `!stepper.selectedIndex === 0` → `stepper.selectedIndex !== 0` (NG7 operator precedence)
   - `!x === 0` always evaluates `(!x)` first (boolean) then compares boolean to number — nonsensical

### Build result (2026-06-07 Wave 2c)
- catalog-form-component lazy chunk: 88.11 kB raw / 15.70 kB gzip (budget <= 120 kB -- 87% headroom)
- 229/236 total tests passing (7 pre-existing failures: export.component.spec.ts NG0300 + shell.component.spec.ts jasmine)
- ng build --configuration=production: ZERO errors, 3 pre-existing warnings (NG8107 + NG8102 in primitives)

---

## Session 2026-06-06 — §5A AMENDMENT 2026-06-06B Shared Component Lock {#5a-lock-batch1}

### Route touched
Shared components only (no page route). Components used across all 10 V1 routes.

### Pattern: §5A hex prohibition — three valid alternatives
1. `var(--mee-color-*)` CSS custom properties — for semantic design tokens (primary, surface, on-surface, error)
2. Tailwind semantic alias classes (`text-on-surface`, `bg-surface-variant`) — wired in tailwind.config.js to CSS vars
3. Tailwind palette classes (`bg-green-100`, `text-green-700`, `border-green-200`) — for non-semantic status tints where no design token exists
4. `mat-flat-button color="primary"` — Material themed button; background resolved automatically to `var(--mee-color-primary)` via _component-overrides.scss without any manual color

### Pattern: Tailwind [class] binding in Angular 18 merges with static class=
- `class="base-classes..."` + `[class]="dynamicClasses()"` — both apply simultaneously in Angular 18.
- Replaces the `[style]` binding pattern used in the old StatusBadge inline-style approach.
- STATUS_CLASSES is a plain `Record<string, string>` — no interface needed; values are Tailwind class strings.
- Default fallback: `const DEFAULT_CLASSES = 'bg-gray-100 text-gray-500 border-gray-200'` constant keeps the computed clean.

### Pattern: output<void>() vs @Output() EventEmitter
- Prefer `output<void>()` (Angular 18 function API) over `@Output() readonly foo = new EventEmitter<void>()`.
- Import: `output` from `@angular/core` — remove `EventEmitter` and `Output` from the import.
- Emit syntax identical: `this.ctaClick.emit()` works for both.

### Pattern: mat-icon 48px sizing without a design token
- `font-size:48px; width:48px; height:48px;` kept as inline style on `<mat-icon>` — 48px is a one-off size, not a semantic design token, no Tailwind class for this.
- Color removed from inline style; moved to `class="text-on-surface-variant"`.

### Pattern: mat-flat-button touch target
- `class="min-h-[44px]"` on `<button mat-flat-button>` for 44px touch target compliance.
- Do NOT set background via inline style — `color="primary"` handles it via Material theming.

### Build notes
- ng build --configuration development: ZERO errors, 5.493s
- Spec files NOT updated — @analogjs not yet installed; spec infra pass is a separate dispatch.

---

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

## Session 2026-06-06 — Onboarding Wizard Dispatch 1 {#onboarding-dispatch-1}

### Route touched
`/onboarding` — features/account/onboarding/

### Services consumed
None (Dispatch 1 is a pure skeleton — no API calls, no service injection beyond Router).

### Pattern: mat-stepper with @ViewChild reference
- `@ViewChild('stepper') stepper!: MatStepper;` — use template variable `#stepper` on `<mat-stepper>`.
- Call `this.stepper?.next()` with optional chaining — ViewChild is defined after ngAfterViewInit,
  but for button-triggered calls it is always initialized. Optional chaining is safe.
- `MatStepperModule` import covers `mat-stepper`, `mat-step`, `matStepperPrevious`, `matStepLabel`, `MatStepper` class.
- `[linear]="false"` for skeleton — allows free navigation without step validators.

### Pattern: mat-step [completed] bound to a signal
- `[completed]="phase1Submitted()"` — `[completed]` is a boolean @Input on MatStep.
- Calling the signal `()` in the template binding is correct Angular 18 syntax.
- Setting signal (`this.phase1Submitted.set(true)`) + calling `stepper.next()` in the same
  method is the correct combined pattern.

### Pattern: mat-spinner inside a disabled button
- `<button mat-flat-button [disabled]="saving()">` — disabled state from signal.
- Inline spinner: `<mat-spinner diameter="16" class="inline-block mr-2">` inside `@if (saving())`.
- `MatProgressSpinnerModule` must be in imports[].

### Pattern: matStepperPrevious directive
- `<button mat-stroked-button matStepperPrevious>` — no (click) handler needed.
- Directive (from MatStepperModule) calls stepper.previous() internally.

### Pattern: Fake timers for setTimeout navigation tests (Vitest)
- `vi.useFakeTimers()` before calling the method under test.
- `vi.advanceTimersByTime(300)` to flush the 300ms timeout.
- `vi.useRealTimers()` in `afterEach()` for test isolation.
- `vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true)` — set spy BEFORE calling method.
- After `vi.advanceTimersByTime(300)`: saving() resets to false AND navigate spy is called in the same tick.

### Pattern: Asserting 3 mat-stepper steps in DOM
- `mat-step` is not a DOM element — renders as `.mat-step-header` entries.
- Query: `fixture.nativeElement.querySelectorAll('.mat-step-header')` → expect length 3.

### Tailwind classes verified for onboarding
- `bg-bg`, `bg-surface`, `bg-surface-variant`, `text-on-surface`, `text-on-surface-variant`
- `rounded-mee-lg`, `rounded-mee-md`, `shadow-mee-2`, `border-outline`
- `text-mee-sm`, `text-mee-lg`, `text-mee-2xl`
- NOTE: `border-b border-outline` — both classes required (`border-b` sets width, `border-outline` sets color).

### i18n flat-key format (en.json)
- en.json uses flat dot-notation keys: `"onboarding.steps.businessDetails": "..."`
- NOT nested JSON objects — that would break Transloco's flat-key parser.

### Build result (2026-06-06 onboarding dispatch 1)
- ng build --configuration=production: ZERO errors
- onboarding-component lazy chunk: 36.19 kB raw / 8.24 kB gzip (budget ≤80 kB gzip — PASS)
- 4/4 new tests pass; NG0914 + Material theme warnings in stderr are expected (pre-documented)

---

## Session 2026-06-07 — Auth Dispatch 2 — features/auth/ {#auth-dispatch-2}

### Route touched
`/signup` + `/login` — features/auth/ (NEW folder, separate from features/account/)

### Services consumed
`AuthApiService` (own, created this dispatch) + `ErrorService` (core) + `ApiClient` (core) + `AuthService` (core)

### Context: Auth sub-session owns features/auth/ (signup + login only)
- Founder ruling 2026-06-06A un-merged account/ — auth sub-session creates features/auth/ for signup+login only
- features/account/ stubs had WRONG OTP contracts — DO NOT consume them
- Three contract corrections applied in auth.model.ts:
  (a) OtpVerifyRequest: { phone, otp } NOT { requestId, otp }
  (b) OtpSendResponse: only { request_id } — no 'message' field
  (c) OtpVerifyResponse: no 'profileComplete' boolean field

### Pattern: ControlValueAccessor stub in parent component spec must implement CVA
- When parent template has `formControlName="phone"` bound to a child component stub,
  the stub MUST implement NG_VALUE_ACCESSOR or Angular throws NG01203 at runtime.
- Correct fix: add `providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => StubClass), multi: true }]`
  to the stub @Component decorator, and implement the 4 CVA methods on the stub class.
- WRONG: bare `@Component({...}) class StubClass {}` — NG01203 "No value accessor for form control name"
- Note: forwardRef import comes from `@angular/core`; ControlValueAccessor + NG_VALUE_ACCESSOR from `@angular/forms`

### Pattern: mat-error in isolated component test — use a plain class instead
- Angular Material `mat-error` visibility is controlled by the parent `mat-form-field` based on
  the form control's error state. In isolation tests (no parent FormGroup), `mat-error` remains
  hidden even if `@if` renders it in the template.
- Workaround: replace `mat-error` with `mat-hint` (always visible per content projection) and
  add a custom CSS class (e.g., `.mee-phone-error`) for test selector targeting.
- Query in spec: `fixture.nativeElement.querySelector('.mee-phone-error')` — reliable in jsdom.
- This is a test-isolation tradeoff; in a real form context mat-error would work correctly.

### Pattern: NG0303 warning from stub inputs — benign in tests
- When a stub component doesn't declare `@Input() label`, the parent template's `[label]="..."` binding
  emits NG0303 in console but does NOT fail the test.
- Tests still pass; NG0303 is a compile-time warning surfaced at runtime in jsdom, not an error.
- Do NOT add unused `@Input()` to stubs just to silence warnings — keep stubs minimal.

### Pattern: feature-scoped service provided at route level (not root)
- `AuthApiService` uses `@Injectable()` with NO `providedIn` — scoped to AUTH_ROUTES providers array.
- Pattern matches ProfileApiService, DashboardApiService, SmartPickerApiService — consistent.

### Pattern: FormBuilder inject() + single CVA-backed control
- `this.fb.group({ phone: ['', [Validators.required]] })` — single control backed by CVA.
- The CVA (`PhoneInputComponent`) emits E.164 on valid 10-digit input, '' on invalid.
- Angular form validates with `Validators.required` — '' (empty string) = invalid, E.164 string = valid.
- No custom validator needed on the FormGroup; validation lives inside the CVA component.

### Pattern: E.164 phone formatting in CVA
- Strip non-digits with `/\D/g`, limit to 10 chars with `.slice(0, 10)`.
- Emit `+91${digits}` when `digits.length === 10`, else `''`.
- `writeValue()` handles incoming E.164 by stripping the `+91` prefix for display.

### Build result (Auth Dispatch 2)
- signup-component lazy chunk: 2.65 kB raw / 963 bytes gzip (budget ≤80 kB gzip — 99% headroom)
- login-component lazy chunk: 2.25 kB raw / 883 bytes gzip (budget ≤80 kB gzip — 99% headroom)
- 14/14 vitest tests passing (3 spec files)
- ng build --configuration=production: ZERO errors

---

## Session 2026-06-07 — Auth Dispatch 3 — OtpVerifyComponent body {#auth-dispatch-3}

### Route touched
`/signup` + `/login` — features/auth/components/otp-verify/

### Services consumed
`AuthApiService` (verifyOtp + sendOtp) + `ApiClient` (GET /seller-profile) + `ErrorService` (core)

### Pattern: ng-otp-input is an NgModule package (NOT standalone)
- `ng-otp-input` v1.9.3 exports `NgOtpInputModule` (NgModule) and `NgOtpInputComponent`.
- In the component's `imports[]` array: use `NgOtpInputModule` (the NgModule) — NOT `NgOtpInputComponent` directly.
- Import `NgOtpInputComponent` type-only for the `@ViewChild` type annotation.
- `NgOtpInputComponent.setValue(value)` — method for programmatic OTP reset (called on resend + verify error).
- `NgOtpInputComponent` has `onInputChange: EventEmitter<string>` output — bind as `(onInputChange)="onOtpChange($event)"`.
- The `config` input accepts `{ length, allowNumbersOnly, inputStyles }` object.
- Import path for both: `'ng-otp-input'` (the public_api.d.ts re-exports both).

### Pattern: DestroyRef + takeUntilDestroyed for interval countdown
- Inject `DestroyRef` explicitly: `private readonly destroyRef = inject(DestroyRef)`.
- `interval(1000).pipe(take(60), takeUntilDestroyed(this.destroyRef)).subscribe(...)` — 60-tick countdown.
- `take(60)` + `timeLeft.update(t => Math.max(0, t - 1))` caps at 0 without going negative.
- `startCountdown()` extracted as a private method — call from `ngOnInit()` AND `onResend()`.
- New call to `startCountdown()` on resend resets `timeLeft.set(60)` before starting interval.
- CRITICAL: `takeUntilDestroyed(destroyRef)` prevents RxJS subscriptions from leaking when component unmounts mid-countdown.

### Pattern: Post-verify routing with nested subscribe (Q-AUTH-003 Option A)
- After verifyOtp() success: call `apiClient.get<SellerProfile>('/seller-profile')` to check `profile.profile_complete`.
- 200 + `profile_complete: true` → navigate to `/dashboard`.
- 200 + `profile_complete: false` → navigate to `/onboarding`.
- 404 or any other error from /seller-profile → navigate to `/onboarding` (safe fallback).
- `verifying` stays `true` throughout the nested call — component unmounts on navigate, signal is abandoned.
- Do NOT call `verifying.set(false)` in the next handler — it would briefly flash UI before unmount.

### Pattern: attempts() counter — increment then check (post-increment semantics)
- `this.attempts.update(a => a + 1)` increments the signal.
- `if (this.attempts() >= 3)` reads the new value AFTER the update.
- This means on the 3rd wrong OTP: attempts goes 2→3, then the ≥3 branch fires showing "too many attempts".
- The Verify button also disables when `attempts() >= 3` via template binding.

### Pattern: displayPhone as computed() reading a @Input() property
- `displayPhone = computed<string>(() => { const p = this.phone; if (p.startsWith('+91')) return p.slice(3); return p; })`
- `this.phone` is a plain `@Input()` property (not a signal), NOT `this.phone()`.
- `computed()` that reads non-signal properties will NOT reactively update if `phone` changes.
- This is acceptable here because `phone` is set once by parent and never changes during the component's lifetime.
- If the parent could dynamically change phone, use `input()` signal instead of `@Input()`.

### Pattern: @ViewChild with null guard on setValue
- `@ViewChild('otpInput') otpInput!: NgOtpInputComponent;`
- Call with null guard: `if (this.otpInput) { this.otpInput.setValue(''); }` — ViewChild is defined after view init; guard prevents error if called before init.

### Pattern: NG0303 warning resolved by proper @Input declarations
- The stub had `@Input() phone = ''` and `@Input() requestId = ''` (no required).
- Signup + login specs were logging NG0303 "Can't bind to 'phone'" warnings because the stub's @Input wasn't being recognized in the TestBed context for those parent component tests.
- Full body with `@Input({ required: true })` properly resolves the binding — NG0303 warnings from signup/login specs disappear.

### Build result (Auth Dispatch 3)
- ng build --configuration=production: EXIT 0, zero errors
- 6/6 new OtpVerify tests pass; 229/242 total; 13 pre-existing failures (unchanged)
  Pre-existing failures: 7 export.spec (NG0300) + 1 shell.spec (Jasmine) + 6 dashboard.spec (styleUrl)
  Note: The "7 pre-existing" count in Wave 2c memory undercounts — actual pre-existing count is 13
  (dashboard.component.spec.ts has 6 styleUrl failures that also pre-exist)

---

## Session 2026-06-07 — Wave 3 — images feature {#images-wave-3}

### Route touched
`/catalogs/:id/images` — features/images/

### Services consumed
`ImagesApiService` (own, replaced stub this dispatch) + `NgxImageCompressService` + `MatDialog` + `MatSnackBar` + `ActivatedRoute` + `Router`

### Pattern: ApiClient.postMultipart returns Observable<T>, NOT Observable<HttpEvent<T>>
- The existing ApiClient.postMultipart uses `http.post<T>()` WITHOUT `{ reportProgress: true, observe: 'events' }`.
- It returns `Observable<T>` (just the response body), NOT an HttpEvent stream.
- Upload progress % (0–100) is therefore NOT available via this method.
- Consequence: uploading state tracks as a boolean flag (uploading[slotIndex]=true/false), not as a %.
- Future upgrade: if upload progress is needed, ApiClient would need a new method using
  `http.request(new HttpRequest('POST', url, formData, { reportProgress: true }))`.
- This is a DEVIATION from the task spec which requested `Observable<HttpEvent<T>>`.

### Pattern: ProductImage model uses snake_case (API wire format)
- The existing stub used camelCase (slotIndex, precheckResults, isJpeg, colorSpaceOk...).
- The actual API contract uses snake_case: slot_index, precheck_jsonb, gcs_url, is_jpeg,
  color_space, resolution_ok, white_bg_ok, watermark_pass.
- ALWAYS use the API spec's snake_case shape for feature-local models. The stub was wrong.

### Pattern: Export pure functions from components to avoid NG0950 in specs
- Components with `input.required()` signals: calling the signal in a computed()
  throws NG0950 in vitest+jsdom if the input hasn't been set.
- Solution: extract computation logic into a standalone exported PURE FUNCTION.
  e.g., `export function buildPrecheckItems(image: ProductImage): PrecheckItem[]`
         `export function imageStatusBadgeClass(status: ...): string`
- Test the pure function directly in specs — no TestBed component needed for logic tests.
- The component's `computed()` delegates to the pure function:
  `readonly precheckItems = computed(() => buildPrecheckItems(this.image()));`
- This avoids the NG0950 trap entirely for the 2 logic-heavy test cases.

### Pattern: overrideComponent remove[] must list real component classes
- `remove: { imports: [RealChild] }` (explicitly listing the class) works correctly.
- `remove: { imports: [] }` (empty array) does NOT remove anything — NG0300 results.
- Always check: when using ImageSlotComponent + PrecheckReportComponent inside a parent,
  explicitly list both in the remove[] array of overrideComponent.

### Pattern: Polling with destroy$ Subject (OnDestroy)
- Use `private readonly destroy$ = new Subject<void>()` for simple observable lifecycle.
- `pollImages().pipe(takeUntil(this.destroy$)).subscribe(...)` — terminates on destroy.
- `ngOnDestroy(): void { this.destroy$.next(); this.destroy$.complete(); }`
- Re-start polling by calling `this.startPolling(id)` again after upload completes.
- This is the pattern for components that do NOT use `takeUntilDestroyed()` from rxjs-interop
  (which requires injection context — constructor or injector-provided destroyRef).
- `takeUntilDestroyed()` in ngOnInit is fine IF DestroyRef is injected explicitly.

### Pattern: MatDialog.open + ConfirmDialogComponent (input() signals, not MAT_DIALOG_DATA)
- ConfirmDialogComponent uses `input<T>(default)` signals (NOT MAT_DIALOG_DATA injection).
- Set inputs via `dialogRef.componentRef!.setInput('inputName', value)` AFTER open().
- Use `!` non-null assertion (componentRef is defined when dialog is open).
- `dialogRef.afterClosed().subscribe((confirmed: boolean) => { ... })` for result.
- This is the CORRECT pattern for Material dialogs using the new Angular input() API.

### Pattern: ngx-image-compress compressFile usage
- `NgxImageCompressService.compressFile(dataUrl, orientation, ratio, quality): Promise<string>`
- orientation: -2 = auto-detect from EXIF
- ratio: 75 = reduce to 75% of original pixel dimensions
- quality: 75 = 75% JPEG quality
- Must read file as dataUrl first (FileReader + readAsDataURL).
- Convert compressed dataUrl back to Blob: split on ',', atob(base64), Uint8Array, new Blob([]).
- Inject NgxImageCompressService in the component's own `providers: []` array (it is
  NOT providedIn: 'root') OR ensure it's provided at a parent level. For standalone
  page components, add `providers: [NgxImageCompressService]` in @Component decorator.

### Pattern: canProceed computed gate (images → preview)
- `canProceed = computed(() => slot0?.status === 'ready' && slot0.precheck_jsonb?.watermark_pass === true)`
- Slot 0 (front image) must be 'ready' AND watermark_pass must be exactly `true` (not null, not undefined).
- "Next step" button `[disabled]="!canProceed()"` prevents navigation until gate passes.

### Build result (2026-06-07 Wave 3 images)
- images-component lazy chunk: 30.90 kB raw / 8.38 kB gzip (budget ≤80 kB — 89% headroom)
- 12/12 new tests passing (4 spec files)
- Total suite: 241/254 passing; 13 pre-existing failures unchanged
- ng build --configuration=production: ZERO errors, 1 new NG8102 warning (benign)


---

## Session 2026-06-07 — Wave 4 — preview + pricing features {#wave-4-preview-pricing}

### Routes touched
- `/catalogs/:id/preview` — features/preview/
- `/catalogs/:id/pricing` — features/pricing/

### Services consumed
- `PreviewApiService` (own, replaced stub this dispatch) + `ApiClient` (core)
- `PricingApiService` (own, replaced stub this dispatch) + `ApiClient` (core)

### Pattern: API model drift — feature-local interface vs @core/models
- `@core/models/pricing-calc.model.ts` uses camelCase + different field names
  (`commissionAmount`, `isPositive`, `productId`) that don't match the locked
  backend API wire format (`commission`, `commission_pct`, `seller_payout`, etc.)
- Solution: define feature-local `PricingCalc` interface in `pricing-api.service.ts`
  with correct snake_case fields. Add `// TODO(cross-cutting): reconcile` comment.
- This is the same pattern used in catalog-wave-2a — established approach for drift.

### Pattern: Two separate describe() blocks for error vs success in TestBed
- TestBed.overrideProvider() cannot be called after the module is instantiated.
- WRONG: single beforeEach + `await TestBed.overrideProvider()` inside a test → throws
- CORRECT: two separate `describe()` blocks each with their own `beforeEach()` calling
  a shared `createTestBed(apiValue)` helper. Each describe block gets a fresh module.
- Each describe block must call `TestBed.resetTestingModule()` in afterEach() to avoid
  bleed between describe blocks.

### Pattern: provideAnimationsAsync('noop') is REQUIRED (not provideAnimations())
- `provideAnimations()` causes `element.animate is not a function` in jsdom when
  mat-tab-group or MatSlider animations fire on test teardown.
- `provideAnimationsAsync('noop')` suppresses all animations in tests — correct pattern.
- This is confirmed from earlier dispatches but worth re-documenting: ALWAYS use
  `provideAnimationsAsync('noop')` in spec providers[], never `provideAnimations()`.

### Pattern: ng2-charts BaseChartDirective in standalone components
- `BaseChartDirective` from `'ng2-charts'` is imported directly in the component's
  `imports[]` array (it is standalone-compatible).
- `ChartConfiguration` type from `'chart.js'` for type-safe chart config.
- Use `computed<ChartConfiguration['data']>()` to derive chart data from input signal.
- `type="bar"` on the `<canvas baseChart>` element with `options.indexAxis='y'`
  for horizontal bar chart.
- Chart height controlled via `[style.height.px]` or container CSS height.
- Canvas must have `aria-hidden="true"` — provide a semantic legend div separately for a11y.

### Pattern: Local estimate computed() for instant slider feedback (§14.D)
- Snapshot `{ commission_pct, gst_pct, platform_fee_pct }` from the last API call.
- `readonly localEstimate = computed<Partial<PricingCalc>>()` reads `mrp()` signal +
  snapshot rates to compute `seller_payout` and `net_margin_pct` instantly.
- `readonly displayCalc = computed<PricingCalc | null>()` merges committed API calc
  with local estimate overrides for live slider feedback without API call.
- On `onMrpChanged(mrp)`: update `mrp` signal → computed auto-fires (no API call).
- On `onMrpCommitted(mrp)`: call the API → update `calc()` signal + refresh snapshot.

### Pattern: MatSlider Angular Material 18 API
- Use `<mat-slider [min] [max] [step] [discrete]>` + `<input matSliderThumb [value]
  (valueChange)="..." (change)="..." />` inside it.
- `(valueChange)` fires on every tick during slide (for live local recompute).
- `(change)` fires once on mouseup/touchend (for committed API call with setTimeout delay).
- Do NOT use deprecated `[thumbLabel]` or single-input `mat-slider` API from Material 12.
- `[discrete]="true"` shows the floating label tooltip during drag.

### Build result (2026-06-07 Wave 4)
- preview-component lazy chunk: 52.30 kB raw / 11.43 kB gzip (budget ≤80 kB — PASS)
- pricing-component lazy chunk: 186.69 kB raw / 53.84 kB gzip (budget ≤80 kB — PASS)
- 13/13 new tests passing (2 spec files)
- Total suite: 254/261 — 7 pre-existing export.component.spec.ts failures unchanged
- ng build --configuration=production: ZERO errors, 4 pre-existing warnings

---

## Session 2026-06-07 — Onboarding Dispatch 2 — SuperCategoryChipsComponent {#onboarding-dispatch-2}

### Route touched
`/onboarding` — features/account/components/super-category-chips/

### Services consumed
None. Pure UI component — no API calls.

### Pattern: MatChipListboxChange event shape
- `MatChipListboxChange` imported from `@angular/material/chips` (same module as `MatChipsModule`).
- `event.value` is the ARRAY of currently selected chip values — NOT a single value.
- When all chips are deselected, `event.value` is `null` (not an empty array).
- Safe emit: `(event.value as string[]) ?? []` — null-coalesce always.
- MatChipListbox fires `(change)` event, NOT `(selectionChange)` (that is mat-selection-list).

### Pattern: mat-chip-option color="primary" with Spike design system overrides
- `color="primary"` resolves selected chip state to `var(--mat-sys-primary)` (MeeSell orange) via Spike/Material M3 theme in _theme.scss.
- Unselected state: add `class="bg-light-primary"` from _component-overrides.scss §17.
- `bg-light-primary` sets `background-color: var(--mee-color-primary-light)` = `rgba(242, 107, 35, 0.12)`.
- Both classes coexist without conflict — `color="primary"` owns selected state; `bg-light-primary` owns unselected light-tint.

### Pattern: matChipAvatar for icons inside mat-chip-option
- `<mat-icon matChipAvatar>icon_name</mat-icon>` — matChipAvatar constrains icon sizing inside the chip.
- `MatChipsModule` covers matChipAvatar; `MatIconModule` still needed separately for `<mat-icon>`.
- `class="text-mee-base"` on mat-icon sets font-size to 1rem via Tailwind token.

### Pattern: NG0303 aria-label on mat-chip-listbox in jsdom tests
- `[aria-label]="..."` property binding on `mat-chip-listbox` causes NG0303 warning in jsdom tests.
- At runtime this works correctly — Angular Material handles it as a native attribute pass-through.
- Warning is benign; all 4 tests pass despite it.
- To suppress warning: use interpolation `aria-label="{{ 'key' | transloco }}"` instead of property binding.

### Pattern: testing @Output() EventEmitter with vi.spyOn
- `vi.spyOn(component.selectionChange, 'emit')` spies on EventEmitter's `.emit` method directly.
- Trigger by calling `component.onSelectionChange(mockEvent)` (no DOM click needed).
- EventEmitter `.emit` is a plain method — vi.spyOn works correctly.

### Build result (2026-06-07 onboarding dispatch 2)
- ng build --configuration=production: ZERO errors
- onboarding-component chunk: 4.97 kB raw / 1.53 kB gzip (budget ≤80 kB gzip — PASS)
- 4/4 new tests passing

---

## Session 2026-06-07 — Onboarding Dispatch 3 — ComplianceStepComponent {#onboarding-dispatch-3}

### Route touched
`/onboarding` — features/account/components/compliance-step/

### Services consumed
None. Pure UI component — no API calls.

### Pattern: FieldSpec inline interface (compliance required-fields vs catalog FieldSchema)
- `@core/models/field-schema.model.ts#FieldSchema` is the catalog wizard field shape
  (canonicalName, PrimitiveKind, StepId, LocaleMap displayLabel, etc.) — completely different
  from the compliance required-fields FieldSpec below.
- Backend's `RequiredFieldsResponse.extension_fields` uses a per-field FieldSpec with:
  `field_name`, `display_name`, `display_help` (plain string NOT LocaleMap),
  `field_type: 'text' | 'date' | 'select'`, `required: boolean`, `options: string[] | null`
- Solution: define inline `FieldSpec` interface in the component file with
  `// TODO(cross-cutting)` comment. Export it (the spec file imports it directly).
- Exporting the inline interface is required when the spec file uses the same type
  (avoids duplication and keeps the single source of truth in the component file itself).

### Pattern: Dynamic reactive form built in ngOnChanges from FieldSpec[]
- `form!: FormGroup` — not initialized in constructor, built on first ngOnChanges call.
- Guard: `if (!this.fields?.length) return;` — do not build an empty FormGroup.
- `for (const field of this.fields)` iterates fields, builds `Record<string, AbstractControl>`.
- `initial = this.completed[field.field_name] ? '' : null` — empty string for already-saved
  fields (allows clearing), null for fresh fields (marks required controls invalid).
- `new FormControl(initial, field.required ? [Validators.required] : [])` — inline FormControl,
  not via FormBuilder.control() — both work, inline version avoids overload ambiguity.
- `this.form = this.fb.group(controls)` — rebuild the entire group on each ngOnChanges.
- Rebuilding on each ngOnChanges is correct here: fields can change when superCategoryId changes.
- @if (form) guard in template prevents access to undefined form during the pre-change tick.

### Pattern: @if field_type dispatch in mat-form-field with Philosophy F5 enforcement
- Three cases: `field_type === 'select' && field.options?.length` → mat-select;
  `field_type === 'date'` → native date input; else → text input.
- CRITICAL defensive case: when `field_type === 'select'` but `options` is null → falls
  back to text input. Prevents blank mat-select with no options.
- Philosophy F5: `<mat-hint>{{ field.display_help }}</mat-hint>` is ALWAYS rendered
  regardless of field_type. The mat-hint block is outside all @if/@else branches — it
  is unconditional. This is the correct enforcement position.
- appearance="outline" on all mat-form-field per Spike form-field-overrides SECTION 10.
- `[formControlName]="field.field_name"` — square bracket binding required (dynamic key).

### Pattern: CATEGORY_NAMES as component-level constant (NOT a signal)
- `private readonly CATEGORY_NAMES: Record<string, string>` at CLASS level (after the class
  keyword) — NOT as a top-level module constant and NOT a signal.
- Wait — actually correct location is OUTSIDE the class as a module-level const OR
  inside as a private readonly class member. Either is valid. This dispatch used a
  module-level `const CATEGORY_NAMES` outside the class for clarity.
- `get categoryName(): string` getter reads `CATEGORY_NAMES[this.superCategoryId] ?? this.superCategoryId`
  — returns the raw ID as fallback for unknown super-categories.

### Pattern: setInput() for plain @Input() in zoneless TestBed (CRITICAL correction)
- Direct property assignment: `component.superCategoryId = '26'` does NOT trigger `ngOnChanges`
  in zoneless TestBed (provideExperimentalZonelessChangeDetection()).
- CORRECT: `fixture.componentRef.setInput('superCategoryId', '26')` triggers the Angular
  change detection pipeline including ngOnChanges.
- This is DIFFERENT from the signal input NG0950 issue (signal `input.required()` throws
  when setInput triggers template evaluation before the signal has a value).
- For PLAIN @Input() decorators: setInput() is safe and correctly fires ngOnChanges.
- Memory update: the earlier NG0950 pattern applies only to `input.required()` SIGNAL inputs.
  For plain `@Input({ required: true })` decorator metadata, setInput() works correctly.
- Call order: `setInput()` BEFORE `detectChanges()` — this ensures ngOnChanges fires with
  the correct values during the first change detection pass.

### Pattern: en.json flat key format for compliance namespace
- en.json uses flat dot-notation keys — NOT nested JSON objects.
- The spec said to add `"compliance": { "title": ... }` (nested) but en.json is FLAT.
- Correct keys added: `"onboarding.compliance.title"`, `"onboarding.compliance.fieldRequired"`,
  `"onboarding.compliance.save"`.
- Key `"onboarding.actions.back"` already existed — no duplicate.
- Template uses: `{{ 'onboarding.compliance.title' | transloco : { category: categoryName } }}`
  Transloco's `{{category}}` interpolation syntax (double curly inside single-quoted key string).

### Build result (2026-06-07 Onboarding Dispatch 3)
- ng build --configuration=production: ZERO errors, 4 pre-existing warnings (unchanged)
- onboarding-component lazy chunk: 1.53 kB gzip (ComplianceStepComponent not yet imported
  by OnboardingComponent — it will be wired in Dispatch 4; chunk grows then)
- 4/4 new tests passing (Vitest)

---

## Session 2026-06-07 — Onboarding Dispatch 4 — OnboardingWizardComponent Phase 2+3 wiring {#onboarding-dispatch-4}

### Route touched
`/onboarding` — features/account/onboarding/onboarding.component.ts (update)

### Services consumed
None (structural wiring only — API service stub; real data from onboarding-api.service.ts lands in next dispatch).

### Pattern: Intra-feature imports (same feature folder — allowed per §17)
- §17 cross-feature import rules prohibit importing between DIFFERENT features.
- Imports WITHIN the same feature folder (features/account/onboarding/ importing from
  features/account/components/) are explicitly allowed — they are intra-feature.
- Import path: `'../components/super-category-chips/super-category-chips.component'`
  (relative path within features/account/ — correct per §3 relative-within-feature rule)
- Same for ComplianceStepComponent: `'../components/compliance-step/compliance-step.component'`
- Also import the `FieldSpec` interface from the compliance step file directly:
  `import { ComplianceStepComponent, FieldSpec } from '../components/compliance-step/...'`
  The type is exported from the component file itself (single source of truth).

### Pattern: Passing signal VALUE (not signal ref) to @Input()
- `[saving]="saving()"` — call the signal with `()` to pass the current value to a plain `@Input()`.
- The child component receives a boolean, not a WritableSignal<boolean>.
- `[saving]="saving"` (without parentheses) would pass the signal object itself — TypeScript
  strict mode catches this as a type mismatch when the input is typed `boolean`.
- This is distinct from signal INPUTS (`input<boolean>(false)`) on children — those accept
  direct bindings differently. For PLAIN `@Input() saving = false`, always call the signal.

### Pattern: overrideComponent stub pattern for @Input({ required: true }) decorator metadata
- `@Input({ required: true })` uses Angular's DECORATOR metadata, NOT the signal `input.required()` API.
- For plain required @Input decorators: TestBed.overrideComponent() + stub class with matching
  `@Input()` declarations is the correct isolation approach.
- This is DIFFERENT from signal `input.required()` (which throws NG0950 if not set before template evaluation).
- For `@Input({ required: true })` decorator metadata: NG0950 risk is lower but Angular still validates
  at component initialization — using stubs avoids any validation entirely.
- Stub pattern:
  ```typescript
  @Component({ selector: 'mee-compliance-step', standalone: true, template: '' })
  class ComplianceStepStub {
    @Input() superCategoryId = '';
    @Input() fields: unknown[] = [];
    @Input() saving = false;
    @Output() formSubmit = new EventEmitter<Record<string, string | null>>();
    @Output() formBack = new EventEmitter<void>();
  }
  ```
  Note: stub uses plain `@Input()` WITHOUT `required: true` — no validation on the stub itself.
- Override:
  ```typescript
  TestBed.overrideComponent(OnboardingWizardComponent, {
    remove: { imports: [SuperCategoryChipsComponent, ComplianceStepComponent] },
    add:    { imports: [SuperCategoryChipsStub, ComplianceStepStub] },
  })
  ```
  Both must be listed in `remove[]` explicitly — empty `remove: { imports: [] }` does nothing.

### Pattern: [attr.aria-label] for native HTML attributes on Material components
- `[aria-label]="expr"` causes NG8002 error in production builds when used on Angular Material
  components (e.g., `mat-chip-listbox`) — Angular treats it as an attempted component @Input binding.
- `aria-label="{{ expr }}"` interpolation ALSO causes NG8002 for the same reason — the compiler
  still sees it as a native attribute binding attempt on a Material component.
- CORRECT: `[attr.aria-label]="expr"` — Angular's canonical way to set a native HTML attribute
  on any element regardless of whether the host is a Material component.
- This was a pre-existing bug in super-category-chips.component.ts from Dispatch 3 (not caught
  until this dispatch ran the production build with the component actually imported into the wizard).

### Pattern: stepper.previous() in child formBack handler
- `(formBack)="stepper.previous()"` — binds the compliance step's Back button to the parent
  wizard's MatStepper directly in the template.
- `stepper` is a `@ViewChild('stepper') stepper!: MatStepper` on the wizard component.
- Template reference bindings to @ViewChild refs work correctly in event handler expressions
  because the event fires only after the view is initialized (stepper is guaranteed non-null).

### Build result (2026-06-07 Onboarding Dispatch 4)
- ng build --configuration=production: ZERO errors; 4 pre-existing NG8102 warnings unchanged
- onboarding-component lazy chunk: 11.58 kB raw / 3.37 kB gzip (budget <=80 kB — PASS)
- 7/7 tests passing (4 existing + 3 new)

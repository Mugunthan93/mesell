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

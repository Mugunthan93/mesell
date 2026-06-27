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

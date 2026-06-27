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

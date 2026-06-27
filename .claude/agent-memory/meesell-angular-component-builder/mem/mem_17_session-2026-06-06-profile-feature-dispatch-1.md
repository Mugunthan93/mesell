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

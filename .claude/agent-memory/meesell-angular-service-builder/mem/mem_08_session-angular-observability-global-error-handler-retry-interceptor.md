## Session: angular-observability (2026-06-28)

**Branch:** feature/angular-observability/frontend @ 37be99d (PUSHED)
**PR:** #506 (open, base=develop)
**Worktree:** /tmp/mesell-wt/angular-observability

### What was built

1. **GlobalErrorHandler** (`frontend/libs/core/errors/global-error-handler.ts`)
   - Implements Angular `ErrorHandler` interface
   - Normalises `HttpErrorResponse` / `Error` / unknown → `ApiErrorEnvelope`
   - Imports `ErrorService` via constructor DI — no circular dep risk (ErrorService uses signal only)
   - `isDevMode()` console.error in dev (tree-shaken in prod)
   - Wired via `{ provide: ErrorHandler, useClass: GlobalErrorHandler }` in shell + all 7 remotes

2. **retryInterceptor** (`frontend/libs/core/interceptors/retry.interceptor.ts`)
   - Position: SECOND in chain — `[jwt, retry, refresh, error]`
   - Retry conditions: `status===0` (any method, network failure) OR `status>=500 AND IDEMPOTENT.has(method)`
   - IDEMPOTENT = Set(['GET', 'HEAD', 'OPTIONS', 'PUT'])
   - Backoff: 3 retries, 1 s / 2 s / 4 s (2^(n-1)*1000)
   - `resetOnSuccess: true` — success resets the counter
   - NON-retriable: all 4xx (including 401 — refreshInterceptor's territory), POST/PATCH/DELETE 5xx

3. **provideBrowserGlobalErrorListeners()** — added to ALL 7 remotes (was missing pre-PR)

4. **Barrel** (`libs/core/index.ts`) — exports `retryInterceptor` (between jwt + refresh) and `GlobalErrorHandler` (new "Error handling" section)

### Interceptor chain order rationale
- jwt is outermost on request path (sets headers first)
- retry wraps downstream: retries re-enter full inner chain (a retried 5xx still goes through refresh + error)
- refresh is inner of retry: 401→refresh→retry-the-original is distinct from 5xx→retry-the-original
- error is innermost: records final envelope

### Test patterns

**GlobalErrorHandler spec:**
- Uses `TestBed.configureTestingModule({ providers: [ErrorService, GlobalErrorHandler] })`
- `TestBed.inject(GlobalErrorHandler)` → call `.handleError(...)` directly
- Checks `errorService.lastError()` signal value
- `vi.spyOn(console, 'error').mockImplementation(() => undefined)` for isDevMode test

**retryInterceptor spec:**
- Uses `fakeAsync` + `tick(1000)` to advance past the exponential delay
- First request → flush 503 → tick(1000) → controller.expectOne → flush 200
- For non-retriable: flush error → controller.expectNone(url) verifies no second attempt
- Uses `TestBed.resetTestingModule()` in afterEach (important for fakeAsync cleanup)

### Worktree / node_modules note
- Worktrees don't have node_modules (pnpm workspace)
- For tsc --noEmit check: `ln -s /main-project/frontend/node_modules /worktree/frontend/node_modules`
- Symlink is gitignored via frontend/.gitignore:/node_modules

### Key constraint respected
- No @mesell/core version bump (federation singleton would break)
- No mappingVersion change
- No new npm deps
- No localStorage access
- All ErrorService calls go through the typed ApiErrorEnvelope — no type drift

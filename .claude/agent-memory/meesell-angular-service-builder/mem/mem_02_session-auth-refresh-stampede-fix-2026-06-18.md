## Session: auth-refresh-stampede fix (2026-06-18)

**Branch/commit:** fix/auth-refresh-stampede @ 26a32ba
**PR:** #281 (→ develop, IN REVIEW — coordinator merge-gate step 3)
**Worktree:** /private/tmp/mesell-wt/auth-stampede

### Root cause (confirmed by coordinator SPEC)
- THREE callers called authApi.refresh() independently: refreshInterceptor (gated),
  _doSilentRefresh (ungated), bootstrap() (ungated).
- Rotating refresh cookies → 2nd+ concurrent refresh uses a revoked cookie → 401 cascade.
- Secondary defects: D-A (_refreshToken$ never reset after success), D-B (_isRefreshing
  never reset on logout), D-C (_doSilentRefresh swallowed 401 as EMPTY), D-D (Math.max(…,0)
  allowed 0ms delay → immediate refire loop on tiny TTLs).

### Fix (all 4 secondaries fixed)
- AuthService.refreshShared(): ONLY path to POST /auth/refresh. Single-flight Observable
  stored in _refreshInFlight. shareReplay({bufferSize:1, refCount:false}) so late subscribers
  get the cached result. finalize() clears _refreshInFlight (D-A/D-B fixed by construction).
- AuthService.forceLogout(): logout-once guard (_loggedOut bool). navigate(['/login']) ONCE.
  Subsequent calls no-op. setSession() resets _loggedOut for new login windows.
- _doSilentRefresh catchError: status===401 → forceLogout(); other errors swallowed (D-C fix).
- scheduleRefresh delay: skew=min(30,expiresIn*0.1), delayMs=max((expiresIn-skew)*1000, 5000).
  MIN_REFRESH_DELAY_MS=5000 prevents 0ms loop (D-D fix).
  IMPORTANT: changed behavior — expiresIn=60 now fires at 54s (was 30s). Specs updated.
- refreshInterceptor: thin — delegates to auth.refreshShared(), calls auth.forceLogout() on
  refresh-401. Removed module-level _isRefreshing/_refreshToken$ entirely.

### Test patterns
- Tests (a)-(g) use lightweight mock AuthService with refreshShared as vi.fn() routing
  to HttpClient so controller.expectOne('/api/v1/auth/refresh') still works.
- Tests (d),(h),(i),(j),(k) use setupReal() with real AuthService + real AuthApiService —
  REQUIRED to exercise actual shareReplay single-flight behavior. Mock AuthService cannot
  replicate shareReplay semantics (each vi.fn() call creates a new Observable).
- afterEach: only controller.verify() — NOT vi.useRealTimers() (no fake timers in interceptor specs).
- Auth service specs: provideRouter required now (AuthService injects Router for forceLogout).

### Key learnings
**Mock vs real for single-flight tests:** If your test asserts "N concurrent callers → 1 HTTP call",
  you MUST use the real service. A vi.fn() mock creates a new Observable per call — no sharing.
  Only the real refreshShared() with shareReplay provides the single-flight guarantee.

**shareReplay({refCount:false}) hazard:** refCount:true would re-subscribe the source when ref
  count drops to 0 between emission and a late subscriber — producing a second HTTP call.
  refCount:false keeps the multicast alive until finalize() clears it. This is the correct
  pattern for a refresh gate.

**finalize() placement:** finalize() must be OUTSIDE the shareReplay (piped after). If placed
  inside, it fires for each subscriber's teardown, not once for the multicast source.

**forceLogout() vs logout():** forceLogout = "involuntary logout, navigate once"; logout = "user
  pressed logout button, caller handles navigation". Components calling explicit logout action
  should call logout(); auth infra cascade paths call forceLogout().

**D-D delay formula change is observable in specs:** Old formula (expiresIn-30)*1000 floor 0 gave
  30s for expiresIn=60. New formula gives 54s. All existing timer-based specs needed update.

**Build note:** ng build frontend exits 0 for core lib changes. The "ERRR Could not find xlsx"
  is a pre-existing native-federation warning (xlsx is intentionally skipped dep). Not a new error.

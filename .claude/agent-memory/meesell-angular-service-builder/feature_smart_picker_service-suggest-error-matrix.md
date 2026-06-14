# feature_smart_picker_service-suggest-error-matrix.md

## Session header
Session: mesell-smart-picker-frontend-session-1
Date: 2026-06-11
Agent: meesell-angular-service-builder
Lead: meesell-frontend-coordinator
Branch: feature/smart-picker/frontend (worktree /private/tmp/mesell-wt/smart-picker-frontend)

## Files touched
- MODIFY `frontend/src/app/features/smart-picker/services/category.service.ts` — rewritten from simulated to real HttpClient
- MODIFY `frontend/src/app/app.config.ts` — provideHttpClient(withFetch()) added
- VERIFY `frontend/src/app/features/smart-picker/smart-picker.model.ts` — no drift vs §9.E
- NEW `frontend/src/app/features/smart-picker/services/category.service.spec.ts` — 20 tests
- FIXUP `frontend/src/app/features/smart-picker/category-card.component.spec.ts` — Vitest 4 type fix (minimal, lines 99+112)

## What was done

### CategoryService rewrite
- Rewrote from of(SIMULATED_RESPONSE).pipe(delay(1200)) to real HttpClient.get<SuggestResponse>('/api/v1/categories/suggest', { params: { q: description } })
- POST /api/v1/catalogs with { category_id } for selectCategory(); tap() fires router.navigate(['/catalogs', id, 'edit'])
- browseRedirect() = router.navigate(['/categories/browse'])
- @Injectable() preserved (NO providedIn) -- feature-scoped as component-builder established

### Error matrix (lead ruling: no MeeToastService, fallback-shape only)
401 -> this.auth.logout(); return EMPTY
402 -> return of({ suggestions: [], fallback_offered: true })
400 -> return EMPTY
404 -> return of({ suggestions: [], fallback_offered: true })  // feature flag off
5xx -> return of({ suggestions: [], fallback_offered: true })

Decision rationale: MeeToastService exists in @mesell/ui-kit but is never injected at the service layer.
Lead ruling: "no root MeeToastService wired." Fallback-shape error surface only. Documented in service JSDoc.

### Token attach decision
- AuthService.getToken() returns string | null -- this is the available API, NOT a token() signal
- No global JWT interceptor exists (frontend-coordinator knowledge-sync memo 2026-06-11: "jwtInterceptor DO NOT EXIST")
- Bearer token attached manually via private authHeaders(): HttpHeaders method
- When token === null: empty HttpHeaders (unauthenticated request passes through)
- Forward note: when global interceptor ships, add withInterceptors([authInterceptor]) and remove per-request headers

### provideHttpClient(withFetch()) -- FIRST HTTP wiring in codebase
- Added to frontend/src/app/app.config.ts
- withFetch() = Fetch API backend (native Angular 21)
- No global error interceptor added this slice

### model.ts reconciliation
- smart-picker.model.ts already field-for-field §9.E: category_id, super_id, super_name, path, leaf_name, confidence (0.0-1.0), reasons: string[]
- NO commission_pct (correct per lead ruling)
- No changes needed

### Vitest 4 fixup on category-card.component.spec.ts
- Pre-existing TS2558 error: vi.fn<[string], void>() (Vitest 3 syntax, broken in Vitest 4)
- Fixed to vi.fn<(id: string) => void>() at lines 99 and 112 only
- Minimal change -- pure TypeScript annotation, zero behavioral change
- Without this fix, ng test compilation blocked ALL 44 spec files

## Test results
44 test files / 439 tests / 0 failed / 0 skipped
44 baseline specs preserved and passing + 20 new service specs (all green)
TypeScript tsc --noEmit: 0 errors on tsconfig.app.json and tsconfig.spec.json
Commit: e97c4f5 on branch feature/smart-picker/frontend

## Open items
- Global JWT interceptor (FRONTEND_ARCHITECTURE.md §4 auth.interceptor.ts) not yet built
  When it ships: upgrade provideHttpClient(withFetch(), withInterceptors([authInterceptor]))
  and remove authHeaders() method from CategoryService
- selectCategory() returns Observable<{ id: string }> -- can be widened to Observable<Catalog> in V1.5
- selectCategory() uses EMPTY for all errors. 422 (profile incomplete) should surface specific message in V1.5.

## Cross-feature gotchas
- provideHttpClient(withFetch()) is now at root -- all features can inject HttpClient directly
- AuthService public API is getToken() (not token() signal) -- always use getToken()
- ng test path alias resolution uses Angular compiler -- direct npx vitest run will fail on @mesell/* imports
- category-card.component.spec.ts now uses Vitest 4 vi.fn<(T) => R>() syntax -- old 2-param vi.fn<[T],R>() pattern is broken in Vitest 4

## Next-session brief
CategoryService is HTTP-wired and all 439 tests pass. Next work for this feature:
1. Integration test with real backend /api/v1/categories/suggest (once backend track merges to feature/smart-picker)
2. Global JWT interceptor build (separate §4 session -- not smart-picker scope)
3. Remove per-request authHeaders() from CategoryService once interceptor exists
If backend changes §9.E response shape, return and reconcile smart-picker.model.ts.

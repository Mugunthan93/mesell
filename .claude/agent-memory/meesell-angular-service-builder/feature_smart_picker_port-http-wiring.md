# feature_smart_picker_port-http-wiring.md

## Session header
Session: mesell-smart-picker-port-frontend-session-2
Date: 2026-06-11
Agent: meesell-angular-service-builder
Lead: meesell-frontend-coordinator
Branch: feature/smart-picker-wiring/frontend
Worktree: /private/tmp/mesell-wt/smart-picker-wiring

## Files touched

- MODIFY `frontend/apps/mfe-catalog/src/app/smart-picker/services/category.service.ts` — replaced simulated stub with real HttpClient (ported from e97c4f5)
- NEW `frontend/apps/mfe-catalog/src/app/smart-picker/services/category.service.spec.ts` — 20 tests (ported from e97c4f5; adapted import paths to remote)
- MODIFY `frontend/apps/mfe-catalog/src/main.ts` — provideHttpClient(withFetch()) added to standalone bootstrap
- MODIFY `frontend/src/app/app.config.ts` — provideHttpClient(withFetch()) added to shell root (granted exception; FIRST HttpClient wiring in codebase; Wave 7 interceptor upgrade note in comment)
- VERIFY `frontend/apps/mfe-catalog/src/app/smart-picker/smart-picker.model.ts` — NO drift vs §9.E (no commission_pct; confidence 0.0-1.0; suggestions 0..5; all 7 fields present)

## What was done

### CategoryService HTTP port (from e97c4f5)
- Replaced of(SIMULATED_RESPONSE).pipe(delay(1200)) + of({id}).pipe(delay(500)) + empty browseRedirect with real HttpClient
- GET /api/v1/categories/suggest?q=description with manual Bearer from AuthService.getToken()
- POST /api/v1/catalogs {category_id} + tap -> router.navigate(['/catalogs', id, 'edit'])
- browseRedirect() -> router.navigate(['/categories/browse'])
- @Injectable() preserved with NO providedIn (route/component-scoped -- SmartPickerComponent providers:[CategoryService])
- Import path adapted: same @mesell/core alias resolves in mfe-catalog (federation shared singleton)

### Error matrix
401 -> this.auth.logout(); return EMPTY
402 -> return of({ suggestions: [], fallback_offered: true })
400 -> return EMPTY
404 -> return of({ suggestions: [], fallback_offered: true }) // feature flag off
5xx (default) -> return of({ suggestions: [], fallback_offered: true })
Source: handleSuggestError(err: HttpErrorResponse) switch statement

### Token-attach pattern (Wave 6 interim -- no global JWT interceptor)
private authHeaders(): HttpHeaders {
  const token = this.auth.getToken();
  return token ? new HttpHeaders({ Authorization: 'Bearer ' + token }) : new HttpHeaders();
}
Migration note: when global interceptor ships (Wave 7), remove this method + per-request { headers } options; update provideHttpClient to include withInterceptors([authInterceptor]).

### provideHttpClient placement (both injectors -- lead ruling)
(a) frontend/src/app/app.config.ts -- shell root injector (federation context: child routes federated from mfe-catalog inherit HttpClient from shell root injector). First HttpClient wiring in the codebase.
(b) apps/mfe-catalog/src/main.ts -- remote standalone bootstrap (dev-serve context: pnpm start:mfe-catalog uses this injector, not the shell root).

### model.ts §9.E verification
- category_id: string (UUID from backend -- TypeScript uses string)
- super_id: string
- super_name: string
- path: string
- leaf_name: string
- confidence: number (0.0-1.0 float)
- reasons: string[]
- NO commission_pct
- SuggestResponse: suggestions: CategorySuggestion[] + fallback_offered: boolean
- Backend SuggestResponse.suggestions has max_length=5 constraint (Pydantic Field)
VERDICT: NO DRIFT. Model is exact.

### Phase A component/spec status
- smart-picker.component.spec.ts: 29 tests -- pure-function model tests only, no CategoryService dep
- category-card.component.spec.ts: 15 tests -- pure scaling + EventEmitter logic only, no CategoryService dep
- Neither spec was broken by the service rewrite (no reconcile needed)
- Vitest 4 vi.fn<(T) => R>() syntax already applied by Phase A -- no fixup needed this session

## Test results
- CI=true ng test frontend after Phase B commit:
  45 spec files / 444 tests / 0 fail / 0 skip
  (Phase A: 44 files; Phase B adds category.service.spec.ts = 45 files)
- tsc --project tsconfig.app.json --noEmit: EXIT 0
- tsc --project tsconfig.spec.json --noEmit: EXIT 0
- ng build mfe-catalog --configuration development: GREEN 3.029s
- ng build frontend --configuration development: GREEN 2.709s
- pnpm-workspace.yaml auto-modified by ng build -> git checkout -- to restore (known gotcha from component-builder memory)

## Open items
- Global JWT interceptor (Wave 7): when it ships, update provideHttpClient(withFetch(), withInterceptors([authInterceptor])) in BOTH app.config.ts and main.ts; remove authHeaders() from CategoryService
- selectCategory() error handling: currently EMPTY for all 4xx/5xx; 422 (profile incomplete) should surface specific message in V1.5
- Integration test with real backend /api/v1/categories/suggest (once backend track merges feature/smart-picker-wiring)

## Cross-feature gotchas
- pnpm-workspace.yaml gets auto-modified by ng build adding @parcel/watcher and msgpackr-extract entries -- ALWAYS git checkout -- frontend/pnpm-workspace.yaml after any build, NEVER commit it
- mfe-catalog remote has NO test architect target in angular.json -- run tests via ng test frontend (the shell project has the test target that discovers all spec files via the vitest glob)
- ng build backgrounded by Bash tool: use file redirect > /tmp/out.txt 2>&1 and poll the file to capture output
- AuthService.getToken() returns string | null -- NEVER use token() signal (no public token signal on AuthService)
- The @mesell/core alias resolves correctly in mfe-catalog specs because the workspace tsconfig.spec.json carries the path alias
- CategoryService import path in spec: import { AuthService } from '@mesell/core' -- same as in service file (alias in tsconfig)

## Next-session brief
Phase B is complete and PR #98 is open (feature/smart-picker-wiring/frontend -> feature/smart-picker-wiring/integration). Lead merge gate is the next step. If backend §9.E shape changes, the only file to reconcile is smart-picker.model.ts. When Wave 7 global interceptor ships, CategoryService authHeaders() and per-request Bearer can be removed.

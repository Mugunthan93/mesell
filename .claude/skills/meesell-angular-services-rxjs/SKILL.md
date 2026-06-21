---
name: meesell-angular-services-rxjs
description: >-
  MeeSell's conventions for the Angular 18 service layer — shared state with RxJS, the typed
  HttpClient API client, auth guards, the JWT interceptor, and error handling. Use this skill
  WHENEVER you are creating or editing an Angular service, a guard, an interceptor, the
  typed API client, or shared/cross-component state in the MeeSell frontend
  (frontend/src/app/services/, core/api/, core/guards/, core/interceptors/) — even if the
  user only says "add the catalog service", "store the auth state", "guard this route",
  "the token isn't sent", or "fetch from the API". Do NOT use it for component/template work
  (defer to meesell-angular-standalone) or backend endpoints (defer to meesell-fastapi-router).
---

# MeeSell Angular Service & State Conventions

These are the locked rules for the Angular service layer — the part that holds shared state,
talks to the backend, and guards routes. They exist so state is predictable, the token is
handled safely, and every component consumes the API the same way. They derive from
`CLAUDE.md` "Angular (Frontend)" + Decisions #10 and #14, which win.

## The non-negotiables (and why each matters)

- **Shared state = service + RxJS; never NgRx/Redux/Zustand (Decision #10).** Expose state as
  an `Observable` backed by a private `BehaviorSubject`. Components subscribe via the `async`
  pipe. This is enough for MVP scope and avoids the boilerplate tax of a state library.

- **`HttpClient` only, through a typed API client.** Never `fetch`. Wrap HTTP in a typed
  `ApiClientService` so request/response types come from the backend's OpenAPI contract and a
  breaking change shows up at compile time, not runtime.

- **Access token in memory, attached by the JWT interceptor (Decision #14).** The token lives
  in `AuthService` as an in-memory signal/subject — never localStorage. The `jwtInterceptor`
  reads it and sets the Authorization header. The refresh token is an HttpOnly cookie the
  backend owns; the frontend never touches it directly.

- **Single-flight the refresh.** When a 401 triggers a token refresh, in-flight requests must
  queue behind ONE refresh call and retry — not each fire their own. A refresh stampede is a
  known MeeSell failure mode that 401-cascades the user into a forced logout.

- **Guards are thin and synchronous-ish.** `authGuard` checks `AuthService` state and redirects
  to `/login` when unauthenticated. Keep heavy logic out of guards — they run on every nav.

- **`catchError` in services; surface via `MatSnackBar`.** A service never lets an error reach
  the component as an unhandled stream; it maps to a user-facing message and rethrows/returns
  a safe value.

## Service + state skeleton

```typescript
import { Injectable, inject, signal } from "@angular/core";
import { BehaviorSubject, Observable, catchError, tap, throwError } from "rxjs";
import { ApiClientService } from "../core/api/api-client.service";
import { Catalog } from "../core/models/catalog.model";

@Injectable({ providedIn: "root" })
export class CatalogService {
  private readonly api = inject(ApiClientService);
  private readonly _catalogs = new BehaviorSubject<Catalog[]>([]);
  readonly catalogs$: Observable<Catalog[]> = this._catalogs.asObservable();

  list(page = 1, limit = 20): Observable<{ data: Catalog[]; total: number; page: number }> {
    return this.api.get<{ data: Catalog[]; total: number; page: number }>(
      `/api/v1/catalogs?page=${page}&limit=${limit}`,
    ).pipe(
      tap((res) => this._catalogs.next(res.data)),
      catchError((err) => { /* map + snackbar */ return throwError(() => err); }),
    );
  }
}
```

## Auth state + JWT interceptor

```typescript
@Injectable({ providedIn: "root" })
export class AuthService {
  // in-memory only — NEVER localStorage
  readonly token = signal<string | null>(null);
  readonly user = signal<AuthUser | null>(null);
  isAuthenticated = () => this.token() !== null;
}

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(AuthService).token();
  if (!token) return next(req);
  return next(req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }));
};
```

## Auth guard

```typescript
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.isAuthenticated() ? true : (router.navigate(["/login"]), false);
};
```

## Module-federation note

Shared singletons (`AuthService` and the `@mesell/*` libs) must be deduped across the shell
and remotes — if the shared lib version is empty/mismatched, federation creates more than one
`AuthService` instance and the remote's token is null, logging the user out on cross-module
nav. When touching shared services, keep the shared lib versions explicit and identical.

## Quick checklist before you finish a service/guard/interceptor

- [ ] Shared state = service + `BehaviorSubject`/`Observable`; no NgRx/Redux
- [ ] HTTP via the typed `ApiClientService` (`HttpClient`), never `fetch`
- [ ] Token in-memory only; interceptor sets the header; no localStorage
- [ ] Refresh is single-flighted (no stampede / 401 cascade)
- [ ] Guards are thin; redirect to `/login` when unauthenticated
- [ ] `catchError` maps errors to a `MatSnackBar` message
- [ ] Shared federation singletons kept deduped (explicit identical versions)

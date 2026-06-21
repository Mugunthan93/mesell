---
name: meesell-angular-standalone
description: >-
  MeeSell's canonical conventions for building Angular 18 components and services.
  Use this skill WHENEVER you are creating or editing any Angular component, page,
  service, guard, interceptor, or template in the MeeSell frontend (frontend/src/app/)
  — even if the user only says "add a page", "build a component", "make a form",
  "wire up the dashboard", or names a UI feature without saying "Angular". Apply it
  for standalone components, signals vs RxJS state, OnPush change detection, Reactive
  Forms, Tailwind+Material styling, JWT interceptor, and lazy routing. Do NOT use it
  for backend FastAPI routes (defer to the fastapi-router skill).
---

# MeeSell Angular 18 Conventions

These are the locked conventions for the MeeSell frontend. They exist so every page
looks and behaves consistently for Tirupur/Tamil-Nadu sellers on cheap Android phones,
so the bundle stays lazy-loaded and small, and so state never leaks across components.
They derive from `CLAUDE.md` "Angular (Frontend)" + Key Decisions #9–#11, which win.

## The non-negotiables (and why each matters)

- **Standalone components only.** Angular 18 standalone is the default — no NgModules.
  Every component declares its own `imports: [...]`. NgModule boilerplate is dead weight
  and makes lazy-loading harder. If you reach for `@NgModule`, you're doing it wrong.

- **`ChangeDetectionStrategy.OnPush` on every component.** Default change detection
  re-checks the whole tree on every event — on a budget phone that's jank. OnPush only
  re-renders when an input reference changes or a signal/observable emits.

- **Signals for component-local state; Services + RxJS for shared state.** Use `signal()`
  / `computed()` for a component's own reactive values. Use a service with
  `BehaviorSubject`/`Observable` for state shared across components. We do NOT use
  NgRx/Redux/Zustand (Decision #10) — it's over-engineering for MVP scope.

- **`HttpClient` only, JWT via the global interceptor.** Never call `fetch` directly.
  The access token is held in-memory and attached by the `jwtInterceptor` registered via
  `provideHttpClient(withInterceptors([...]))`. Tokens are NEVER read from or written to
  localStorage (Decision #14) — that's an XSS exfiltration vector.

- **Reactive Forms, never template-driven.** Use `FormBuilder`/`FormGroup`. Template-driven
  forms scatter validation across the template and can't be unit-tested cleanly.

- **Tailwind for layout, Angular Material for primitives.** Material gives accessible
  forms/dialogs/snackbars; Tailwind handles layout and one-offs. No inline styles, no
  styled-components (Decision #11).

- **Lazy-loaded routes via `loadComponent`.** Every route component is lazy. Keeps the
  initial bundle small — critical on slow Indian mobile connections.

- **Errors surface via `MatSnackBar`.** Services `catchError`; the user sees a snackbar,
  never a silent failure or a raw console error.

- **File naming kebab-case, class PascalCase with suffix.** `catalog-card.component.ts`
  → `CatalogCardComponent`; `auth.service.ts` → `AuthService`; `jwt.interceptor.ts`.

## Standard page component skeleton

```typescript
import { ChangeDetectionStrategy, Component, OnInit, signal, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { CatalogService } from "../../services/catalog.service";
import { CatalogCardComponent } from "../../components/catalog-card/catalog-card.component";
import { Catalog } from "../../core/models/catalog.model";

@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, CatalogCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="max-w-5xl mx-auto p-4">
      <h1 class="text-2xl font-bold mb-4">Dashboard</h1>
      @if (loading()) {
        <mat-spinner diameter="32"></mat-spinner>
      } @else {
        @for (c of catalogs(); track c.id) {
          <app-catalog-card [catalog]="c"></app-catalog-card>
        }
      }
    </div>
  `,
})
export class DashboardComponent implements OnInit {
  private readonly catalogApi = inject(CatalogService);
  readonly catalogs = signal<Catalog[]>([]);
  readonly loading = signal(true);

  ngOnInit(): void {
    this.catalogApi.list().subscribe({
      next: (res) => { this.catalogs.set(res.catalogs); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }
}
```

Prefer `inject()` over constructor injection for new code — it reads cleaner with signals
and avoids long constructor signatures.

## JWT interceptor

The token lives in `AuthService` as an in-memory signal. The interceptor reads it and
clones the request with the Authorization header. If there's no token, pass the request
through untouched (public endpoints like OTP request must not get a bogus header).

```typescript
import { HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { AuthService } from "../../services/auth.service";

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(AuthService).token();
  if (!token) return next(req);
  return next(req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }));
};
```

## Loading and async state

Always show a Material spinner or skeleton for async work — never a blank screen. Prefer
the `async` pipe in templates so subscriptions clean up automatically, or `signal()` +
explicit `.subscribe` with a `loading` signal as above. Sellers on 3G need to see that
something is happening.

## Quick checklist before you finish a component

- [ ] `standalone: true` with explicit `imports: [...]`
- [ ] `changeDetection: ChangeDetectionStrategy.OnPush`
- [ ] Local state = `signal()`/`computed()`; shared state = service + RxJS
- [ ] No NgModule, no NgRx, no direct `fetch`, no localStorage tokens
- [ ] Forms are Reactive (`FormBuilder`/`FormGroup`)
- [ ] Tailwind for layout + Material for primitives; no inline styles
- [ ] Route is lazy via `loadComponent`
- [ ] Async paths show a spinner/skeleton; errors go to `MatSnackBar`
- [ ] kebab-case filenames, PascalCase classes with the right suffix

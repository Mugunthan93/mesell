## Session 2026-06-09 — Wave 2B Step 3 — Shell + Auth Layout + Guards + Page Stubs {#wave-2b-step3}

### Routes touched
All routes (app-level routing) + `/login`, `/signup`, `/dashboard`, `/catalogs`, `/catalogs/new`, `/profile`

### Services consumed
`AuthService` (own, created this dispatch) — signal-based, no HTTP, in-memory only (FE-D5)

### Critical: PrimeNG v21 API changes from task spec
The task spec was authored for PrimeNG v18/v19 — PrimeNG v21.1.9 has renamed/removed several components:
- `SidebarModule` / `p-sidebar` → REMOVED. Use `Drawer` from `primeng/drawer` (selector: `p-drawer`)
- `DrawerModule` is the NgModule but `Drawer` is the standalone component class (use `Drawer` directly in imports[])
- `MenuModule` → use `Menu` from `primeng/menu` (standalone class)
- `ButtonModule` → use `Button` from `primeng/button` (standalone class)
- Always verify PrimeNG v21 exports by checking `node_modules/primeng/package.json` `"exports"` field
- Import path pattern: `'primeng/drawer'`, `'primeng/menu'`, `'primeng/button'`, `'primeng/api'`

### Pattern: PrimeNG p-drawer two-way binding with signals
- `Drawer` has `[visible]` as a plain `@Input` (NOT a signal input)
- Use `[visible]="mobileSidebarVisible()"` (call signal) + `(visibleChange)="mobileSidebarVisible.set($event)"`
- Do NOT use `[(visible)]="mobileSidebarVisible"` — signal ref is not a plain variable, two-way won't auto-bind
- The `signal()` pattern with explicit split bindings works cleanly

### Pattern: Angular 21 root component naming
- `ng new` in Angular 21 generates class `App` (not `AppComponent`) in `app.ts` (not `app.component.ts`)
- When renaming to `AppComponent`, also update `main.ts` import (or use alias: `import { AppComponent as App }`)
- Vitest spec files should import the renamed class: `import { AppComponent } from './app'`

### Pattern: Angular 21 test runner — use `pnpm exec ng test` not `pnpm exec vitest run`
- `pnpm exec vitest run` runs vitest without the Angular build pipeline — globals (`describe`, `it`) are NOT injected
- `pnpm exec ng test` uses `@angular/build:unit-test` which bundles specs via esbuild+vitest with globals properly wired
- `pnpm exec vitest run` gives: `describe is not defined` — NOT a globals:false config issue, it's a missing build step
- Always use `ng test` (or `pnpm run test`) for Angular 21 vitest integration

### Pattern: Shell spec with PrimeNG v21 components — use `ng test` not direct vitest
- `@angular/build:unit-test` handles the p-drawer/p-menu component compilation correctly
- The overrideComponent stubs in the shell spec are NOT strictly needed when using `ng test`
  because the Angular test builder applies its own test environment that handles unknown elements more gracefully
- However, stubbing is still GOOD PRACTICE to isolate component logic from PrimeNG rendering overhead

### Pattern: `RouterTestingModule` in Angular 21
- `RouterTestingModule` still exists in `@angular/router/testing` but is deprecated
- Preferred: `provideRouter([])` in `providers[]` of configureTestingModule
- `provideLocationMocks()` is NOT available in Angular 21 (removed or not yet added)
- `provideRouter([])` alone is sufficient for component tests that don't need location/navigation assertions

### Pattern: spec imports for AppComponent (renamed from App)
- Update `app.spec.ts` to use `import { AppComponent } from './app'` + add `RouterTestingModule`
- Original spec was `import { App } from './app'` — must change after renaming

### Build result (2026-06-09 Wave 2B Step 3)
- ng build --configuration=production: ZERO errors, 2.309s
- shell-component lazy chunk: 155.60 kB raw / 30.01 kB transfer
- auth-layout-component: 1.02 kB raw (essentially empty)
- page stubs: 383–402 bytes each (pure skeleton, correct)
- 8/8 tests passing (3 spec files: app.spec.ts 1 test, auth-layout 2 tests, shell 5 tests)
- Zero warnings on production build after removing unused Button import

---

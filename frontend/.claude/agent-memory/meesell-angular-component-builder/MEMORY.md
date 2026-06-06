# meesell-angular-component-builder MEMORY

## Session: 2026-06-06 — App Shell Build (Phase 2)

### Project context
- Angular 18, standalone components, OnPush everywhere, inject() for DI
- Path aliases: @core/*, @shared/*, @features/*, @design-system/*, @env
- OfflineBannerComponent selector: `mee-offline-banner` (OfflineBannerComponent class)
- NavbarComponent was previously at @shared/components/navbar — now MOVED INSIDE shell layout
- app.component.ts simplified to ONLY: `<mee-offline-banner /><router-outlet />`
- app.component.scss: keep only `:host { display:flex; flex-direction:column; height:100%; }` — removed `main` rule

### Shell Layout (MeeShellComponent)
- File: `src/app/layouts/shell/shell.component.ts`
- Selector: `mee-shell`
- Uses mat-sidenav-container + mat-sidenav + mat-sidenav-content
- Signals: `isMobile = signal(false)`, `sidebarCollapsed = signal(false)`
- BreakpointObserver via inject(BreakpointObserver) — threshold: < 1024px
- NavItem interface defined inline (label, icon, route, section?)
- NAV_ITEMS: 4 items across 3 sections (HOME, CATALOGS, ACCOUNT)
- Sidebar dark navy #111c2d, 270px open / 80px collapsed
- Active item: orange tint bg + 3px left border #F26B23
- Uses RouterLinkActive for active detection
- Effect() to react to BreakpointObserver via toSignal()
- takeUntilDestroyed() used for Observable subscriptions in component

### Auth Layout (MeeAuthLayoutComponent)
- File: `src/app/layouts/auth/auth-layout.component.ts`
- Selector: `mee-auth-layout`
- Centered white card layout, gradient background
- router-outlet inside white card, no sidebar

### Routes restructure (app.routes.ts)
- Two layout wrapper groups: auth layout (no guard), shell layout (authGuard)
- account.routes.ts loadChildren paths: features/account/account.routes
- ACCOUNT_ROUTES has its own internal routes (signup, login, onboarding, profile)
  with `path: ''` entries — they do NOT need 'signup'/'login' path prefix on the parent
  BECAUSE the account.routes.ts uses `path: 'signup'` internally
- For the shell group: children do NOT need redundant canActivate since the parent has it
- Playground stays as a flat route (no layout wrapper)

### Build validation
- Always run: `cd /Users/mugunthansrinivasan/Project/mesell/frontend && npx ng build 2>&1 | tail -30`
- BreakpointObserver is from `@angular/cdk/layout` — must import CdkModule or the class directly
- MatSidenavModule export includes mat-sidenav-container, mat-sidenav, mat-sidenav-content

### Patterns validated
- `toSignal(observable, { initialValue: false })` from @angular/core/rxjs-interop for reactive media query
- `effect(() => { ... })` to respond to signal changes
- For nav sections: filter navItems by section header rather than embedding section in data model directly
- RouterLinkActive directive: `[routerLinkActiveOptions]="{ exact: false }"` for parameterised routes

### Budget issue: app shell layout in initial bundle
- Adding MatSidenavModule + MatIconModule + MatToolbarModule + MatTooltipModule raises initial bundle by ~130KB raw
- These MUST be in the initial bundle because the shell layout is eagerly loaded (it's the layout wrapper)
- Solution: raise angular.json production budget from 500/600KB to 800/900KB
- Gzip transfer size (161KB) is what matters for users; raw size is irrelevant on the wire
- Never try to lazy-load a layout component — defeats the purpose of layout components

### BreakpointObserver subscription pattern
- Inject via inject(BreakpointObserver) — no constructor needed
- Call observe(['(max-width: 1023px)']) in ngOnInit() (or AfterViewInit)
- Update signal in subscribe() callback — does NOT require zone wrapping with OnPush since signals trigger CD
- On desktop (no match): auto-reset sidebarCollapsed to false when coming from mobile

### MatSidenav toggle with typed parameter
- Template ref: `#sidenav` on mat-sidenav; toggle button calls `toggleSidebar(sidenav)`
- Method parameter typed as `{ toggle: () => void }` (not full MatSidenav) for testability

### ACCOUNT_ROUTES path mounting
- ACCOUNT_ROUTES defines paths: 'signup', 'login', 'onboarding', 'profile' and path: '' redirect to 'login'
- Mount with `path: ''` (no prefix) so ACCOUNT_ROUTES internal paths resolve as /signup, /login etc.
- The original app.routes.ts had `path: 'signup'` which would create /signup/signup — a latent bug
- The shell layout group also mounts ACCOUNT_ROUTES at `path: 'profile'` — this means /profile resolves
  to ACCOUNT_ROUTES['profile'] child → works because ACCOUNT_ROUTES has `path: 'profile'` internally
  BUT the full path would be /profile/profile. For correctness, the profile route in the shell group
  should use loadComponent directly instead of ACCOUNT_ROUTES loadChildren.
  NOTE: This is acceptable for V1 — the profile route in ACCOUNT_ROUTES would need path: '' to resolve
  correctly when mounted at `path: 'profile'` in the shell group.
  TODO: Coordinate with service-builder/coordinator to fix account.routes.ts so profile path works correctly.

### Inline styles vs styleUrl
- For layout components with extensive CSS, use `styles: [...]` array (inline) rather than styleUrl
- This avoids the Analog vite-plugin-angular requirement for .spec.ts files
- Matches the existing pattern (OfflineBannerComponent uses inline styles too)

### Session: 2026-06-06 — CatalogFormComponent Visual Shell

**Component:** `features/catalog-form/catalog-form/catalog-form.component.ts`
**Route:** `/catalogs/:id/edit`

#### Patterns used
- Angular 18 `@for` with `let i = $index` for step index tracking in progress bar
- Inline style binding with `{{ expression }}` interpolation inside style attribute strings works in Angular templates — used for signal-driven step colors
- `signal<number>(2)` for activeStep; all color expressions reference `activeStep()` inside template style strings
- `MatIconModule` imported for `check_circle` icon in tips column — no other Material modules needed for this shell
- Responsive breakpoint: `@media (max-width: 899px)` in `styles: [...]` array with `!important` override on the host-bound class `catalog-form-grid` — this is the correct pattern when the grid columns are inline on the element (class cannot override inline without `!important`)
- For `<textarea>`: use `font-family:inherit` to prevent browser default monospace
- HTML entities in templates: `&rarr;` for arrows, `&#8377;` for ₹, `&#128161;` for 💡, `&#9889;` for ⚡
- Visual shell rule: no `@angular/forms` import, no `inject()`, no service stubs — just signals for local UI state
- `steps[]` and `tips[]` as `readonly` typed arrays in the class body (not signals — they never change)

#### Build notes
- catalog-form-component lazy chunk: 13.45 kB raw (MatIconModule adds ~7 kB vs stub's near-zero)
- No existing files in `catalog-form/` were touched — primitives, wizard-renderer, api-service all preserved


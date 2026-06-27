## Session 2026-06-09 — Wave 5 F1 Landing — EXECUTED {#wave5-f1-landing}

### Route touched
`/` — features/landing/landing.component.ts

### Services consumed
None. Fully static public page.

### Pattern: routerLink native anchor for primary CTA (not mee-button + router.navigate)
- Prior stub used `(clicked)="navigateToSignup()"` + `router.navigate(['/signup'])` on mee-button.
- Dispatch spec Gate 4 requires `routerLink="/signup"` attribute on the "Start free" element.
- `mee-button` wraps PrimeNG p-button which renders as `<button>` — cannot carry `routerLink`.
- CORRECT approach: `<a routerLink="/signup" class="btn-primary">Start free →</a>` styled via component CSS.
- CSS-styled anchor requires: `display:inline-flex; align-items:center; justify-content:center; min-height:44px;` + brand colors via CSS vars.
- Nav "Log in": `<a routerLink="/login" class="login-link"><mee-button variant="ghost" size="sm" label="Log in" /></a>` — wraps mee-button in an anchor.
- Removed `Router` injection entirely — no `inject(Router)` needed on a purely static page.

### Pattern: provideRouter([]) replaces RouterTestingModule in specs
- `RouterTestingModule` from `@angular/router/testing` is deprecated in Angular 21.
- CORRECT: `providers: [provideRouter([])]` in `TestBed.configureTestingModule`.
- `provideRouter([])` is sufficient for component tests checking routerLink attributes.

### Pattern: routerLink attribute query in jsdom tests
- After `fixture.detectChanges()`, Angular resolves routerLink — attribute may appear as `ng-reflect-router-link` in jsdom.
- Selector: `'a[routerLink="/signup"], a[ng-reflect-router-link="/signup"]'` — query both forms.
- `firstLink.getAttribute('routerLink') ?? firstLink.getAttribute('ng-reflect-router-link')` — coalesce both attribute names.
- This pattern works reliably across both with-zone and zoneless TestBed setups.

### Pattern: Fully static page — no Router injection needed
- If a page has ZERO programmatic navigation (all nav via routerLink anchors), do NOT inject Router.
- Only `RouterLink` directive (for template) is needed in imports[].
- Removes one service dependency → cleaner component.

### Build result (Wave 5 F1 Landing)
- pnpm run build: ZERO errors, 3.396s
- landing-component lazy chunk: 7.37 kB raw / 1.93 kB transfer (budget ≤80 kB gzip — 97.6% headroom)
- 8/8 landing tests passing (landing.component.spec.ts)
- Total suite: 202 passed / 62 pre-existing failures (unchanged — all in catalog-new/dashboard/profile/shell/onboarding/images/preview/pricing)
- Boundary check: grep features/ for primeng → empty (CLEAN)

---

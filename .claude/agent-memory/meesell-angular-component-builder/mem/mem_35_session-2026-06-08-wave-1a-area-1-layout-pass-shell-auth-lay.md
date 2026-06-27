## Session 2026-06-08 — Wave 1A Area 1 — Layout pass (shell + auth-layout) {#wave-1a-area1}

### Routes touched
Layout shell (all authenticated routes) + auth layout (/, /signup, /login)

### Services consumed
`AuthService` (auth.logout() + auth.userId()) — existing; `Router` (router.navigate()) — existing

### Pattern: MatMenuModule for profile dropdown in shell
- Import `MatMenuModule` from `@angular/material/menu` in the imports[] array.
- Use `mat-mini-fab` with `[matMenuTriggerFor]="profileMenu"` — the trigger attribute comes from MatMenuModule.
- `mat-menu #profileMenu="matMenu"` declared AFTER the trigger button in the template is fine (Angular resolves template refs).
- `xPosition="before"` — opens the menu to the left of the trigger (correct for top-right avatar).
- `aria-haspopup="true"` on the trigger button for WCAG.
- mat-menu handles `role="menuitem"` on its items automatically — no manual role needed.
- Material Symbols Outlined: `fontSet="material-symbols-outlined"` on `<mat-icon>` inside mat-menu-item.

### Pattern: mat-mini-fab sizing override
- `width: 36px !important; height: 36px !important; min-width: 36px !important;` — Material sets min-width on buttons; `!important` is required for override.
- `background: var(--mee-color-primary) !important;` — Material also sets background via its own theming; `!important` bypasses it.
- This is an intentional CSS specificity override — expected and documented.

### Pattern: auth exposure for tests
- `private readonly auth = inject(AuthService)` was changed to `readonly auth = inject(AuthService)` to allow spec tests to spy on `auth.logout`.
- Tests that call `fixture.componentInstance.logout()` directly work because the method calls `this.auth.logout()`.
- For mat-menu tests: inject `OverlayContainer` in `beforeEach` and query `overlayContainer.getContainerElement()` for menu items in the CDK overlay.
- Menu items rendered in overlay use selector `button[mat-menu-item]` — query with `querySelectorAll`.
- Dynamic import of Router in test: `const router = TestBed.inject((await import('@angular/router')).Router)` — avoids circular import at module level when using a dynamic import in async tests.
- `vi.spyOn(router, 'navigate').mockResolvedValue(true)` — Router.navigate returns a Promise<boolean>; mockResolvedValue matches.

### Pattern: Token substitution decisions (Wave 1A Gate 2)
Token-replaced:
- `#F26B23` → `var(--mee-color-primary)` (brand icon, nav-active, user-avatar-fab, auth-brand-logo)
- `#f0f5f9` → `var(--mee-color-bg)` (sidenav-container bg, page-content bg)
- `#ffffff` on top-header → `var(--mee-color-bg-elevated)` (token exists = #ffffff, same value)
- `#e8ecf0` on border-bottom → `var(--mee-color-outline)` (token = #e5eaef, near-identical)
- `rgba(242, 107, 35, 0.12)` → `color-mix(in srgb, var(--mee-color-primary) 12%, transparent)`
- `rgba(242, 107, 35, 0.2)` → `color-mix(in srgb, var(--mee-color-primary) 20%, transparent)`
- `#111827` (auth-brand-name) → `var(--mee-color-on-surface)`
- `16px border-radius` (auth-card) → `var(--mee-radius-md)` (exact match)

Grandfathered (no token):
- `#111c2d` — dark navy sidebar bg (no token; must stay dark for sidebar contrast)
- `#374151` — header toggle btn color (no token)
- `#f3f4f6` — hover bg (no token; near-white hover)
- `#fff` / `rgba(255,255,255,*)` — text on dark sidebar bg (no token for white-on-dark)
- `12px border-radius` (auth-brand-logo) — no token at 12px (--mee-radius-md = 16px, mismatch)
- gradient `#f5f5f5 + #ffe8d6` — auth-specific background gradient (no token)
- `#ffffff` on .auth-card background — task spec says leave as-is

### Pattern: color-mix() for opacity-based primaries without alpha tokens
- Angular Material 18 supports `color-mix()` in all target browsers (Chrome 111+, Safari 16.2+).
- `color-mix(in srgb, var(--mee-color-primary) 12%, transparent)` is equivalent to `rgba(242, 107, 35, 0.12)`.
- This is the correct approach when `--mee-color-primary-light` (= rgba with fixed opacity) does not match the needed opacity exactly.
- Syntax: `color-mix(in srgb, <color> <pct>%, transparent)` — not `<color> / alpha` syntax.

### Build result (2026-06-08 Wave 1A Area 1)
- ng build --configuration=production: ZERO errors, 7.476s
- 11/11 shell component tests passing (6 existing + 5 new); 7 pre-existing export.spec failures unchanged
- 272/279 total tests passing

---

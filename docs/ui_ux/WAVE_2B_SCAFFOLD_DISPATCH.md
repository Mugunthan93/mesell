# WAVE 2B — NEW FRONTEND SCAFFOLD — DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 2B — New Frontend Scaffold |
| **Date authored** | 2026-06-08 |
| **Status** | 📤 READY TO DISPATCH |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | mesell-design-system-2 |
| **Library confirmed** | PrimeNG 21 + Sakai-ng Free (founder ratified 2026-06-08) |
| **Predecessor** | `WAVE_2A_FRAMEWORK_SHORTLIST.md` — Gate A ✅ |
| **Scope** | Scaffold + tokens + 2-layout shell ONLY. No page components. |

---

## 1. Context

Wave 2A confirmed PrimeNG + Sakai-ng Free as the MeeSell frontend library and visual reference. Old frontend archived at `archive/frontend_angular_material/`. New `frontend/` does not yet exist.

Wave 2B creates the new frontend foundation:
- Sakai-ng cloned as READ-ONLY visual reference
- Fresh Angular 21 + PrimeNG 21 + Tailwind 4 scaffold at `frontend/`
- MeeSell design tokens applied via `@primeuix/themes` preset
- 2-layout routing structure (auth-layout + app-shell)

**This wave ends when the scaffold builds, runs, and passes founder visual review.** Page components (dashboard, catalog, profile, etc.) are Wave 2C+ — separate dispatches.

---

## 2. Sequence (3 sub-dispatches in order)

Execute in strict order — each step depends on the previous.

| Step | Agent | Task | Output |
|---|---|---|---|
| **2B-1** | `meesell-infra-builder` | Clone Sakai-ng + scaffold new Angular 21 frontend + install deps + remove primeclt | `themes/sakai-ng/` + `frontend/` with clean build |
| **2B-2** | `meesell-angular-ui-styler` | Configure `@primeuix/themes` preset with MeeSell tokens | Themed frontend — orange primary, dark sidebar, light bg |
| **2B-3** | `meesell-angular-component-builder` | Build auth-layout + app-shell (sidebar + header toolbar) | 2-layout pattern wired to router + passing tests |

---

## 3. Sub-Dispatch 2B-1 — Scaffold (meesell-infra-builder)

### 3.1 Step A — Clone Sakai-ng as visual reference

```bash
cd /Users/mugunthansrinivasan/Project/mesell
git clone https://github.com/primefaces/sakai-ng themes/sakai-ng
```

**Sakai-ng is READ-ONLY.** It is a visual reference only — never import from it into `frontend/`.

Verify after clone:
```bash
cat themes/sakai-ng/package.json | grep -E '"@angular/core"|"primeng"|"tailwindcss"'
```

Expected: `@angular/core ^21`, `primeng ^21`, `tailwindcss ^4`

### 3.2 Step B — Scaffold new Angular 21 frontend

```bash
cd /Users/mugunthansrinivasan/Project/mesell
npx @angular/cli@21 new frontend \
  --standalone \
  --routing \
  --style=css \
  --skip-git \
  --skip-tests=false \
  --package-manager=pnpm
```

### 3.3 Step C — Install PrimeNG + Tailwind + PrimeUI themes

```bash
cd /Users/mugunthansrinivasan/Project/mesell/frontend

pnpm add primeng @primeuix/themes

pnpm add -D tailwindcss @tailwindcss/vite
```

### 3.4 Step D — Remove primeclt (Vue dep accidentally bundled in Sakai-ng ecosystem)

In `frontend/package.json`, ensure `primeclt` is NOT present. If it was auto-added by any peer dep resolution, remove it:

```bash
cd frontend && pnpm remove primeclt 2>/dev/null; echo "primeclt check done"
```

### 3.5 Step E — Wire Tailwind into styles.css

`frontend/src/styles.css`:
```css
@import "tailwindcss";
```

### 3.6 Step F — Verify scaffold builds

```bash
cd /Users/mugunthansrinivasan/Project/mesell/frontend
pnpm run build
```

**Pass criteria**: zero errors. Bundle size not yet relevant (no components yet).

### 3.7 2B-1 completion check

- [ ] `themes/sakai-ng/` exists with Sakai-ng source
- [ ] `frontend/` exists with Angular 21 scaffold
- [ ] `primeng` + `@primeuix/themes` in `frontend/package.json` dependencies
- [ ] `tailwindcss` in `frontend/package.json` devDependencies
- [ ] `primeclt` NOT in `frontend/package.json`
- [ ] `pnpm run build` passes with zero errors

---

## 4. Sub-Dispatch 2B-2 — Design Tokens (meesell-angular-ui-styler)

### 4.1 MeeSell token values

| Token | Value | Usage |
|---|---|---|
| Primary (brand orange) | `#F26B23` | Buttons, active states, links, CTA |
| Primary hover | `#d95e1e` | Darker orange for hover states |
| Background | `#f0f5f9` | Page/app background |
| Background elevated | `#ffffff` | Cards, panels, dialogs |
| Sidebar background | `#111c2d` | Dark navy sidebar |
| Sidebar text | `rgba(255,255,255,0.85)` | Sidebar nav labels |
| Sidebar active | `#F26B23` | Active nav item indicator |
| Border / outline | `#e5eaef` | Input borders, dividers |
| On-surface | `#1e293b` | Primary text |
| On-surface variant | `#64748b` | Secondary text, labels |
| Success | `#22c55e` | Quality pass, positive |
| Error | `#ef4444` | Quality fail, destructive |
| Warning | `#f59e0b` | Quality warn, caution |

### 4.2 Configure @primeuix/themes preset

Create `frontend/src/app/core/theme/meesell-preset.ts`:

```typescript
import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

export const MeeSellPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '#fef3ec',
      100: '#fde3d0',
      200: '#fbc4a0',
      300: '#f8a070',
      400: '#f58248',
      500: '#F26B23',  // MeeSell brand orange
      600: '#d95e1e',
      700: '#b84d17',
      800: '#963d12',
      900: '#6e2c0c',
      950: '#4a1d08',
    },
    colorScheme: {
      light: {
        surface: {
          0:   '#ffffff',
          50:  '#f0f5f9',
          100: '#e2eaf2',
          200: '#c5d5e5',
          300: '#a8c0d8',
          400: '#8babcb',
          500: '#6e96be',
          600: '#5881a8',
          700: '#456a8a',
          800: '#32536c',
          900: '#1e3c4e',
          950: '#111c2d',
        },
        primary: {
          color:           '#F26B23',
          contrastColor:   '#ffffff',
          hoverColor:      '#d95e1e',
          activeColor:     '#b84d17',
        },
        highlight: {
          background:      'rgba(242, 107, 35, 0.12)',
          focusBackground: 'rgba(242, 107, 35, 0.20)',
          color:           '#F26B23',
          focusColor:      '#d95e1e',
        },
      },
    },
  },
  components: {
    button: {
      borderRadius: '7px',
    },
    inputtext: {
      borderRadius: '7px',
    },
    card: {
      borderRadius: '16px',
      shadow: '0 1px 4px rgba(0,0,0,0.08)',
    },
  },
});
```

### 4.3 Wire preset into app.config.ts

`frontend/src/app/app.config.ts`:
```typescript
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { providePrimeNG } from 'primeng/config';
import { MeeSellPreset } from './core/theme/meesell-preset';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideAnimationsAsync(),
    providePrimeNG({
      theme: {
        preset: MeeSellPreset,
        options: {
          darkModeSelector: '.dark-mode',
          cssLayer: {
            name: 'primeng',
            order: 'tailwind-base, primeng, tailwind-utilities',
          },
        },
      },
    }),
  ],
};
```

### 4.4 Tailwind config — extend with MeeSell tokens

`frontend/tailwind.config.js`:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        'mee-primary':          '#F26B23',
        'mee-primary-hover':    '#d95e1e',
        'mee-bg':               '#f0f5f9',
        'mee-bg-elevated':      '#ffffff',
        'mee-sidebar':          '#111c2d',
        'mee-border':           '#e5eaef',
        'mee-on-surface':       '#1e293b',
        'mee-on-surface-muted': '#64748b',
      },
      borderRadius: {
        'mee-sm':   '7px',
        'mee-md':  '16px',
        'mee-lg':  '18px',
        'mee-full': '9999px',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
```

### 4.5 Plus Jakarta Sans font

`frontend/src/index.html` — add in `<head>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### 4.6 2B-2 completion check

- [ ] `frontend/src/app/core/theme/meesell-preset.ts` created
- [ ] `app.config.ts` wires `MeeSellPreset` via `providePrimeNG`
- [ ] `tailwind.config.js` extends with `mee-*` tokens
- [ ] Plus Jakarta Sans font loaded in `index.html`
- [ ] `pnpm run build` still passes with zero errors

---

## 5. Sub-Dispatch 2B-3 — Layouts (meesell-angular-component-builder)

### 5.1 Auth layout component

**Reference**: `themes/sakai-ng/src/app/layout/` (READ-ONLY)

File: `frontend/src/app/layouts/auth/auth-layout.component.ts`

Structure:
```
┌─────────────────────────────────────────────────────┐
│           (centered vertically + horizontally)       │
│   ┌───────────────────────────────────────────┐     │
│   │  MeeSell logo / brand mark                │     │
│   │                                           │     │
│   │  <router-outlet>                          │     │
│   │  (login / signup / otp-verify pages)      │     │
│   │                                           │     │
│   └───────────────────────────────────────────┘     │
│                                                      │
│  background: var(--mee-bg) #f0f5f9                  │
└─────────────────────────────────────────────────────┘
```

Constraints:
- Standalone + OnPush
- No PrimeNG components needed (pure layout shell)
- Min-height: 100vh; center content with Tailwind `flex items-center justify-center`
- Route children: `/login`, `/signup`, `/otp-verify`

### 5.2 App shell component (authenticated)

**Reference**: `themes/sakai-ng/src/app/layout/` (READ-ONLY — AppLayoutComponent + AppSidebarComponent + AppTopbarComponent)

File: `frontend/src/app/layouts/shell/shell.component.ts`

Structure:
```
┌──────────────────────────────────────────────────────────────┐
│  SHELL (full viewport)                                        │
│  ┌──────────────┬────────────────────────────────────────┐  │
│  │  SIDEBAR     │  MAIN CONTENT AREA                      │  │
│  │  270px       │  ┌──────────────────────────────────┐  │  │
│  │  bg:#111c2d  │  │ HEADER TOOLBAR                    │  │  │
│  │              │  │ hamburger  ···  profile avatar    │  │  │
│  │  [MeeSell    │  └──────────────────────────────────┘  │  │
│  │   logo/brand]│  ┌──────────────────────────────────┐  │  │
│  │              │  │ <router-outlet>                   │  │  │
│  │  [NAV LIST]  │  │ (page components)                 │  │  │
│  │  · Dashboard │  │                                   │  │  │
│  │  · New Cat.  │  └──────────────────────────────────┘  │  │
│  │  · My Cats.  │                                         │  │
│  │  · Profile   │                                         │  │
│  └──────────────┴────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
Mobile (<1024px): sidebar collapses to overlay drawer (PrimNG p-drawer or CSS transform)
```

**PrimeNG components to use:**
- `p-drawer` (or custom CSS) — sidebar overlay on mobile
- `p-button` (text variant) — nav items OR `p-panelmenu` for grouped nav
- `p-avatar` — profile avatar in header
- `p-menu` — profile dropdown (My Profile / Log out)

**Nav items** (mirror old architecture):
```typescript
const NAV_ITEMS = [
  { label: 'Dashboard',    icon: 'pi pi-home',    route: '/dashboard' },
  { label: 'New Catalog',  icon: 'pi pi-plus',    route: '/catalogs/new' },
  { label: 'My Catalogs',  icon: 'pi pi-list',    route: '/catalogs' },
  { label: 'Profile',      icon: 'pi pi-user',    route: '/profile' },
];
```

**Profile dropdown** (header, right side):
- "My Profile" → `/profile`
- "Log out" → `AuthService.logout()` → `/login`
- NO notifications bell (Wave 1A ruling preserved)

### 5.3 Routing structure

`frontend/src/app/app.routes.ts`:
```typescript
export const routes: Routes = [
  {
    path: '',
    component: AuthLayoutComponent,
    children: [
      { path: '',      redirectTo: 'login', pathMatch: 'full' },
      { path: 'login',      loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent) },
      { path: 'signup',     loadComponent: () => import('./features/auth/signup/signup.component').then(m => m.SignupComponent) },
      { path: 'otp-verify', loadComponent: () => import('./features/auth/otp-verify/otp-verify.component').then(m => m.OtpVerifyComponent) },
    ],
  },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      { path: 'dashboard', loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent) },
      { path: 'catalogs',  loadComponent: () => import('./features/catalog/catalog-list/catalog-list.component').then(m => m.CatalogListComponent) },
      { path: 'profile',   loadComponent: () => import('./features/profile/profile.component').then(m => m.ProfileComponent) },
    ],
  },
  { path: '**', redirectTo: '/login' },
];
```

**Stub page components** (empty OnPush stubs — just enough to make routes resolve):
Create minimal stubs for: `LoginComponent`, `SignupComponent`, `OtpVerifyComponent`, `DashboardComponent`, `CatalogListComponent`, `ProfileComponent`. Each stub is 8-10 lines: selector + standalone + OnPush + template `<p>Page name placeholder</p>`.

### 5.4 Auth service stub

`frontend/src/app/core/services/auth.service.ts` — minimal stub:
```typescript
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly _token = signal<string | null>(null);
  readonly token = this._token.asReadonly();
  readonly isAuthenticated = computed(() => !!this._token());

  logout(): void {
    this._token.set(null);
  }
}
```

### 5.5 Auth guard

`frontend/src/app/core/guards/auth.guard.ts`:
```typescript
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.isAuthenticated() ? true : router.createUrlTree(['/login']);
};
```

### 5.6 Required tests

`shell.component.spec.ts`:
- Shell renders sidebar with 4 nav items
- Profile avatar present in header
- "Log out" calls `auth.logout()` + navigates to `/login`
- "My Profile" navigates to `/profile`
- Bell (notifications) is absent

`auth-layout.component.spec.ts`:
- Auth layout renders router-outlet
- No sidebar present
- Background is auth-bg class

### 5.7 2B-3 completion check

- [ ] `AuthLayoutComponent` created + routes to login/signup/otp-verify
- [ ] `ShellComponent` created + sidebar (4 nav items) + header (profile avatar + dropdown)
- [ ] Auth service stub + auth guard wired
- [ ] 6 page stubs created (resolve routes without errors)
- [ ] `pnpm run build` passes with zero errors
- [ ] `pnpm vitest run` (or `ng test`) — all tests pass

---

## 6. Verification Gates (post all 3 sub-dispatches)

### Gate 1 — BUILD
```bash
cd frontend && pnpm run build
```
**Pass**: zero errors, zero new warnings.

### Gate 2 — DEV SERVER
```bash
cd frontend && pnpm run start
```
Verify:
- `http://localhost:4200/` redirects to `/login` (auth layout, no sidebar)
- `http://localhost:4200/dashboard` redirects to `/login` (auth guard fires)
- Auth layout has white/grey background (no dark sidebar)

### Gate 3 — TOKEN SPOT CHECK
Open browser devtools → Inspect any button element:
- Primary button background should be `#F26B23` (MeeSell orange) — NOT default PrimeNG blue
- Page background should be `#f0f5f9`
- Font should be Plus Jakarta Sans

### Gate 4 — FUNCTIONAL
```bash
cd frontend && pnpm run test
```
**Pass**: all shell + auth-layout tests passing.

### Gate 5 — VISUAL (founder review)
Founder visits `http://localhost:4200/login` and `http://localhost:4200/dashboard` (after manually setting auth signal to true in browser devtools).
**Pass**: founder verbal approval.

### 6.1 Gate tracking

| Gate | Status | Owner |
|---|---|---|
| 1 BUILD | ⏳ pending | design-system-2 |
| 2 DEV SERVER | ⏳ pending | design-system-2 |
| 3 TOKEN SPOT CHECK | ⏳ pending | design-system-2 |
| 4 FUNCTIONAL | ⏳ pending | design-system-2 |
| 5 VISUAL | ⏳ pending founder | Founder |

---

## 7. Constraints (non-negotiable)

| Constraint | Rule |
|---|---|
| **Standalone + OnPush** | All components: `standalone: true`, `ChangeDetectionStrategy.OnPush` |
| **Signals** | Use Angular signals (`signal()`, `computed()`) for reactive state — no BehaviorSubject for local state |
| **No NgModules** | Router config via `provideRouter(routes)` in `app.config.ts` |
| **MeeSell tokens only** | All colours from `meesell-preset.ts` or `tailwind.config.js` `mee-*` tokens — no hardcoded hex |
| **PrimeIcons** | Use `pi pi-*` icons in this phase — PrimeNG's native icon set. Material Symbols migration deferred to Wave 2D |
| **Mobile 360px baseline** | Sidebar collapses to drawer/overlay at `<1024px` |
| **FE-D5 preserved** | Auth token in-memory only (`signal<string | null>`) — no localStorage/sessionStorage/cookie |
| **No page logic** | Stubs only for page components — no API calls, no form logic in Wave 2B |
| **primeclt absent** | Verify not in package.json after scaffold |
| **Only `meesell-*` agents** | Per CLAUDE.md rules |

---

## 8. Out of Scope

| Item | Wave |
|---|---|
| Page component implementation (login form, dashboard widgets, catalog form) | Wave 2C+ |
| API integration | Held until UI/UX confirmed |
| OTP flow wiring | Wave 2C auth |
| FRONTEND_ARCHITECTURE.md pruning | Separate dispatch (parallel) |
| Mobile-specific overrides beyond 360px collapse | Wave 2C+ |
| i18n / Tamil / Hindi | V1.5 |
| Module Federation | Phase 2 |
| Dark mode | Post-V1 |

---

## 9. Dispatch Notification (paste-ready block)

```
══════════════════════════════════════════════════════════════════
📨 MASTER → DESIGN-SYSTEM NOTIFICATION
Date: 2026-06-08
From: meesell-frontend-coordinator (master session)
Wave: WAVE 2B — NEW FRONTEND SCAFFOLD
Type: Scaffold + design tokens + 2-layout shell
══════════════════════════════════════════════════════════════════

CONFIRMED DECISION (founder 2026-06-08)
────────────────────────────────────────
Library:    PrimeNG 21 + @primeuix/themes (Aura base)
Reference:  Sakai-ng Free (READ-ONLY visual reference)
Tailwind:   v4
Angular:    21
Archive:    frontend_angular_material → archive/ (done)

══════════════════════════════════════════════════════════════════

YOUR JOB — 3 SUB-DISPATCHES IN ORDER
──────────────────────────────────────

STEP 2B-1 → meesell-infra-builder
  1. Clone Sakai-ng to themes/sakai-ng/ (read-only reference)
     git clone https://github.com/primefaces/sakai-ng themes/sakai-ng
  2. Scaffold new Angular 21 frontend:
     npx @angular/cli@21 new frontend --standalone --routing
       --style=css --skip-git --package-manager=pnpm
  3. Install PrimeNG + @primeuix/themes:
     cd frontend && pnpm add primeng @primeuix/themes
  4. Install Tailwind 4:
     pnpm add -D tailwindcss @tailwindcss/vite
  5. Remove primeclt (Vue dep — must not be present):
     pnpm remove primeclt 2>/dev/null
  6. Wire Tailwind in styles.css:
     @import "tailwindcss";
  7. Verify: pnpm run build → zero errors

STEP 2B-2 → meesell-angular-ui-styler
  Full spec: WAVE_2B_SCAFFOLD_DISPATCH.md §4
  1. Create frontend/src/app/core/theme/meesell-preset.ts
     (definePreset over Aura — #F26B23 primary palette)
  2. Wire MeeSellPreset into app.config.ts via providePrimeNG
  3. Extend tailwind.config.js with mee-* color/radius tokens
  4. Add Plus Jakarta Sans font in index.html
  5. Verify: pnpm run build → zero errors

STEP 2B-3 → meesell-angular-component-builder
  Full spec: WAVE_2B_SCAFFOLD_DISPATCH.md §5
  1. AuthLayoutComponent (centered, no sidebar, bg:#f0f5f9)
     Routes: /login + /signup + /otp-verify (stub pages)
  2. ShellComponent (sidebar #111c2d + header toolbar)
     Sidebar nav: Dashboard / New Catalog / My Catalogs / Profile
     Header: profile avatar → p-menu dropdown (My Profile + Log out)
     NO bell / NO notifications
  3. Auth guard (blocks unauthenticated /dashboard access)
  4. Auth service stub (signal-based, in-memory token, FE-D5)
  5. 6 page stubs (empty OnPush, just enough for routes to resolve)
  6. Tests: shell (5 tests) + auth-layout (2 tests)
  7. Verify: pnpm run build + pnpm test → zero errors + all pass

══════════════════════════════════════════════════════════════════

VERIFICATION GATES (all 5 before notifying master)
───────────────────────────────────────────────────
Gate 1 BUILD:        pnpm run build → zero errors
Gate 2 DEV SERVER:   / redirects to /login (no sidebar)
                     /dashboard redirects to /login (auth guard)
Gate 3 TOKEN:        Primary button = #F26B23 (not default blue)
                     Background = #f0f5f9
                     Font = Plus Jakarta Sans
Gate 4 FUNCTIONAL:   All shell + auth-layout tests passing
Gate 5 VISUAL:       ⏳ founder review after Gates 1-4 pass

══════════════════════════════════════════════════════════════════

CONSTRAINTS
───────────────────────────────────────────────────
• Standalone + OnPush + signals — all components
• No NgModules — provideRouter in app.config.ts
• MeeSell tokens only — no hardcoded hex
• PrimeIcons (pi pi-*) for now (Material Symbols = Wave 2D)
• Sidebar collapses to overlay at <1024px
• FE-D5: auth token in-memory signal only
• Stubs only for pages — no API calls, no form logic
• primeclt absent from package.json
• Only meesell-* agents

NOT IN SCOPE:
✗ Page component implementation
✗ API integration (on hold)
✗ OTP wiring
✗ FRONTEND_ARCHITECTURE.md pruning (separate)
✗ Dark mode, i18n, Module Federation

══════════════════════════════════════════════════════════════════

STATUS UPDATE (append to STATUS_DESIGN_SYSTEM.md)
───────────────────────────────────────────────────
  ═════════════════════════════════════════════════
  UPDATE 2026-06-08 — WAVE 2B SCAFFOLD
  ═════════════════════════════════════════════════
  Library confirmed: PrimeNG 21 + Sakai-ng Free (MIT)
  Archive: frontend_angular_material + themes → archive/
  Sub-dispatch 2B-1 (infra-builder):  ⏳/✅/❌
  Sub-dispatch 2B-2 (ui-styler):      ⏳/✅/❌
  Sub-dispatch 2B-3 (component-builder): ⏳/✅/❌
  Gate 1 BUILD:     ⏳
  Gate 2 DEV SERVER: ⏳
  Gate 3 TOKEN:      ⏳
  Gate 4 FUNCTIONAL: ⏳
  Gate 5 VISUAL:     ⏳ pending founder
  Open questions: [any blockers for master]

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```

---

## 10. Related Documents

| Document | Relevance |
|---|---|
| `docs/ui_ux/WAVE_2A_FRAMEWORK_SHORTLIST.md` | Framework selection evidence |
| `archive/frontend_angular_material/` | Old codebase (reference for porting business logic later) |
| `archive/themes/sakai-ng/` | NOT the reference — `themes/sakai-ng/` (new clone) is |
| `docs/FRONTEND_ARCHITECTURE.md` | Will be pruned in parallel — stable enough to reference for routing/API contract patterns |
| `docs/status/STATUS_DESIGN_SYSTEM.md` | Receives UPDATE block |

---

## 11. What Comes After Wave 2B

| Wave | Owner | Trigger |
|---|---|---|
| **2C — Auth pages** (login/signup/otp-verify with PrimeNG forms) | `mesell-ui-auth-*` sub-session | After Gate 5 ✅ |
| **2D — Dashboard page** | `mesell-ui-dashboard-*` sub-session | After 2C ✅ |
| **2E — Catalog pages** | `mesell-ui-catalog-*` sub-session | After 2D ✅ |
| **FRONTEND_ARCHITECTURE.md prune** | `meesell-angular-ui-styler` dispatch | Parallel to 2B |

---

## 12. Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-08 | meesell-frontend-coordinator (master) | Initial authoring — PrimeNG confirmed by founder |

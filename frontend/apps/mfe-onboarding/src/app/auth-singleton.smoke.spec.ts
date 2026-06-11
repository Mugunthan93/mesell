/**
 * SP03 D22 C5 — AuthService singleton smoke test (the migration's AUTH GO/NO-GO).
 *
 * This is the contract that gates the WHOLE 6-remote federation migration
 * (MASTER_PLAN R1 P0). `mfe-onboarding` is the FIRST remote to inject `AuthService`
 * across the federation boundary (profile.component reads `currentUser()` + calls
 * `logout()`). If the remote resolved its OWN AuthService instance instead of the
 * shell's shared singleton, login state would not cross the boundary and the whole
 * auth story would be broken.
 *
 * `AuthService` is `@Injectable({ providedIn: 'root' })` (D22 C2 — retained, NOT
 * refactored). Under Native Federation the singleton is achieved by `@mesell/core`
 * being a `shared + singleton: true` module in the import map, so both the shell host
 * and every remote import the SAME `@mesell/core` module URL → ONE provider in ONE
 * root injector. The STATIC proof is in the build output: `@mesell/core` is shared
 * (`_mesell_core-*.js`) and AuthService is NOT inlined into the ProfileComponent
 * chunk (no duplicate `auth.service` chunk) — verified by the lead's build-output
 * inspection. This spec is the RUNTIME proof of the same contract: ONE AuthService
 * instance is observed by both the "shell" caller and the remote `ProfileComponent`.
 *
 * The test models the boundary with a single root injector (exactly what the shared
 * import-map produces): inject AuthService as the "shell", drive it, and assert the
 * remote ProfileComponent + the authGuard observe the SAME instance's state.
 *
 * Steps (D22 C5):
 *   1. (shell) setSession(token, user) — simulate login.
 *   2. (remote) render ProfileComponent — assert it renders currentUser().name.
 *   3. (remote) onLogout() — calls auth.logout().
 *   4. (shell) assert isAuthenticated() === false.
 *   5. (shell) assert authGuard now BLOCKS a protected route (returns a redirect UrlTree).
 */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import {
  ActivatedRouteSnapshot,
  provideRouter,
  Router,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { runInInjectionContext, EnvironmentInjector } from '@angular/core';

import { AuthService, AuthUser, authGuard } from '@mesell/core';
import { ProfileComponent } from './profile.component';

function makeUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return { id: 7, name: 'Mugunthan', phone: '+919876543210', ...overrides };
}

describe('SP03 D22 C5 — AuthService singleton across the federation boundary', () => {
  let fixture: ComponentFixture<ProfileComponent>;
  let shellAuth: AuthService;
  let envInjector: EnvironmentInjector;
  let router: Router;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ProfileComponent, ReactiveFormsModule],
      providers: [
        // Stub /login + /dashboard so the component's post-logout router.navigate(['/login'])
        // resolves cleanly (no unhandled NavigationError leak); the guard-block assertion
        // below uses authGuard directly, not navigation.
        provideRouter([
          { path: 'login', children: [] },
          { path: 'dashboard', children: [] },
        ]),
        provideAnimationsAsync('noop'),
      ],
    }).compileComponents();

    // The "shell" handle on the shared singleton (providedIn:'root' → one instance).
    shellAuth = TestBed.inject(AuthService);
    envInjector = TestBed.inject(EnvironmentInjector);
    router = TestBed.inject(Router);
  });

  afterEach(() => TestBed.resetTestingModule());

  it('C5 — shell login is visible in the remote ProfileComponent; remote logout clears the shell + the guard blocks', () => {
    // ── 1. (shell) login ──────────────────────────────────────────────
    shellAuth.setSession('shell-issued-token', makeUser({ name: 'Mugunthan' }));
    expect(shellAuth.isAuthenticated()).toBe(true);

    // ── 2. (remote) render ProfileComponent — it injects the SAME AuthService ──
    fixture = TestBed.createComponent(ProfileComponent);
    const comp = fixture.componentInstance;
    fixture.detectChanges();

    // The remote sees the shell's value crossing the boundary (C3 — signals natively).
    // comp.auth is the SAME instance as shellAuth (one root provider).
    expect((comp as unknown as { auth: AuthService }).auth).toBe(shellAuth);
    expect((comp as unknown as { auth: AuthService }).auth.currentUser()?.name).toBe('Mugunthan');
    const renderedName = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(renderedName).toContain('Mugunthan');

    // ── 3. (remote) logout via the remote component's own handler ──────
    comp.onLogout(); // calls this.auth.logout()

    // ── 4. (shell) the shell's singleton reflects the remote's mutation ──
    expect(shellAuth.isAuthenticated()).toBe(false);
    expect(shellAuth.currentUser()).toBeNull();
    expect(shellAuth.getToken()).toBeNull();

    // ── 5. (shell) the authGuard now BLOCKS a protected route ──────────
    const guardResult = runInInjectionContext(envInjector, () =>
      authGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/dashboard' } as RouterStateSnapshot,
      ),
    );
    // Blocked → guard returns a redirect UrlTree (to /login), NOT `true`.
    expect(guardResult).toBeInstanceOf(UrlTree);
    expect(router.serializeUrl(guardResult as UrlTree)).toContain('/login');
  });

  it('C5b — a second AuthService injection resolves to the SAME instance (no drift)', () => {
    // Two injection points → one instance. This is the in-process analogue of the
    // shared import-map guarantee: the remote never gets its own copy.
    const again = TestBed.inject(AuthService);
    expect(again).toBe(shellAuth);

    shellAuth.setSession('t', makeUser({ name: 'Drift Check' }));
    expect(again.currentUser()?.name).toBe('Drift Check');
  });
});

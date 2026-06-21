/**
 * auth.guard.spec.ts — QA Wave 1
 *
 * Tests authGuard (CanActivateFn):
 *   - returns true when AuthService.isAuthenticated() is true (token present)
 *   - returns a UrlTree for /login when AuthService.isAuthenticated() is false (token null)
 *
 * Uses TestBed + Router to exercise the guard through the Angular DI / router pipeline.
 * AuthService is provided via a spy so no real HTTP or session state leaks between tests.
 */

import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { provideRouter } from '@angular/router';
import { computed, signal } from '@angular/core';

import { AuthService } from '../services/auth.service';
import { authGuard } from './auth.guard';

// ── helpers ───────────────────────────────────────────────────────────────────

function makeAuthMock(authenticated: boolean) {
  const _auth = signal(authenticated);
  return {
    isAuthenticated: computed(() => _auth()),
    getToken: () => (authenticated ? 'tok' : null),
  } as Pick<AuthService, 'isAuthenticated' | 'getToken'>;
}

function setup(authenticated: boolean) {
  TestBed.configureTestingModule({
    providers: [
      provideRouter([
        { path: 'login', children: [] },
        { path: 'dashboard', canActivate: [authGuard], children: [] },
      ]),
      { provide: AuthService, useValue: makeAuthMock(authenticated) },
    ],
  });
  return {
    router: TestBed.inject(Router),
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('authGuard — token present (authenticated)', () => {
  it('should return true when isAuthenticated() is true', () => {
    setup(true);

    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as never, {} as never),
    );

    expect(result).toBe(true);
  });
});

describe('authGuard — token null (unauthenticated)', () => {
  it('should return a UrlTree for /login when isAuthenticated() is false', () => {
    setup(false);

    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as never, {} as never),
    );

    expect(result).toBeInstanceOf(UrlTree);
    const tree = result as UrlTree;
    // The UrlTree's primary segment group key should encode '/login'
    expect(tree.toString()).toContain('login');
  });

  it('should NOT return true when unauthenticated', () => {
    setup(false);

    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as never, {} as never),
    );

    expect(result).not.toBe(true);
  });
});

const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// MF Sub-Plan 03 — remote `mfe-onboarding` (F5 onboarding + F13 profile,
// routes /onboarding + /profile). FIRST multi-expose remote (D20): ONE remoteEntry.json
// exposing TWO components. FIRST remote to consume AuthService across the federation
// boundary — profile.component injects @mesell/core AuthService (currentUser/logout).
//
// @mesell/core (the AuthService singleton) MUST resolve to the SHELL's single instance:
// shareAll({ singleton: true }) puts @mesell/core in the import map as ONE shared module,
// so the remote's inject(AuthService) returns the shell's instance (D22 C1/C2 — the
// singleton holds via import-map sharing, NOT a decorator refactor). @mesell/core is
// NOT skipped. @mesell/ui-kit, @mesell/composites (incl. the promoted AuthLayout),
// @angular/*, rxjs resolve to the shell's instances too (MASTER_PLAN §6.1).
module.exports = withNativeFederation({
  name: 'mfe-onboarding',

  exposes: {
    './OnboardingComponent': './apps/mfe-onboarding/src/app/onboarding.component.ts',
    './ProfileComponent': './apps/mfe-onboarding/src/app/profile.component.ts',
  },

  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
  },

  skip: [
    'rxjs/ajax',
    'rxjs/fetch',
    'rxjs/testing',
    'rxjs/webSocket',
  ],

  features: {
    ignoreUnusedDeps: true,
  },
});

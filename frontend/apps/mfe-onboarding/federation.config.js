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
    // F-001: @primeuix/themes is imported via subpath (/aura) inside libs/ui-kit/theme.ts.
    // Subpaths are NOT registered in the import map (only root keys are), so any consumer
    // that loads the shared kit chunk would fail to resolve '@primeuix/themes/aura' at runtime.
    // Unsharing bundles Aura directly into the _mesell_ui_kit.js shared chunk — no import-map lookup.
    '@primeuix/themes', // F-001
    '@primeuix/themes/aura', // F-001 guard
  ],

  features: {
    ignoreUnusedDeps: true,
  },
});

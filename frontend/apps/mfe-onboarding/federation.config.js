const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// VERSION-PIN (fix/federation-shared-version-pin): see shell/federation.config.js for full comment.
const MESELL_SHARED_VERSION = '1.0.0';

const mesellShared = {
  '@mesell/core':      { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/env':       { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/ui-kit':    { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/composites': { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
};

// MF Sub-Plan 03 — remote `mfe-onboarding` (F5 onboarding + F13 profile,
// routes /onboarding + /profile). FIRST multi-expose remote (D20): ONE remoteEntry.json
// exposing TWO components. FIRST remote to consume AuthService across the federation
// boundary — profile.component injects @mesell/core AuthService (currentUser/logout).
//
// @mesell/core (the AuthService singleton) MUST resolve to the SHELL's single instance.
// Explicit version pin (1.0.0) + strictVersion:true ensures NF dedup by version key
// regardless of chunk-hash divergence (fix/federation-shared-version-pin).
module.exports = withNativeFederation({
  name: 'mfe-onboarding',

  exposes: {
    './OnboardingComponent': './apps/mfe-onboarding/src/app/onboarding.component.ts',
    './ProfileComponent': './apps/mfe-onboarding/src/app/profile.component.ts',
  },

  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
    ...mesellShared,
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

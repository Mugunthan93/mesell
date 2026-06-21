const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// VERSION-PIN (fix/federation-shared-version-pin): see shell/federation.config.js for full comment.
const MESELL_SHARED_VERSION = '1.0.0';

const mesellShared = {
  '@mesell/core':      { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/env':       { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/ui-kit':    { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/composites': { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
};

// MF Sub-Plan 06 — remote `mfe-auth` (F2 login + F3 signup + F4 otp-verify; routes
// /login + /signup + /otp-verify, all PUBLIC pre-auth). The SIXTH and FINAL extraction
// and the most shell-connected remote: otp-verify is the ONLY flow that WRITES the shell's
// auth.token() via setSession (the C4 WRITE path, D38). Extracted last so 5 reference
// implementations + the proven D22 C1–C5 contract de-risk it.
//
// R-SP3-1 (P0): @mesell/core (AuthService) is consumed by otp-verify.component — its
// setSession() WRITE depends on resolving the SHELL's single AuthService instance via the
// import map. Explicit version pin (1.0.0) + strictVersion:true guarantees NF dedup
// by version key so otp-verify always writes to the shell's AuthService (D38 C4).
module.exports = withNativeFederation({
  name: 'mfe-auth',

  exposes: {
    './LoginComponent': './apps/mfe-auth/src/app/login.component.ts',
    './SignupComponent': './apps/mfe-auth/src/app/signup.component.ts',
    './OtpVerifyComponent': './apps/mfe-auth/src/app/otp-verify.component.ts',
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
    // mappingVersion: true — see shell/federation.config.js for rationale.
    mappingVersion: true,
  },
});

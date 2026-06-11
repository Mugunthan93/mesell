const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// MF Sub-Plan 06 — remote `mfe-auth` (F2 login + F3 signup + F4 otp-verify; routes
// /login + /signup + /otp-verify, all PUBLIC pre-auth). The SIXTH and FINAL extraction
// and the most shell-connected remote: otp-verify is the ONLY flow that WRITES the shell's
// auth.token() via setSession (the C4 WRITE path, D38). Extracted last so 5 reference
// implementations + the proven D22 C1–C5 contract de-risk it.
//
// R-SP3-1 (P0): @mesell/core (AuthService) is consumed by otp-verify.component — its
// setSession() WRITE depends on resolving the SHELL's single AuthService instance via the
// import map. main.ts MUST route to OtpVerifyComponent (the core consumer) so the Sheriff
// import-graph analysis (ignoreUnusedDeps) keeps @mesell/core shared+singleton and does NOT
// inline it into the otp chunk (which would be the P0 drift, MASTER_PLAN R1). shareAll +
// main.ts-routes-to-all-3 = uniform shared set; @mesell/ui-kit, @mesell/composites,
// @mesell/core, @angular/*, rxjs all resolve to the shell's instances (MASTER_PLAN §6.1).
module.exports = withNativeFederation({
  name: 'mfe-auth',

  exposes: {
    './LoginComponent': './apps/mfe-auth/src/app/login.component.ts',
    './SignupComponent': './apps/mfe-auth/src/app/signup.component.ts',
    './OtpVerifyComponent': './apps/mfe-auth/src/app/otp-verify.component.ts',
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

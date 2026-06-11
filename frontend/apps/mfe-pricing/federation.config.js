const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// MF Sub-Plan 01 — PILOT remote `mfe-pricing` (F11 pricing, route /catalogs/:id/pricing).
// kind: 'remote' — produces remoteEntry.json + ESM chunks, mounted by the shell host.
// Exposes a SINGLE component (D10) — pricing is a leaf page with no sub-routes.
// @mesell/core (auth singleton), @mesell/ui-kit, @mesell/composites, @angular/*, rxjs
// resolve to the SHELL's single instances via shareAll singleton:true (MASTER_PLAN §6.1).
// Even though pricing does not use AuthService, the shared contract is uniform (D11/§9.A-3).
module.exports = withNativeFederation({
  name: 'mfe-pricing',

  exposes: {
    './PricingComponent': './apps/mfe-pricing/src/app/pricing.component.ts',
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

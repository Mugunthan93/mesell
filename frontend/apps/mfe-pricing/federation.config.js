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

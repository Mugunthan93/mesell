const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// MF Sub-Plan 05 — remote `mfe-catalog` (R4): the 5-page catalog funnel
// (F7 smart-picker, F8 catalog-form, F9 images, F10 preview, + catalogs list).
// kind: 'remote' — produces remoteEntry.json + ESM chunks, mounted by the shell host.
// Exposes a Routes ARRAY (D31) — the FIRST non-component expose — because catalog
// owns a connected :id-threaded flow (MASTER_PLAN §2.4).
// @mesell/core (auth singleton — carries the promoted Product/Catalog after D33),
// @mesell/ui-kit, @mesell/composites, @angular/*, rxjs resolve to the SHELL's single
// instances via shareAll singleton:true (MASTER_PLAN §6.1).
module.exports = withNativeFederation({
  name: 'mfe-catalog',

  exposes: {
    './CatalogRoutes': './apps/mfe-catalog/src/app/catalog.routes.ts',
  },

  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
  },

  skip: [
    'rxjs/ajax',
    'rxjs/fetch',
    'rxjs/testing',
    'rxjs/webSocket',
    '@primeuix/themes', // F-001
    '@primeuix/themes/aura', // F-001 guard
  ],

  features: {
    ignoreUnusedDeps: true,
  },
});

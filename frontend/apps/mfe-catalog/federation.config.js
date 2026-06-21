const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// VERSION-PIN (fix/federation-shared-version-pin): see shell/federation.config.js for full comment.
const MESELL_SHARED_VERSION = '1.0.0';

const mesellShared = {
  '@mesell/core':      { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/env':       { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/ui-kit':    { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/composites': { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
};

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
    './CatalogRoutes':   './apps/mfe-catalog/src/app/catalog.routes.ts',
    // B04 — /categories/browse browse page; mounted via loadRemoteWithFallback in shell app.routes.ts:89
    './BrowseComponent': './apps/mfe-catalog/src/app/categories/browse/browse.component.ts',
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

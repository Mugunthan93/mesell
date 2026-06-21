const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// VERSION-PIN (fix/federation-shared-version-pin):
// @mesell/* workspace libs had no package.json → version="" in every remoteEntry.json.
// With empty version, Native Federation cannot dedup by version key → each remote loaded
// its own @mesell/core instance (different chunk hash) → AuthService token=null → logout.
// Fix: explicit shared overrides with version:'1.0.0' + singleton:true + strictVersion:true
// on ALL @mesell/* libs across ALL 7 federation configs. Matching libs/*/package.json files
// were also added (same version) so requiredVersion:'auto' resolves correctly in future builds.

const MESELL_SHARED_VERSION = '1.0.0';

const mesellShared = {
  '@mesell/core':      { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/env':       { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/ui-kit':    { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/composites': { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
};

// Sub-Plan 0 — Workspace Foundation. HOST (dynamic-host), ZERO remotes wired (D7).
// Remotes are loaded at runtime from public/federation.manifest.json (currently {}).
// Sub-Plan 1 adds the first remote (mfe-pricing pilot) to the manifest.
// @mesell/core (AuthService) is THE federation auth singleton per MASTER_PLAN §6.1 —
// it is picked up by shareAll() below and resolves to the shell's instance once a
// remote crosses the boundary in Sub-Plan 1.
module.exports = withNativeFederation({
  name: 'shell',

  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
    // Explicit version-pinned overrides MUST come AFTER shareAll so they win:
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
    // Add further packages you don't need at runtime
    // F-001: @primeuix/themes is imported via subpath (/aura) inside libs/ui-kit/theme.ts.
    // Subpaths are NOT registered in the import map (only root keys are), so any consumer
    // that loads the shared kit chunk would fail to resolve '@primeuix/themes/aura' at runtime.
    // Unsharing bundles Aura directly into the _mesell_ui_kit.js shared chunk — no import-map lookup.
    '@primeuix/themes', // F-001
    '@primeuix/themes/aura', // F-001 guard
  ],

  // Please read our FAQ about sharing libs:
  // https://shorturl.at/jmzH0

  features: {
    // New feature for more performance and avoiding
    // issues with node libs. Comment this out to
    // get the traditional behavior:
    ignoreUnusedDeps: true,
    // mappingVersion: true — makes NF emit the version field for tsconfig-path shared mappings
    // (@mesell/* libs). Without this, version='' for ALL workspace libs → NF cannot dedup by
    // version key → each remote loads its own @mesell/core → AuthService token=null → logout.
    // Version is read from libs/*/package.json (added as part of fix/federation-shared-version-pin).
    mappingVersion: true,
  },
});

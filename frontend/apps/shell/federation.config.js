const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

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
  ],

  // Please read our FAQ about sharing libs:
  // https://shorturl.at/jmzH0

  features: {
    // New feature for more performance and avoiding
    // issues with node libs. Comment this out to
    // get the traditional behavior:
    ignoreUnusedDeps: true,
  },
});

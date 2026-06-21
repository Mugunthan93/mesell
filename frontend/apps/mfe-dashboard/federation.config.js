const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// VERSION-PIN (fix/federation-shared-version-pin): see shell/federation.config.js for full comment.
const MESELL_SHARED_VERSION = '1.0.0';

const mesellShared = {
  '@mesell/core':      { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/env':       { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/ui-kit':    { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
  '@mesell/composites': { singleton: true, strictVersion: true, requiredVersion: MESELL_SHARED_VERSION, version: MESELL_SHARED_VERSION },
};

// MF Sub-Plan 04 — remote `mfe-dashboard` (F1 landing + F6 dashboard,
// routes / [public] + /dashboard [authenticated]). The FOURTH extraction and the
// FIRST remote to federate a PUBLIC pre-auth route. Exposes TWO components living on
// OPPOSITE sides of the shell's authGuard (D26): LandingComponent (public) and
// DashboardComponent (shell-guarded).
module.exports = withNativeFederation({
  name: 'mfe-dashboard',

  exposes: {
    './LandingComponent': './apps/mfe-dashboard/src/app/landing.component.ts',
    './DashboardComponent': './apps/mfe-dashboard/src/app/dashboard.component.ts',
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

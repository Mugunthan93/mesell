const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');
const { mesellShared } = require('../../libs/federation/shared.config');

// Wave 5 — new 7th remote `mfe-billing` (D-FE1 — new remote for billing vertical).
// kind: 'remote' — produces remoteEntry.json + ESM chunks, mounted by the shell host.
// Exposes a Routes ARRAY (D31 precedent from mfe-catalog) — billing owns /billing/plans
// and /billing/account: a connected sub-tree (MASTER_PLAN §2.4 Routes-expose justification).
// @mesell/core (auth singleton — carries AuthUser.entitlement after Wave 3 widening),
// @mesell/ui-kit, @mesell/composites, @angular/*, rxjs resolve to the SHELL's single
// instances via shareAll singleton:true (MASTER_PLAN §6.1).
// NOTE: any change to @mesell/core (e.g. Wave 3 AuthUser widening) requires a full-fleet
// remote rebuild for singleton consistency (see finding-federation-auth-singleton-not-shared).
module.exports = withNativeFederation({
  name: 'mfe-billing',

  exposes: {
    './BillingRoutes': './apps/mfe-billing/src/app/public-api.ts',
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

const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// MF Sub-Plan 04 — remote `mfe-dashboard` (F1 landing + F6 dashboard,
// routes / [public] + /dashboard [authenticated]). The FOURTH extraction and the
// FIRST remote to federate a PUBLIC pre-auth route. Exposes TWO components living on
// OPPOSITE sides of the shell's authGuard (D26): LandingComponent (public) and
// DashboardComponent (shell-guarded).
//
// R-SP3-1 (P0): neither page injects AuthService, so @mesell/core is not strictly
// required by the import graph. It is kept in the shared/singleton set for contract
// uniformity (D22 C1) via shareAll. ignoreUnusedDeps may still prune it from this
// remote's remoteEntry shared[] (correct — same as mfe-pricing/mfe-export, which also
// omit @mesell/core). That is NOT drift: drift only matters for a lib a remote DOES
// consume. @mesell/ui-kit, @mesell/composites, @angular/*, rxjs resolve to the shell's
// instances (MASTER_PLAN §6.1).
module.exports = withNativeFederation({
  name: 'mfe-dashboard',

  exposes: {
    './LandingComponent': './apps/mfe-dashboard/src/app/landing.component.ts',
    './DashboardComponent': './apps/mfe-dashboard/src/app/dashboard.component.ts',
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

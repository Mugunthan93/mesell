const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// MF Sub-Plan 02 — remote `mfe-export` (F12 export, route /catalogs/:id/export).
// kind: 'remote' — produces remoteEntry.json + ESM chunks, mounted by the shell host.
// Exposes a SINGLE component (D16) — export is a leaf page with no sub-routes.
// @mesell/core (auth singleton), @mesell/ui-kit, @mesell/composites, @angular/*, rxjs
// resolve to the SHELL's single instances via shareAll singleton:true (MASTER_PLAN §6.1).
// Export does not use AuthService; @mesell/core is omitted from remoteEntry shared[] by
// ignoreUnusedDeps:true — CORRECT (D17 / SP01 recipe), the shared contract stays uniform.
// Token-for-token copy of mfe-pricing's config (D15) — only `name` + `exposes` differ.
module.exports = withNativeFederation({
  name: 'mfe-export',

  exposes: {
    './ExportComponent': './apps/mfe-export/src/app/export.component.ts',
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

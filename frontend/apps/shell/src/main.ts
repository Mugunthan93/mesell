import { initFederation } from '@angular-architects/native-federation';

/**
 * Federation manifest (2026-07-03 fix — F-001 class regression on GitHub Pages).
 *
 * main.ts MUST NOT statically import any federated/shared package (e.g. @mesell/env):
 * shared packages resolve through the import map that initFederation() itself installs,
 * so a static import here is a chicken-and-egg — es-module-shims throws
 * "Unable to resolve specifier '@mesell/env' imported from main-*.js" and the app
 * never boots (blank screen, observed live on Pages 2026-07-03).
 *
 * Environment selection therefore happens via DATA, not code:
 *   - DEV: apps/shell/public/federation.manifest.json (localhost ng-serve ports)
 *     is copied into dist and fetched relative to <base href>.
 *   - PROD (GitHub Pages): the deploy-frontend.yml assemble step OVERWRITES
 *     federation.manifest.json in the publish dir with the /mesell/remotes/<name>/
 *     absolute URLs. Same fetch path, different payload.
 */
initFederation('federation.manifest.json')
  .catch((err) => console.error(err))
  .then((_) => import('./bootstrap'))
  .catch((err) => console.error(err));

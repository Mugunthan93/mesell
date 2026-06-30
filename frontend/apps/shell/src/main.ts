import { initFederation } from '@angular-architects/native-federation';
import { environment } from '@mesell/env';

/**
 * Federation manifest selection (2026-06-30 platform pivot).
 *
 * DEV: load the static localhost manifest (apps/shell/public/federation.manifest.json),
 *   served at <base>/federation.manifest.json — remotes are local `ng serve` ports.
 *   That file is intentionally LEFT UNCHANGED so the localhost dev stack keeps working.
 * PROD (GitHub Pages): the FE ships under https://Mugunthan93.github.io/mesell/ with the
 *   remotes published under /mesell/remotes/<name>/ (see .github/workflows/deploy-frontend.yml).
 *   Pass an inline manifest object of absolute remoteEntry.json URLs so prod never depends
 *   on a second static manifest file. `initFederation` accepts either a manifest URL (string)
 *   or a Manifest object (Record<remoteName, remoteEntryUrl>).
 */
const PROD_MANIFEST: Record<string, string> = {
  'mfe-auth': 'https://Mugunthan93.github.io/mesell/remotes/mfe-auth/remoteEntry.json',
  'mfe-billing': 'https://Mugunthan93.github.io/mesell/remotes/mfe-billing/remoteEntry.json',
  'mfe-catalog': 'https://Mugunthan93.github.io/mesell/remotes/mfe-catalog/remoteEntry.json',
  'mfe-dashboard': 'https://Mugunthan93.github.io/mesell/remotes/mfe-dashboard/remoteEntry.json',
  'mfe-export': 'https://Mugunthan93.github.io/mesell/remotes/mfe-export/remoteEntry.json',
  'mfe-onboarding': 'https://Mugunthan93.github.io/mesell/remotes/mfe-onboarding/remoteEntry.json',
  'mfe-pricing': 'https://Mugunthan93.github.io/mesell/remotes/mfe-pricing/remoteEntry.json',
};

initFederation(environment.production ? PROD_MANIFEST : 'federation.manifest.json')
  .catch((err) => console.error(err))
  .then((_) => import('./bootstrap'))
  .catch((err) => console.error(err));

// src/environments/environment.prod.ts — Production environment
// Build-time replacement via angular.json fileReplacements per §20.F

import { EnvConfig } from '@core/tokens/env-config.model';

export const environment: EnvConfig = {
  production: true,
  apiBaseUrl: 'https://api.mesell.xyz/api/v1',
  defaultLocale: 'en',
  serviceWorkerEnabled: true,
  bundleAnalyzerEnabled: false,
};

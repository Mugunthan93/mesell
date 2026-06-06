// src/environments/environment.ts — Development environment
// Build-time replacement via angular.json fileReplacements per §20.F

import { EnvConfig } from '@core/tokens/env-config.model';

export const environment: EnvConfig = {
  production: false,
  apiBaseUrl: 'https://api-dev.mesell.xyz/api/v1',
  defaultLocale: 'en',
  serviceWorkerEnabled: true,
  bundleAnalyzerEnabled: true,
};

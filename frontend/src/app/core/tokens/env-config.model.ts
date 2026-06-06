// core/tokens/env-config.model.ts
// EnvConfig shape per §4.H — build-time injected via InjectionToken

export interface EnvConfig {
  readonly production: boolean;
  readonly apiBaseUrl: string;
  readonly defaultLocale: 'en' | 'ta' | 'hi';
  readonly serviceWorkerEnabled: boolean;
  readonly bundleAnalyzerEnabled: boolean;
}

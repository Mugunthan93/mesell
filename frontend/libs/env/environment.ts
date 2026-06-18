/**
 * environment.ts — DEV default environment (committed, fileReplaced in production builds).
 *
 * apiBase: '' — relative paths, so the ng-serve proxy (/proxy.conf.json) handles /api/v1/*
 * routing to the backend. This means every HTTP call in the app uses /api/v1/... paths
 * byte-identical to what they were before this file existed (zero-diff for dev).
 *
 * Production swap: angular.json fileReplacements swaps this for environment.prod.ts when
 * building with --configuration production. See README.md for the full mapping table.
 *
 * Sync rule: keep in lockstep with backend .env APP_ENV, COOKIE_DOMAIN, COOKIE_SECURE.
 * Cross-origin apiBase (e.g. 'https://api.meesell.in') requires:
 *   - backend CORS_ALLOWED_ORIGINS must include the FE origin
 *   - backend allow_credentials=True (for the refresh cookie)
 *   - backend COOKIE_DOMAIN must cover both FE and API origins
 *   - backend COOKIE_SECURE=true
 */
export type { Environment } from './environment.interface';
import type { Environment } from './environment.interface';

export const environment: Environment = {
  production: false,
  name: 'development',
  /**
   * apiBase '' = relative paths — the ng-serve proxy in proxy.conf.json forwards
   * /api/v1/* to http://localhost:8000. In production the Ingress does the same.
   */
  apiBase: '',
  /**
   * DEV Google OAuth Web client id. Authorized JS origin = the shell dev origin
   * (http://localhost:4200 — the user interacts with the shell, never the
   * mfe-auth remote at :4206). Provisioned in GCP by infra (see handoff memo).
   * mesell-prod GIS Web client — same id authorizes localhost:4200, mesell.xyz,
   * and www.mesell.xyz. PUBLIC value (embedded in page) — not a secret.
   * Backend pins the SAME id for ID-token `aud` verification (FE/BE lockstep).
   */
  googleOauthClientId: '378368872039-q0kkbbih1fj50ea25c0eefvb8679sid9.apps.googleusercontent.com',
};

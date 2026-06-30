/**
 * environment.prod.ts — PRODUCTION environment swap file.
 *
 * Swapped in via angular.json fileReplacements on --configuration production.
 * This file is NEVER imported directly — angular.json replaces environment.ts with this.
 *
 * Imports Environment from environment.interface.ts (NOT from ./environment) to avoid
 * a circular import: fileReplacements makes environment.prod.ts the effective
 * ./environment, so importing from './environment' would be self-referential.
 *
 * apiBase — CROSS-ORIGIN in production (2026-06-30 platform pivot).
 *   The FE ships to GitHub Pages (https://Mugunthan93.github.io/mesell/) while the
 *   API runs on Fly.io (https://meesell-api.fly.dev). These are DIFFERENT origins,
 *   so apiBase is the absolute Fly URL and the backend env is set IN LOCKSTEP:
 *     - CORS_ALLOWED_ORIGINS includes https://Mugunthan93.github.io   (fly secret set)
 *     - CORS_ALLOW_CREDENTIALS=true  (for the HttpOnly refresh cookie) (already set)
 *     - COOKIE_SECURE=true                                             (already set)
 *     - COOKIE_DOMAIN=.fly.dev  (interim, until a custom apex domain)  (fly secret set)
 *   NOTE: a custom domain spanning both FE+API (e.g. *.meesell.in) is the durable
 *   fix for first-party refresh cookies; until then the refresh cookie is a
 *   third-party cookie (SameSite=None;Secure) scoped to *.fly.dev.
 *   DO NOT change apiBase without the matching backend env-var changes above.
 */
import type { Environment } from './environment.interface';

export const environment: Environment = {
  production: true,
  name: 'production',
  /**
   * Cross-origin: the GitHub Pages FE calls the Fly.io API at a different origin.
   * All /api/v1/... URLs are prefixed with this absolute base. Requires the
   * backend CORS + cookie env set in lockstep (see header doc above).
   */
  apiBase: 'https://meesell-api.fly.dev',
  /**
   * PROD Google OAuth Web client id. Authorized JS origin = the production app
   * (shell) origin. Provisioned in GCP by infra (see handoff memo). The backend
   * MUST pin this same id for ID-token `aud` verification.
   * mesell-prod GIS Web client — same id authorizes localhost:4200, mesell.xyz,
   * and www.mesell.xyz. PUBLIC value (embedded in page) — not a secret.
   */
  googleOauthClientId: '378368872039-q0kkbbih1fj50ea25c0eefvb8679sid9.apps.googleusercontent.com',
};

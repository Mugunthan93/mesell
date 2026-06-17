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
 * apiBase: '' — same-origin in production (K3s Traefik Ingress routes /api → api svc
 * on the same host). This means all /api/v1/... calls are byte-identical to dev.
 *
 * Cross-origin apiBase note:
 *   If a future deployment splits FE and API onto different origins (e.g.
 *   app.meesell.in and api.meesell.in), set apiBase: 'https://api.meesell.in'.
 *   That change REQUIRES backend changes IN LOCKSTEP:
 *     - CORS_ALLOWED_ORIGINS must include the FE origin
 *     - allow_credentials=True (for the HttpOnly refresh cookie)
 *     - COOKIE_DOMAIN must span both origins (e.g. '.meesell.in')
 *     - COOKIE_SECURE=true
 *   DO NOT change apiBase without those backend env-var changes.
 */
import type { Environment } from './environment.interface';

export const environment: Environment = {
  production: true,
  name: 'production',
  /**
   * '' = same-origin: production Ingress routes /api → api svc on the same host.
   * All /api/v1/... URLs remain relative — no CORS or cookie-domain changes needed.
   */
  apiBase: '',
};

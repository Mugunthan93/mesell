/**
 * Environment interface — NOT replaced by fileReplacements.
 * Both environment.ts and environment.prod.ts import from here.
 * This file is never subject to fileReplacements.
 */
export interface Environment {
  /** True only in production builds (swapped via fileReplacements). */
  readonly production: boolean;
  /** Human-readable environment name; use for diagnostics only, never for routing logic. */
  readonly name: 'development' | 'production';
  /**
   * API origin prefix prepended to every /api/v1/... path in ApiClient + AuthApiService.
   * '' = same-origin (default for both dev and prod V1 — Ingress routes /api → api svc).
   * Set to 'https://api.example.com' for cross-origin only (requires backend CORS changes).
   */
  readonly apiBase: string;
  /**
   * Google Identity Services OAuth 2.0 Web client id.
   * PUBLIC by design (embedded in the page) — NOT a secret, safe as a compile-time
   * constant. The backend pins the SAME client id for ID-token `aud` verification,
   * so FE/BE must stay in lockstep. Authorized JavaScript origins are configured on
   * the GCP OAuth client against the SHELL origin (not the mfe-auth remote origin).
   */
  readonly googleOauthClientId: string;
}

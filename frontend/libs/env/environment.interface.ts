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
}

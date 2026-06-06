// core/auth/jwt-payload.model.ts
// JWT claim structure issued by the FastAPI iam module

export type UUID = string;

export interface JwtPayload {
  /** Seller user ID */
  readonly sub: UUID;
  /** Expiry epoch seconds */
  readonly exp: number;
  /** Plan tier — free is default in V1; pro is V1.5 feature */
  readonly plan: 'free' | 'pro';
}

/**
 * Decodes a JWT without verifying the signature.
 * The backend validates the signature on every request; the frontend only reads claims.
 * Returns null if the token is absent or malformed.
 */
export function decodeJwt(token: string | null): JwtPayload | null {
  if (!token) return null;
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    // atob works in browsers; in test environments jsdom provides a shim
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'))) as unknown;
    if (typeof payload !== 'object' || payload === null) return null;
    const p = payload as Record<string, unknown>;
    if (typeof p['sub'] !== 'string' || typeof p['exp'] !== 'number') return null;
    return {
      sub: p['sub'] as UUID,
      exp: p['exp'] as number,
      plan: (p['plan'] === 'pro' ? 'pro' : 'free') as 'free' | 'pro',
    };
  } catch {
    return null;
  }
}

// core/auth/auth-tokens.ts
// InjectionToken for cross-module DI of the access token signal (§4.C)
// Avoids direct injection of the full AuthService where only the token is needed.

import { InjectionToken, Signal } from '@angular/core';

/**
 * InjectionToken carrying the read-only access token signal.
 * Provided via app.config.ts when needed for cross-module DI.
 * In V1, most consumers inject AuthService directly — this token is
 * reserved for cases where a library or shared component must read the
 * token without taking a hard dependency on AuthService.
 */
export const ACCESS_TOKEN_SIGNAL = new InjectionToken<Signal<string | null>>(
  'ACCESS_TOKEN_SIGNAL',
);

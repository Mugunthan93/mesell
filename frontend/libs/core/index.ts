// @mesell/core — Layer 0 shared singletons (federation singleton home, MASTER_PLAN §6.1).
// AuthService is the auth singleton declared `singleton: true` in the federation manifest.
export { AuthService } from './services/auth.service';
export type { AuthUser } from './services/auth.service';
export { AuthApiService } from './services/auth-api.service';
export type { MeResponse, SendOtpResponse, VerifyOtpResponse, RefreshResponse } from './services/auth-api.service';
export { authGuard } from './guards/auth.guard';

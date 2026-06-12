// @mesell/core — Layer 0 shared singletons (federation singleton home, MASTER_PLAN §6.1).
// AuthService is the auth singleton declared `singleton: true` in the federation manifest.

// ── Services ────────────────────────────────────────────────────────────────
export { AuthService } from './services/auth.service';
export type { AuthUser } from './services/auth.service';
export { AuthApiService } from './services/auth-api.service';
export type { MeResponse, SendOtpResponse, VerifyOtpResponse, RefreshResponse } from './services/auth-api.service';
export { ApiClient } from './services/api-client.service';
export type { ApiClientOptions } from './services/api-client.service';
export { ErrorService } from './services/error.service';
export { NetworkService } from './services/network.service';

// ── Interceptors ─────────────────────────────────────────────────────────────
export { jwtInterceptor } from './interceptors/jwt.interceptor';
export { refreshInterceptor } from './interceptors/refresh.interceptor';
export { errorInterceptor } from './interceptors/error.interceptor';
export type { ApiErrorEnvelope } from './interceptors/error.interceptor';

// ── Guards ───────────────────────────────────────────────────────────────────
export { authGuard } from './guards/auth.guard';

// ── Models (export type — erased at runtime, zero chunk cost — R-W6-3) ───────
export type { Product, ProductStatus } from './models/product.model';

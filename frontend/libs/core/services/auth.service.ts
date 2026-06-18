import { Injectable, signal, computed } from '@angular/core';

export interface AuthUser {
  id: number;
  name: string;
  phone: string;
}

// Federation singleton bridge: @mesell/core is a TS path alias (no package.json),
// so shareAll() cannot share it as a singleton — each remote bundles its own copy.
// sessionStorage is the shared medium both copies can read/write. The bridge key uses
// a prefix so it is isolated from any future real auth keys.
const SS_TOKEN_KEY = '__mee_design_auth__';
const SS_USER_KEY  = '__mee_design_user__';

function readBridgeToken(): string | null {
  try { return sessionStorage.getItem(SS_TOKEN_KEY); } catch { return null; }
}
function readBridgeUser(): AuthUser | null {
  try {
    const raw = sessionStorage.getItem(SS_USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch { return null; }
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  // Initialise from sessionStorage so the shell's instance picks up a session
  // that was written by the mfe-auth instance (and vice-versa).
  private readonly _token = signal<string | null>(readBridgeToken());
  private readonly _user  = signal<AuthUser | null>(readBridgeUser());

  // Also check sessionStorage directly: if the shell instance was constructed
  // before mfe-auth wrote the bridge key, the signal is null but storage is set.
  readonly isAuthenticated = computed(
    () => this._token() !== null || readBridgeToken() !== null,
  );
  readonly currentUser = computed(() => this._user() ?? readBridgeUser());

  /** Called by login/OTP flow after backend confirms token */
  setSession(token: string, user: AuthUser): void {
    try {
      sessionStorage.setItem(SS_TOKEN_KEY, token);
      sessionStorage.setItem(SS_USER_KEY, JSON.stringify(user));
    } catch { /* SSR / private-browsing no-op */ }
    this._token.set(token);
    this._user.set(user);
  }

  logout(): void {
    try {
      sessionStorage.removeItem(SS_TOKEN_KEY);
      sessionStorage.removeItem(SS_USER_KEY);
    } catch { /* no-op */ }
    this._token.set(null);
    this._user.set(null);
  }

  /** Returns bearer token for HTTP interceptor */
  getToken(): string | null {
    return this._token() ?? readBridgeToken();
  }
}

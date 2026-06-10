import { Injectable, signal, computed } from '@angular/core';

export interface AuthUser {
  id: number;
  name: string;
  phone: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  // FE-D5: in-memory token only — never persisted to localStorage/sessionStorage
  private readonly _token = signal<string | null>(null);
  private readonly _user  = signal<AuthUser | null>(null);

  readonly isAuthenticated = computed(() => this._token() !== null);
  readonly currentUser     = computed(() => this._user());

  /** Called by login/OTP flow after backend confirms token */
  setSession(token: string, user: AuthUser): void {
    this._token.set(token);
    this._user.set(user);
  }

  logout(): void {
    this._token.set(null);
    this._user.set(null);
  }

  /** Returns bearer token for HTTP interceptor */
  getToken(): string | null {
    return this._token();
  }
}

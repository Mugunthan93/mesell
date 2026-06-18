/**
 * google-gsi.d.ts — minimal ambient typing for the Google Identity Services
 * (GIS) browser global, scoped to the slice GoogleIdentityService uses.
 *
 * We deliberately DO NOT pull in `@types/google.accounts`:
 *  - it declares a large global `google` namespace that can collide across the
 *    federated builds (shell + 6 remotes each compile independently);
 *  - we only need `initialize`, `renderButton`, `prompt`, `cancel`,
 *    `disableAutoSelect`.
 * A hand-rolled minimal declaration keeps the global-type footprint tiny.
 *
 * GIS itself is NOT an npm dependency — it is a runtime browser asset fetched
 * from https://accounts.google.com/gsi/client. This file only types `window.google`.
 */

/** The callback payload GIS hands back after a successful credential selection. */
export interface GoogleCredentialResponse {
  /** The Google-issued ID token (a JWT). POSTed to the backend verify endpoint. */
  credential: string;
  /** How the credential was selected (e.g. 'btn', 'user', 'auto'). Diagnostic only. */
  select_by: string;
}

export interface GoogleIdConfiguration {
  client_id: string;
  callback: (response: GoogleCredentialResponse) => void;
  auto_select?: boolean;
  use_fedcm_for_prompt?: boolean;
}

export interface GoogleButtonConfiguration {
  type?: 'standard' | 'icon';
  theme?: 'outline' | 'filled_blue' | 'filled_black';
  size?: 'large' | 'medium' | 'small';
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
  shape?: 'rectangular' | 'pill' | 'circle' | 'square';
  logo_alignment?: 'left' | 'center';
  width?: number;
}

export interface GoogleAccountsId {
  initialize(config: GoogleIdConfiguration): void;
  renderButton(parent: HTMLElement, options: GoogleButtonConfiguration): void;
  prompt(): void;
  cancel(): void;
  disableAutoSelect(): void;
}

export interface GoogleAccounts {
  id: GoogleAccountsId;
}

export interface GoogleNamespace {
  accounts: GoogleAccounts;
}

declare global {
  interface Window {
    google?: GoogleNamespace;
  }
}


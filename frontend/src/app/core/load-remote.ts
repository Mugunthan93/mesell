import { loadRemoteModule } from '@angular-architects/native-federation';
import type { Type } from '@angular/core';

import { RemoteFailureComponent } from './remote-failure.component';

/**
 * MF Sub-Plan 01 (D12 / MASTER_PLAN §6.4) — the single reusable extraction primitive.
 *
 * Wraps `loadRemoteModule` for a route's `loadComponent`, returning the remote's
 * exposed component on success and the shell-owned `RemoteFailureComponent` on any
 * failure (remoteEntry 404, network error, malformed manifest). This is the codebase's
 * FIRST `loadRemoteModule` call (SP0 had zero).
 *
 * Reused verbatim by Sub-plans 02–06 — do NOT re-author per remote.
 *
 * @param remoteName     the federation manifest key (e.g. 'mfe-pricing')
 * @param exposedModule  the remote's `exposes` key (e.g. './PricingComponent')
 */
export function loadRemoteWithFallback(
  remoteName: string,
  exposedModule: string,
): () => Promise<Type<unknown>> {
  return () =>
    loadRemoteModule({ remoteName, exposedModule })
      // The remote exposes exactly one symbol (its public-api re-exports only the
      // component). Resolve the first exported value as the route component.
      .then((m: Record<string, Type<unknown>>) => m[Object.keys(m)[0]])
      .catch((err: unknown) => {
        console.error(`[federation] remote "${remoteName}" failed to load:`, err);
        return RemoteFailureComponent;
      });
}

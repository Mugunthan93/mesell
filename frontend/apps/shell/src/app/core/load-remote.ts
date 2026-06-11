import { loadRemoteModule } from '@angular-architects/native-federation';
import type { Type } from '@angular/core';
import { Routes } from '@angular/router';

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

/**
 * SP05 (D31) — Routes-array variant of loadRemoteWithFallback. Returns a `loadChildren`
 * function that resolves a remote's exposed Routes array. On load failure the WHOLE
 * sub-tree degrades to a single catch-all route rendering RemoteFailureComponent
 * (MASTER_PLAN §6.4) — not a white screen. Authored ONCE here; catalog is the only
 * flow-owning (Routes-expose) remote in V1.
 */
export function loadRemoteRoutesWithFallback(remoteName: string, exposedModule: string) {
  return () =>
    loadRemoteModule({ remoteName, exposedModule })
      .then(m => (m['CATALOG_ROUTES'] ?? Object.values(m).find(Array.isArray)) as Routes)
      .catch(() => [{ path: '**', component: RemoteFailureComponent }] as Routes);
}

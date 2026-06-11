// mfe-catalog — dev-serve / standalone bootstrap entry ONLY.
// In federation the routes are mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation.
//
// R-SP3-1 (P0 — SP05 is the HIGH-attention case): Native Federation's
// `ignoreUnusedDeps` analyzer (Sheriff) prunes shared-mappings from the import graph
// rooted at THIS main.ts. A shared lib (e.g. @mesell/core, which after D33 carries the
// promoted Product/Catalog types) consumed by an UNREACHED expose gets dropped from
// `shared[]` and INLINED into a component chunk → the remote gets its OWN copy →
// singleton drift (the SP03 bug). For a Routes-array expose, "all exposes reachable"
// means provideRouter(CATALOG_ROUTES) here — CATALOG_ROUTES references all 5 lazy
// loadComponent targets, so every page (and thus every shared lib any page consumes)
// stays in the analysis graph. Do NOT trim CATALOG_ROUTES here or short-circuit to a
// subset — the FULL route set must be reachable from main.ts (forward rule from SP03).
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';

import { CatalogListComponent } from './app/catalog-list.component';
import { CATALOG_ROUTES } from './app/catalog.routes';

import { jwtInterceptor, refreshInterceptor, errorInterceptor } from '@mesell/core';

bootstrapApplication(CatalogListComponent, {
  providers: [
    provideRouter(CATALOG_ROUTES),
    provideAnimationsAsync(),
    // HttpClient for standalone dev-serve (pnpm start:mfe-catalog).
    // In federation the shell injector (app.config.ts) provides HttpClient;
    // this entry is the fallback for the remote's own bootstrap context.
    // withFetch() = Fetch API backend (Angular 18+).
    // Wave 6 Wave A: interceptor chain matches shell (jwt → refresh → error).
    // NOTE: in federated mode the shell injector provides HttpClient; this
    // registration is for dev-serve standalone parity (proven #101 ruling).
    provideHttpClient(
      withFetch(),
      withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor]),
    ),
  ],
}).catch((err) => console.error(err));

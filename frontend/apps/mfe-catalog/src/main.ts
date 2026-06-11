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

import { CatalogListComponent } from './app/catalog-list.component';
import { CATALOG_ROUTES } from './app/catalog.routes';

bootstrapApplication(CatalogListComponent, {
  providers: [
    provideRouter(CATALOG_ROUTES),
    provideAnimationsAsync(),
  ],
}).catch((err) => console.error(err));

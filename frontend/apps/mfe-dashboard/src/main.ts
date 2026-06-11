// mfe-dashboard — dev-serve / standalone bootstrap entry ONLY.
// In federation each component is mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation.
//
// R-SP3-1 (P0): main.ts MUST reference BOTH exposed components. Native Federation's
// `ignoreUnusedDeps` analyzer (Sheriff) prunes shared-mappings from the import graph
// rooted at THIS main.ts. Routing to BOTH LandingComponent and DashboardComponent keeps
// every shared lib either page consumes (@mesell/ui-kit, @mesell/composites) in the
// analysis graph so they stay shared+singleton and resolve to the shell's import-map
// instances. Referencing only one expose would let a lib used solely by the OTHER expose
// get inlined into that component's chunk → silent singleton drift. (Mirrors mfe-onboarding.)
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, type Routes } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { LandingComponent } from './app/landing.component';
import { DashboardComponent } from './app/dashboard.component';

const devRoutes: Routes = [
  { path: '', component: LandingComponent },
  { path: 'dashboard', component: DashboardComponent },
];

bootstrapApplication(LandingComponent, {
  providers: [
    provideRouter(devRoutes),
    provideAnimationsAsync(),
  ],
}).catch((err) => console.error(err));

// mfe-onboarding — dev-serve / standalone bootstrap entry ONLY.
// In federation each component is mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation
// (the §9 "both routes load in shell" + the D22 C5 auth-singleton smoke tests).
// Bootstraps OnboardingComponent with a minimal router so the remote serves on its port.
//
// D22 C1 / R-SP3-1 (P0): main.ts MUST reference BOTH exposed components. Native
// Federation's `ignoreUnusedDeps` analyzer (Sheriff) prunes shared-mappings from the
// import graph rooted at THIS main.ts. ProfileComponent is the only consumer of
// @mesell/core (AuthService); if main.ts references OnboardingComponent alone, the
// graph excludes profile → @mesell/core is pruned from `shared` → AuthService gets
// INLINED into the remote → the remote would get its OWN AuthService instance, NOT the
// shell's singleton (auth-singleton DRIFT). Routing to BOTH exposed components here
// keeps profile (and thus @mesell/core) in the analysis graph so @mesell/core stays
// shared+singleton and resolves to the shell's import-map instance. This mirrors how
// SP05 (a Routes-array expose) will reference its full route component set.
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, type Routes } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { OnboardingComponent } from './app/onboarding.component';
import { ProfileComponent } from './app/profile.component';

const devRoutes: Routes = [
  { path: '', component: OnboardingComponent },
  { path: 'profile', component: ProfileComponent },
];

bootstrapApplication(OnboardingComponent, {
  providers: [
    provideRouter(devRoutes),
    provideAnimationsAsync(),
  ],
}).catch((err) => console.error(err));

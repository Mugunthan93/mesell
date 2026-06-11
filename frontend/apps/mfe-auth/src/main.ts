// mfe-auth — dev-serve / standalone bootstrap entry ONLY.
// In federation each component is mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation.
//
// R-SP3-1 (P0): main.ts MUST reference ALL THREE exposed components. Native Federation's
// `ignoreUnusedDeps` analyzer (Sheriff) prunes shared-mappings from the import graph rooted
// at THIS main.ts. OtpVerifyComponent is the @mesell/core (AuthService) consumer — routing
// to it keeps @mesell/core in the analysis graph so it stays shared+singleton and resolves
// to the SHELL's import-map instance. Without otp-verify reachable here, @mesell/core would
// be inlined into the otp chunk → setSession would mutate a DUPLICATE AuthService → the shell
// never sees authentication = the P0 WRITE-path drift (R-SP6-1 / MASTER_PLAN R1). Login + Signup
// are routed too for completeness (they consume @mesell/composites + @mesell/ui-kit). (Mirrors
// mfe-onboarding / mfe-dashboard.)
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, type Routes } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { LoginComponent } from './app/login.component';
import { SignupComponent } from './app/signup.component';
import { OtpVerifyComponent } from './app/otp-verify.component';

const devRoutes: Routes = [
  { path: '', component: LoginComponent },
  { path: 'signup', component: SignupComponent },
  { path: 'otp-verify', component: OtpVerifyComponent },
];

bootstrapApplication(LoginComponent, {
  providers: [
    provideRouter(devRoutes),
    provideAnimationsAsync(),
  ],
}).catch((err) => console.error(err));

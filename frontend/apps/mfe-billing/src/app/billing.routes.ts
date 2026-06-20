/**
 * billing.routes.ts — BILLING_ROUTES Routes array (the federation expose).
 *
 * Exposed as './BillingRoutes' from the mfe-billing federation config.
 * The shell mounts this via loadRemoteRoutesWithFallback('mfe-billing', './BillingRoutes')
 * under the authGuarded empty-path parent (both routes require auth, inherited from parent).
 *
 * BillingApiService is route-scoped (provided here, not providedIn:'root') — it is
 * remote-private and travels with the Routes-array expose (D28a/D32 precedent).
 * RazorpayCheckoutService is also route-scoped (needed only on the plans page).
 *
 * Routes:
 *   /billing/plans   — tier selection + checkout + start-trial
 *   /billing/account — current subscription + cancel
 */

import { Routes } from '@angular/router';
import { BillingApiService } from './billing-api.service';
import { RazorpayCheckoutService } from './checkout/razorpay-checkout.service';

export const BILLING_ROUTES: Routes = [
  {
    path: 'plans',
    loadComponent: () =>
      import('./plans/plans.component').then((m) => m.PlansComponent),
    providers: [BillingApiService, RazorpayCheckoutService],
  },
  {
    path: 'account',
    loadComponent: () =>
      import('./account/account-billing.component').then(
        (m) => m.AccountBillingComponent,
      ),
    providers: [BillingApiService],
  },
  {
    // Default /billing → redirect to plans
    path: '',
    redirectTo: 'plans',
    pathMatch: 'full',
  },
];

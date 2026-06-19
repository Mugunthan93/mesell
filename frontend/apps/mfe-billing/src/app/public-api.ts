/**
 * public-api.ts — mfe-billing federation expose entry point.
 *
 * Only BILLING_ROUTES is exposed via './BillingRoutes' in federation.config.js.
 * All other exports (model, service, constants) are remote-private — they are NOT
 * consumed across the federation boundary (only MeResponse/AuthUser widening crosses
 * into @mesell/core, which lives in libs/core/).
 */
export { BILLING_ROUTES } from './billing.routes';

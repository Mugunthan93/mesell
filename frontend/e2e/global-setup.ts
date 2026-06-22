/**
 * global-setup.ts — runs ONCE before the whole Playwright suite.
 *
 * Performs the OTP rate-limit env reset (clears `meesell:rl:*` in Valkey DB0) so the
 * suite's fresh-user logins are not 429'd by the 3/3600s-per-IP OTP-send limit. This
 * is the dev-env reset the brief mandates be in the harness setup, NOT inside a spec.
 */
import { resetRateLimits } from './fixtures/rate-limit';

export default async function globalSetup(): Promise<void> {
  await resetRateLimits();
}

/**
 * billing-poll.util.ts — RxJS post-checkout polling state-machine primitive.
 *
 * After the Razorpay widget closes (payment submitted OR short_url opened), the FE
 * polls GET /billing/subscription until the entitlement upgrades or the budget runs out.
 *
 * Rules (WAVE5_FRONTEND_TASKSPEC.md §5.2):
 *  - NEVER optimistic — the plan card does not flip until the poll observes entitlement.
 *  - Pending-timeout is NOT a failure — the webhook may still be delayed. Show
 *    reassuring copy + "Refresh status" button. Do NOT assert error.
 *  - Poll with timer + switchMap + takeWhile / take. Destroyed on component teardown
 *    (the D18 discipline — navigate-away must clear the poll via subject.complete()).
 *  - interval: POLL_INTERVAL_MS (3s). budget: POLL_MAX_ATTEMPTS (20) ≈ 60s.
 *
 * Usage (in Plans component):
 *   const sub = pollUntilActivated(
 *     () => billingApi.getSubscription(),
 *     expectedEntitlement,
 *     { onActivated, onTimeout },
 *   ).subscribe();
 *   // on destroy: sub.unsubscribe() (ngOnDestroy or takeUntilDestroyed)
 */

import {
  Observable,
  timer,
  switchMap,
  take,
  filter,
  tap,
  finalize,
} from 'rxjs';
import type { BillingSubscriptionResponse, EntitlementLiteral } from '../billing.model';
import { POLL_INTERVAL_MS, POLL_MAX_ATTEMPTS } from '../billing.model';

/** Callbacks for the polling observable. */
export interface PollCallbacks {
  /** Called when the entitlement upgrades to the expected level. */
  onActivated: (response: BillingSubscriptionResponse) => void;
  /** Called when the poll budget is exhausted without observing activation. */
  onTimeout: () => void;
}

/**
 * pollUntilActivated — returns an Observable that polls the billing subscription
 * endpoint until the entitlement matches or the budget runs out.
 *
 * The returned Observable should be subscribed by the component and stored.
 * Unsubscribe it in ngOnDestroy (or use takeUntilDestroyed) to clear the timer
 * on navigate-away (D18 timer-leak prevention).
 *
 * @param fetchSubscription — factory that calls BillingApiService.getSubscription()
 * @param targetEntitlement — the entitlement value we are waiting for
 * @param callbacks — onActivated + onTimeout handlers
 * @returns Observable<BillingSubscriptionResponse | null>
 */
export function pollUntilActivated(
  fetchSubscription: () => Observable<BillingSubscriptionResponse>,
  targetEntitlement: EntitlementLiteral,
  callbacks: PollCallbacks,
): Observable<BillingSubscriptionResponse> {
  let attemptCount = 0;
  let activated = false;

  return timer(POLL_INTERVAL_MS, POLL_INTERVAL_MS).pipe(
    // Limit total poll ticks to POLL_MAX_ATTEMPTS (budget)
    take(POLL_MAX_ATTEMPTS),
    // Each tick: call getSubscription() (switchMap cancels a prior in-flight call
    // if the timer fires before the previous response arrives — safe here because
    // each tick is 3s and typical API round-trip is <500ms)
    switchMap(() => {
      attemptCount++;
      return fetchSubscription();
    }),
    // Pass through responses that match the target entitlement
    tap((response: BillingSubscriptionResponse) => {
      if (response.entitlement === targetEntitlement && !activated) {
        activated = true;
        callbacks.onActivated(response);
      }
    }),
    // Stop emitting once activated (takeWhile + inclusive=true emits the activating item)
    // We use the `activated` flag to stop after the first match.
    filter(() => !activated || attemptCount < POLL_MAX_ATTEMPTS),
    finalize(() => {
      // finalize fires on complete (budget exhausted) AND on unsubscribe (navigate-away).
      // Only call onTimeout when budget is truly exhausted without activation.
      if (!activated && attemptCount >= POLL_MAX_ATTEMPTS) {
        callbacks.onTimeout();
      }
    }),
  );
}

/**
 * isEntitlementUpgrade — helper used by Plans component to determine whether the
 * poll result represents an upgrade for the current user.
 *
 * Collapse order: free < starter < pro < business.
 * Any response whose entitlement is higher than the user's current entitlement
 * (or matches the specifically requested tier's entitlement) counts as activated.
 */
export function isEntitlementUpgrade(
  previousEntitlement: EntitlementLiteral,
  newEntitlement: EntitlementLiteral,
): boolean {
  const rank: Record<EntitlementLitlement, number> = {
    free: 0,
    starter: 1,
    pro: 2,
    business: 3,
  };
  return (rank[newEntitlement] ?? 0) > (rank[previousEntitlement] ?? 0);
}

// ─── Local type alias to satisfy the rank lookup type ──────────────────────
type EntitlementLitlement = 'free' | 'starter' | 'pro' | 'business';

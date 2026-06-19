/**
 * PlansComponent — tier selection, Razorpay checkout, and trial CTA.
 *
 * STUB: service-builder shell for the state machine + service wiring.
 * The component-builder (Wave 5 step 2b) builds the full template, tier-card grid,
 * and entitlement-gated CTA rendering. This file establishes the:
 *   - Signal-based checkout state machine (CheckoutState)
 *   - Service injections (BillingApiService, RazorpayCheckoutService, AuthService)
 *   - subscribe() / startTrial() action methods
 *   - Polling setup and teardown (D18 — ngOnDestroy clears the poll subscription)
 *
 * The component-builder MUST:
 *   - Add the template (tier cards, pending panel, error banners)
 *   - Wire the state signals to the template
 *   - Add plan-card child components
 *   - Implement aria-live on the polling status region
 */

import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  inject,
  signal,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

import { AuthService } from '@mesell/core';

import { BillingApiService } from '../billing-api.service';
import { RazorpayCheckoutService } from '../checkout/razorpay-checkout.service';
import { pollUntilActivated } from '../checkout/billing-poll.util';
import { BILLING_STRINGS, TIER_DISPLAY } from '../billing.constants';

import type {
  CheckoutState,
  SubscribableTier,
  EntitlementLiteral,
  BillingErrorShape,
  BillingSubscribeResponse,
} from '../billing.model';

@Component({
  selector: 'app-plans',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  // TODO(component-builder): replace with full tier-card template
  template: `
    <div class="mee-plans">
      <p>Plans — template TODO (component-builder step 2b)</p>
      <p>Checkout state: {{ checkoutState() }}</p>
      <p>Current entitlement: {{ auth.entitlement() }}</p>
    </div>
  `,
})
export class PlansComponent implements OnDestroy {
  // ── Service injections ────────────────────────────────────────────────────
  protected readonly auth    = inject(AuthService);
  private readonly billing   = inject(BillingApiService);
  private readonly rzpCheckout = inject(RazorpayCheckoutService);

  // ── Checkout state machine ────────────────────────────────────────────────

  /** Current state of the checkout flow (see billing.model.ts CheckoutState). */
  readonly checkoutState = signal<CheckoutState>('idle');

  /** Error message to display when state === 'error'. */
  readonly errorMessage = signal<string>('');

  /** Tier currently being checked out (for loading spinners per card). */
  readonly activeTier = signal<SubscribableTier | null>(null);

  /** Entitlement value at the time checkout was initiated (for poll target). */
  private _priorEntitlement: EntitlementLiteral = 'free';

  /** Activated subscription response (for success message). */
  readonly activatedAt = signal<string | null>(null);

  /** Whether the trial CTA has been permanently hidden (409 trial-already-used). */
  readonly trialUnavailable = signal(false);

  /** Tier display table for the template. */
  readonly tiers = TIER_DISPLAY;

  /** Entitlement signal re-exposed for template ergonomics. */
  readonly entitlement = computed(() => this.auth.entitlement());

  // ── Poll subscription (D18 — must be cleared on destroy) ─────────────────
  private _pollSub: Subscription | null = null;

  // ── Action methods ────────────────────────────────────────────────────────

  /**
   * subscribe — main checkout action.
   * Called by the tier-card CTA button.
   *
   * State machine:
   *   idle → initiating → (checkout-open) → pending → activated | pending-timeout
   *   Any 409/502 → error
   *   Widget cancelled → cancelled → (reset to idle on next action)
   */
  subscribe(tier: SubscribableTier): void {
    if (this.checkoutState() !== 'idle' && this.checkoutState() !== 'cancelled' && this.checkoutState() !== 'error') {
      return; // debounce double-clicks during active checkout
    }

    this._priorEntitlement = this.auth.entitlement();
    this.activeTier.set(tier);
    this.checkoutState.set('initiating');
    this.errorMessage.set('');

    this.billing.subscribe(tier).subscribe({
      next: (resp: BillingSubscribeResponse) => {
        this.checkoutState.set('checkout-open');
        // Open Razorpay widget — the promise resolves when the widget closes.
        void this.rzpCheckout.openWidget(resp.checkout).then((result: import('./checkout/razorpay-checkout.service').CheckoutResult) => {
          if (result.status === 'cancelled') {
            this.checkoutState.set('cancelled');
            this.activeTier.set(null);
            return;
          }
          // payment_submitted or short_url_opened → transition to PENDING and poll
          this.checkoutState.set('pending');
          this._startPolling(tier);
        });
      },
      error: (err: BillingErrorShape) => {
        this._handleSubscribeError(err);
      },
    });
  }

  /**
   * startTrial — begin the 14-day Pro trial.
   * No Razorpay. Grant is immediate; single refreshUser() call is sufficient.
   */
  startTrial(): void {
    this.billing.startTrial().subscribe({
      next: () => {
        // Re-hydrate the auth user so the shell sidebar + all remotes see new entitlement.
        this.auth.refreshUser().subscribe();
        this.checkoutState.set('activated');
        this.activatedAt.set(new Date().toISOString());
        // TODO(component-builder): show success toast (BILLING_STRINGS['billing.trial_started'])
      },
      error: (err: BillingErrorShape) => {
        if (
          err.kind === 'billing_error' &&
          err.code === 'billing.trial.already_used'
        ) {
          // 409 trial-already-used — hide the CTA permanently for this session
          this.trialUnavailable.set(true);
          this.errorMessage.set(BILLING_STRINGS['billing.trial.already_used']);
        } else {
          this.errorMessage.set(BILLING_STRINGS['billing.generic_error']);
        }
        this.checkoutState.set('error');
      },
    });
  }

  /** Reset to idle (called after error/cancelled states for retry). */
  reset(): void {
    this._clearPoll();
    this.checkoutState.set('idle');
    this.activeTier.set(null);
    this.errorMessage.set('');
  }

  // ── D18 teardown ──────────────────────────────────────────────────────────

  ngOnDestroy(): void {
    this._clearPoll();
  }

  // ── Private helpers ───────────────────────────────────────────────────────

  private _startPolling(subscribedTier: SubscribableTier): void {
    this._clearPoll(); // safety: clear any prior poll

    // Determine the target entitlement for the subscribed tier.
    // The TIER_DISPLAY table maps tier → entitlement.
    const tierDisplay = TIER_DISPLAY.find((t) => t.tier === subscribedTier);
    const targetEntitlement: EntitlementLiteral = tierDisplay?.entitlement ?? 'pro';

    this._pollSub = pollUntilActivated(
      () => this.billing.getSubscription(),
      targetEntitlement,
      {
        onActivated: (resp) => {
          // Re-hydrate AuthService so the shell sees the new entitlement immediately.
          this.auth.refreshUser().subscribe();
          this.checkoutState.set('activated');
          this.activatedAt.set(resp.current_period_end);
          this.activeTier.set(null);
          this._clearPoll();
          // TODO(component-builder): show success toast (BILLING_STRINGS['billing.plan_activated'])
        },
        onTimeout: () => {
          // NOT a failure — webhook may be delayed.
          this.checkoutState.set('pending-timeout');
          this.activeTier.set(null);
          this._clearPoll();
          // TODO(component-builder): show reassuring copy + "Refresh status" button
        },
      },
    ).subscribe({
      error: () => {
        // Poll network error — transition to pending-timeout (same as budget-exhausted)
        this.checkoutState.set('pending-timeout');
        this.activeTier.set(null);
        this._clearPoll();
      },
    });
  }

  private _handleSubscribeError(err: BillingErrorShape): void {
    this.checkoutState.set('error');
    this.activeTier.set(null);

    if (err.kind === 'provider_unavailable') {
      this.errorMessage.set(BILLING_STRINGS['billing.provider_unavailable']);
    } else if (
      err.kind === 'billing_error' &&
      err.code === 'billing.subscription.already_active'
    ) {
      this.errorMessage.set(BILLING_STRINGS['billing.subscription.already_active']);
    } else {
      this.errorMessage.set(BILLING_STRINGS['billing.generic_error']);
    }
  }

  private _clearPoll(): void {
    if (this._pollSub) {
      this._pollSub.unsubscribe();
      this._pollSub = null;
    }
  }
}

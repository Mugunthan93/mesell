/**
 * AccountBillingComponent — current subscription view + cancel flow.
 *
 * STUB: service-builder shell for service wiring and cancel state.
 * The component-builder (Wave 5 step 2b) builds the full template, subscription
 * detail display, cancel confirm dialog, and entitlement-gated "Upgrade" CTA.
 *
 * The component-builder MUST:
 *   - Add the template (subscription status card, period-end display, cancel CTA)
 *   - Wire subscription data signal to the template
 *   - Implement MeeConfirmDialog for cancel confirmation
 *   - Hide the cancel button when plan === 'ltd' (LTD-perpetual rule)
 *   - Display "scheduled to cancel" badge when cancel_scheduled === true
 *   - Add aria-live on loading/error states
 */

import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { AuthService } from '@mesell/core';

import { BillingApiService } from '../billing-api.service';
import { BILLING_STRINGS } from '../billing.constants';

import type { BillingSubscriptionResponse, BillingErrorShape } from '../billing.model';

@Component({
  selector: 'app-account-billing',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  // TODO(component-builder): replace with full subscription management template
  template: `
    <div class="mee-account-billing">
      <p>Account Billing — template TODO (component-builder step 2b)</p>
      @if (loading()) {
        <p>Loading...</p>
      } @else if (subscription()) {
        <p>Plan: {{ subscription()?.plan }}</p>
        <p>Entitlement: {{ subscription()?.entitlement }}</p>
        <p>Status: {{ subscription()?.status }}</p>
        <p>Cancel scheduled: {{ subscription()?.cancel_scheduled }}</p>
      } @else if (billingUnavailable()) {
        <p>Billing is not available yet.</p>
      }
    </div>
  `,
})
export class AccountBillingComponent implements OnInit {
  // ── Service injections ────────────────────────────────────────────────────
  protected readonly auth   = inject(AuthService);
  private readonly billing  = inject(BillingApiService);

  // ── State signals ─────────────────────────────────────────────────────────

  readonly loading             = signal(true);
  readonly subscription        = signal<BillingSubscriptionResponse | null>(null);
  readonly billingUnavailable  = signal(false);
  readonly errorMessage        = signal('');
  readonly cancelPending       = signal(false);
  readonly cancelConfirmOpen   = signal(false);

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  ngOnInit(): void {
    this._loadSubscription();
  }

  // ── Action methods ────────────────────────────────────────────────────────

  /** Open the cancel confirmation dialog. */
  openCancelConfirm(): void {
    // Only accessible when plan !== 'ltd'
    if (this.subscription()?.plan === 'ltd') {
      this.errorMessage.set(BILLING_STRINGS['billing.subscription.none_active']);
      return;
    }
    this.cancelConfirmOpen.set(true);
  }

  /** Confirmed cancel — POST /billing/cancel. */
  confirmCancel(): void {
    this.cancelConfirmOpen.set(false);
    this.cancelPending.set(true);
    this.errorMessage.set('');

    this.billing.cancel().subscribe({
      next: () => {
        this.cancelPending.set(false);
        // Refresh subscription data to show cancel_scheduled badge.
        this._loadSubscription();
        // Re-hydrate auth user (entitlement unchanged until period_end).
        this.auth.refreshUser().subscribe();
        // TODO(component-builder): show toast (BILLING_STRINGS['billing.cancel_scheduled'])
      },
      error: (err: BillingErrorShape) => {
        this.cancelPending.set(false);
        this._handleCancelError(err);
      },
    });
  }

  /** Dismiss the cancel dialog. */
  dismissCancel(): void {
    this.cancelConfirmOpen.set(false);
  }

  // ── Private helpers ───────────────────────────────────────────────────────

  private _loadSubscription(): void {
    this.loading.set(true);
    this.billingUnavailable.set(false);
    this.errorMessage.set('');

    this.billing.getSubscription().subscribe({
      next: (sub: BillingSubscriptionResponse) => {
        this.subscription.set(sub);
        this.loading.set(false);
      },
      error: (err: BillingErrorShape) => {
        this.loading.set(false);
        // 404 → FEATURE_BILLING_ENABLED is off — degrade gracefully
        if (err.kind === 'billing_error' && err.status === 404) {
          this.billingUnavailable.set(true);
        } else {
          this.errorMessage.set(BILLING_STRINGS['billing.generic_error']);
        }
      },
    });
  }

  private _handleCancelError(err: BillingErrorShape): void {
    if (
      err.kind === 'billing_error' &&
      err.code === 'billing.subscription.none_active'
    ) {
      // LTD-perpetual or no active subscription — not a user-facing error.
      // Show informational copy and refresh the view.
      this.errorMessage.set(BILLING_STRINGS['billing.subscription.none_active']);
      this._loadSubscription();
    } else if (err.kind === 'provider_unavailable') {
      this.errorMessage.set(BILLING_STRINGS['billing.provider_unavailable']);
    } else {
      this.errorMessage.set(BILLING_STRINGS['billing.generic_error']);
    }
  }
}

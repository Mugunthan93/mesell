/**
 * PlansComponent — tier selection, Razorpay checkout, and trial CTA.
 *
 * Implements the full post-checkout polling state machine per WAVE5_FRONTEND_TASKSPEC §5.2:
 *   idle → initiating → checkout-open → pending → activated | pending-timeout | cancelled | error
 *
 * Key rules:
 *  - NEVER optimistic: plan card does not flip until poll detects entitlement upgrade.
 *  - pending-timeout is NOT a failure: reassuring copy + "Refresh status" button.
 *  - Poll is torn down on ngOnDestroy (D18 discipline).
 *  - Gating is on auth.entitlement(), never plan literal.
 *  - withCredentials NOT set (JWT Bearer path, not cookie).
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
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';

import { AuthService } from '@mesell/core';
import { MeeToastService } from '@mesell/ui-kit';

import { BillingApiService } from '../billing-api.service';
import { RazorpayCheckoutService } from '../checkout/razorpay-checkout.service';
import type { CheckoutResult } from '../checkout/razorpay-checkout.service';
import { pollUntilActivated } from '../checkout/billing-poll.util';
import { BILLING_STRINGS, TIER_DISPLAY } from '../billing.constants';
import { PlanCardComponent } from './plan-card.component';

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
  imports: [CommonModule, RouterLink, PlanCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; padding: var(--mee-space-4, 16px); }

    .plans-header {
      text-align: center;
      margin-bottom: var(--mee-space-8, 32px);
    }
    .plans-title {
      font-size: 22px;
      font-weight: 700;
      color: var(--mee-color-on-surface, #2a3547);
      margin: 0 0 var(--mee-space-2, 8px);
    }
    @media (min-width: 640px) {
      .plans-title { font-size: 28px; }
    }
    .plans-subtitle {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted, #5a6a85);
      margin: 0;
    }

    /* Tier grid — stacks at ≤639px, 2-col at 640px+, 3-col at 1024px+, 4-col at 1280px+ */
    .tier-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--mee-space-4, 16px);
      max-width: 1200px;
      margin: 0 auto;
    }
    @media (min-width: 640px) {
      .tier-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (min-width: 1024px) {
      .tier-grid { grid-template-columns: repeat(3, 1fr); }
    }
    @media (min-width: 1280px) {
      .tier-grid { grid-template-columns: repeat(4, 1fr); }
    }

    /* Pending panel */
    .pending-panel {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--mee-space-4, 16px);
      max-width: 480px;
      margin: var(--mee-space-8, 32px) auto;
      padding: var(--mee-space-8, 32px) var(--mee-space-6, 24px);
      background: var(--mee-color-surface-variant, #f5f5f5);
      border-radius: var(--mee-radius-lg, 12px);
      text-align: center;
    }
    .pending-panel__spinner {
      width: 48px;
      height: 48px;
      border: 4px solid var(--mee-color-surface-variant, #f2f6fa);
      border-top-color: var(--mee-color-primary, #F26B23);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    @media (prefers-reduced-motion: reduce) {
      .pending-panel__spinner {
        animation: none;
        border-top-color: var(--mee-color-primary, #F26B23);
        border-color: var(--mee-color-primary, #F26B23);
        opacity: 0.6;
      }
    }
    .pending-panel__title {
      font-size: 18px;
      font-weight: 600;
      color: var(--mee-color-on-surface, #2a3547);
      margin: 0;
    }
    .pending-panel__body {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted, #5a6a85);
      margin: 0;
      line-height: 1.5;
    }

    /* Pending-timeout panel */
    .timeout-panel {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--mee-space-4, 16px);
      max-width: 480px;
      margin: var(--mee-space-8, 32px) auto;
      padding: var(--mee-space-6, 24px);
      background: var(--mee-color-info-light, rgba(37,99,235,0.10));
      border: 1px solid var(--mee-color-info, #2563EB);
      border-radius: var(--mee-radius-lg, 12px);
      text-align: center;
    }
    .timeout-panel__icon { font-size: 36px; }
    .timeout-panel__title {
      font-size: 16px;
      font-weight: 600;
      color: var(--mee-color-on-surface, #2a3547);
      margin: 0;
    }
    .timeout-panel__body {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted, #5a6a85);
      margin: 0;
      line-height: 1.5;
    }
    .timeout-panel__refresh-btn {
      min-height: 44px;
      padding: 0 var(--mee-space-6, 24px);
      background: var(--mee-color-primary, #F26B23);
      color: #fff;
      border: none;
      border-radius: var(--mee-radius-md, 8px);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
    .timeout-panel__refresh-btn:hover { opacity: 0.9; }

    /* Success panel */
    .success-panel {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--mee-space-4, 16px);
      max-width: 480px;
      margin: var(--mee-space-8, 32px) auto;
      padding: var(--mee-space-8, 32px) var(--mee-space-6, 24px);
      background: var(--mee-color-success-light, rgba(22,163,74,0.10));
      border: 1px solid var(--mee-color-success, #16A34A);
      border-radius: var(--mee-radius-lg, 12px);
      text-align: center;
    }
    .success-panel__icon { font-size: 40px; }
    .success-panel__title {
      font-size: 20px;
      font-weight: 700;
      color: var(--mee-color-on-surface, #2a3547);
      margin: 0;
    }
    .success-panel__body {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted, #5a6a85);
      margin: 0;
    }
    .success-panel__cta {
      min-height: 44px;
      padding: 0 var(--mee-space-8, 32px);
      background: var(--mee-color-primary, #F26B23);
      color: #fff;
      border: none;
      border-radius: var(--mee-radius-md, 8px);
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
    }

    /* Error banner */
    .error-banner {
      max-width: 640px;
      margin: 0 auto var(--mee-space-4, 16px);
      padding: var(--mee-space-3, 12px) var(--mee-space-4, 16px);
      background: var(--mee-color-error-light, rgba(220,38,38,0.10));
      border: 1px solid var(--mee-color-error, #DC2626);
      border-radius: var(--mee-radius-md, 8px);
      color: var(--mee-color-error, #DC2626);
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: var(--mee-space-2, 8px);
    }
    .error-banner__retry-btn {
      margin-left: auto;
      min-height: 36px;
      padding: 0 var(--mee-space-4, 16px);
      background: transparent;
      border: 1px solid var(--mee-color-error, #DC2626);
      border-radius: var(--mee-radius-sm, 6px);
      color: var(--mee-color-error, #DC2626);
      font-size: 13px;
      cursor: pointer;
      white-space: nowrap;
    }

    /* Cancelled notice */
    .cancelled-notice {
      max-width: 480px;
      margin: 0 auto var(--mee-space-4, 16px);
      padding: var(--mee-space-3, 12px) var(--mee-space-4, 16px);
      background: var(--mee-color-surface-variant, #f5f5f5);
      border-radius: var(--mee-radius-md, 8px);
      font-size: 14px;
      color: var(--mee-color-on-surface-muted, #5a6a85);
      text-align: center;
    }

    /* Trial CTA banner */
    .trial-banner {
      max-width: 640px;
      margin: 0 auto var(--mee-space-6, 24px);
      padding: var(--mee-space-4, 16px) var(--mee-space-5, 20px);
      background: linear-gradient(135deg, rgba(242,107,35,0.08), rgba(242,107,35,0.15));
      border: 1px solid var(--mee-color-primary-light, rgba(242,107,35,0.3));
      border-radius: var(--mee-radius-lg, 12px);
      display: flex;
      align-items: center;
      gap: var(--mee-space-4, 16px);
      flex-wrap: wrap;
    }
    .trial-banner__text {
      flex: 1;
      font-size: 14px;
      color: var(--mee-color-on-surface, #2a3547);
      margin: 0;
    }
    .trial-banner__cta {
      min-height: 44px;
      padding: 0 var(--mee-space-5, 20px);
      background: var(--mee-color-primary, #F26B23);
      color: #fff;
      border: none;
      border-radius: var(--mee-radius-md, 8px);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
    }
    .trial-banner__cta:disabled { opacity: 0.6; cursor: not-allowed; }
    /* Mobile: trial CTA full-width so it's reachable on 360px */
    @media (max-width: 479px) {
      .trial-banner { flex-direction: column; align-items: stretch; }
      .trial-banner__cta { width: 100%; }
    }

    /* prefers-reduced-motion: disable all transitions/animations in this component */
    @media (prefers-reduced-motion: reduce) {
      .timeout-panel__refresh-btn,
      .success-panel__cta,
      .trial-banner__cta { transition: none; }
    }

    /* Billing unavailable */
    .unavailable-notice {
      max-width: 480px;
      margin: var(--mee-space-8, 32px) auto;
      padding: var(--mee-space-6, 24px);
      text-align: center;
      color: var(--mee-color-on-surface-muted, #5a6a85);
      font-size: 15px;
    }
  `],
  template: `
    <!-- === BILLING UNAVAILABLE (FEATURE_BILLING_ENABLED=off) === -->
    @if (billingUnavailable()) {
      <div class="unavailable-notice" role="status">
        <p>Billing is not available yet. Check back soon.</p>
      </div>
    } @else {

      <!-- === PENDING: processing your payment === -->
      @if (checkoutState() === 'pending') {
        <div
          class="pending-panel"
          role="status"
          aria-live="polite"
          aria-atomic="true"
          aria-label="Processing your payment"
        >
          <div class="pending-panel__spinner" aria-hidden="true"></div>
          <p class="pending-panel__title">{{ STRINGS['billing.processing'] }}</p>
          <p class="pending-panel__body">
            This usually takes just a few seconds.
            Please don't close this tab.
          </p>
        </div>
      }

      <!-- === PENDING-TIMEOUT: webhook delayed, not a failure === -->
      @if (checkoutState() === 'pending-timeout') {
        <div
          class="timeout-panel"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          <span class="timeout-panel__icon" aria-hidden="true">&#x1F4E8;</span>
          <p class="timeout-panel__title">Almost there!</p>
          <p class="timeout-panel__body">
            {{ STRINGS['billing.activation_pending'] }}
          </p>
          <button
            class="timeout-panel__refresh-btn"
            type="button"
            (click)="refreshStatus()"
            aria-label="Refresh subscription status"
          >
            Refresh status
          </button>
        </div>
      }

      <!-- === ACTIVATED: success === -->
      @if (checkoutState() === 'activated') {
        <div
          class="success-panel"
          role="status"
          aria-live="polite"
          aria-atomic="true"
        >
          <span class="success-panel__icon" aria-hidden="true">&#x2705;</span>
          <p class="success-panel__title">Plan activated!</p>
          <p class="success-panel__body">{{ STRINGS['billing.plan_activated'] }}</p>
          <a
            class="success-panel__cta"
            routerLink="/billing/account"
            role="button"
          >
            Manage my plan
          </a>
        </div>
      }

      <!-- === ERROR banner (409 / 502 / generic) === -->
      @if (checkoutState() === 'error' && errorMessage()) {
        <div class="error-banner" role="alert">
          <span>{{ errorMessage() }}</span>
          <button
            class="error-banner__retry-btn"
            type="button"
            (click)="reset()"
            aria-label="Dismiss error and retry"
          >
            Try again
          </button>
        </div>
      }

      <!-- === CANCELLED notice === -->
      @if (checkoutState() === 'cancelled') {
        <div class="cancelled-notice" role="status" aria-live="polite">
          {{ STRINGS['billing.checkout_cancelled'] }}
        </div>
      }

      <!-- === PLANS PAGE (idle / cancelled / error / initiating / checkout-open) === -->
      @if (!['pending', 'pending-timeout', 'activated'].includes(checkoutState())) {

        <header class="plans-header">
          <h1 class="plans-title">Choose your plan</h1>
          <p class="plans-subtitle">
            All plans include a 14-day free Pro trial for new sellers.
          </p>
        </header>

        <!-- 14-day trial CTA — only for free entitlement, not yet trialed -->
        @if (showTrialCTA()) {
          <div class="trial-banner" aria-label="Free trial offer">
            <p class="trial-banner__text">
              <strong>Try Pro free for 14 days</strong> — no credit card required.
              Unlimited listings, all AI features, full access.
            </p>
            <button
              class="trial-banner__cta"
              type="button"
              [disabled]="trialInProgress()"
              (click)="startTrial()"
              aria-label="Start your free 14-day Pro trial"
            >
              @if (trialInProgress()) { Starting… } @else { Start free trial }
            </button>
          </div>
        }

        <!-- Tier card grid -->
        <div class="tier-grid" role="list" aria-label="Subscription plans">
          @for (tier of tiers; track tier.tier) {
            <app-plan-card
              [tier]="tier"
              [currentEntitlement]="entitlement()"
              [isInitiating]="activeTier() === tier.tier && checkoutState() === 'initiating'"
              (subscribe)="subscribe($event)"
              role="listitem"
            />
          }
        </div>
      }

    }
  `,
})
export class PlansComponent implements OnDestroy {
  // ── Service injections ────────────────────────────────────────────────────
  protected readonly auth       = inject(AuthService);
  private readonly billing      = inject(BillingApiService);
  private readonly rzpCheckout  = inject(RazorpayCheckoutService);
  private readonly toast        = inject(MeeToastService);

  // ── Constants ─────────────────────────────────────────────────────────────
  readonly STRINGS = BILLING_STRINGS;

  /** Tier display table for the template (all tiers including free). */
  readonly tiers = TIER_DISPLAY;

  // ── Checkout state machine ────────────────────────────────────────────────

  /** Current state of the checkout flow. */
  readonly checkoutState = signal<CheckoutState>('idle');

  /** Error message to display when state === 'error'. */
  readonly errorMessage = signal<string>('');

  /** Tier currently being checked out (for per-card loading spinners). */
  readonly activeTier = signal<SubscribableTier | null>(null);

  /** Whether billing feature is unavailable (FEATURE_BILLING_ENABLED=off). */
  readonly billingUnavailable = signal(false);

  /** Whether the trial CTA is hidden (409 trial-already-used). */
  readonly trialUnavailable = signal(false);

  /** Whether startTrial() is in-flight. */
  readonly trialInProgress = signal(false);

  /** Effective entitlement re-exposed for template ergonomics. */
  readonly entitlement = computed(() => this.auth.entitlement());

  /**
   * Show trial CTA only when:
   *  - User is on free entitlement
   *  - Trial has not been used (no trial_ends_at set on the user)
   *  - The 409 trial-already-used error has not been hit this session
   */
  readonly showTrialCTA = computed(() => {
    if (this.entitlement() !== 'free') return false;
    if (this.trialUnavailable()) return false;
    const user = this.auth.currentUser();
    // If the user has trial_ends_at (any value, past or future), trial was used.
    if (user?.trial_ends_at) return false;
    return true;
  });

  /** Entitlement at the time checkout was initiated (for poll target comparison). */
  private _priorEntitlement: EntitlementLiteral = 'free';

  // ── Poll subscription (D18 — must be cleared on destroy) ─────────────────
  private _pollSub: Subscription | null = null;

  // ── Action methods ────────────────────────────────────────────────────────

  /**
   * subscribe — main checkout action.
   * Called by PlanCardComponent's (subscribe) output.
   *
   * State machine: idle → initiating → checkout-open → pending → activated | pending-timeout
   * Errors: 409 (already-subscribed) | 502 (provider unavailable) → error state
   * Widget dismiss without payment → cancelled
   */
  subscribe(tier: SubscribableTier): void {
    const state = this.checkoutState();
    if (state !== 'idle' && state !== 'cancelled' && state !== 'error') {
      return; // debounce: reject while a checkout is already active
    }

    this._priorEntitlement = this.auth.entitlement();
    this.activeTier.set(tier);
    this.checkoutState.set('initiating');
    this.errorMessage.set('');

    this.billing.subscribe(tier).subscribe({
      next: (resp: BillingSubscribeResponse) => {
        // DEV-MOCK: backend already granted entitlement synchronously — skip checkout.js,
        // go straight to PENDING + poll (the first poll flips to active).
        if (resp.checkout.mock) {
          this.checkoutState.set('pending');
          this._startPolling(tier);
          return;
        }
        this.checkoutState.set('checkout-open');
        void this.rzpCheckout.openWidget(resp.checkout).then((result: CheckoutResult) => {
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
   * No Razorpay, no polling. Grant is immediate; a single refreshUser() is sufficient.
   */
  startTrial(): void {
    this.trialInProgress.set(true);
    this.billing.startTrial().subscribe({
      next: () => {
        // Re-hydrate the auth user so the shell sidebar + all remotes see new entitlement.
        this.auth.refreshUser().subscribe({
          next: () => {
            this.trialInProgress.set(false);
            this.checkoutState.set('activated');
            this.toast.success(BILLING_STRINGS['billing.trial_started'], 'Trial started!');
          },
          error: () => {
            this.trialInProgress.set(false);
            this.checkoutState.set('activated');
          },
        });
      },
      error: (err: BillingErrorShape) => {
        this.trialInProgress.set(false);
        if (
          err.kind === 'billing_error' &&
          err.code === 'billing.trial.already_used'
        ) {
          this.trialUnavailable.set(true);
          this.toast.warn(BILLING_STRINGS['billing.trial.already_used'], 'Trial already used');
        } else {
          this.errorMessage.set(BILLING_STRINGS['billing.generic_error']);
          this.checkoutState.set('error');
        }
      },
    });
  }

  /**
   * refreshStatus — manually refresh subscription after pending-timeout.
   * Re-polls once; if still not activated, stays in pending-timeout.
   */
  refreshStatus(): void {
    this.billing.getSubscription().subscribe({
      next: (sub) => {
        if (sub.entitlement !== this._priorEntitlement && sub.entitlement !== 'free') {
          this.auth.refreshUser().subscribe();
          this.checkoutState.set('activated');
          this.toast.success(BILLING_STRINGS['billing.plan_activated'], 'Plan activated!');
        }
        // Otherwise stay on pending-timeout with the Refresh button available.
      },
      error: (err: BillingErrorShape) => {
        if (err.kind === 'billing_error' && err.status === 404) {
          this.billingUnavailable.set(true);
        }
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
    this._clearPoll();

    const tierDisplay = TIER_DISPLAY.find((t) => t.tier === subscribedTier);
    const targetEntitlement: EntitlementLiteral = tierDisplay?.entitlement ?? 'pro';

    this._pollSub = pollUntilActivated(
      () => this.billing.getSubscription(),
      targetEntitlement,
      {
        onActivated: (resp) => {
          this.auth.refreshUser().subscribe();
          this.checkoutState.set('activated');
          this.activeTier.set(null);
          this._clearPoll();
          this.toast.success(BILLING_STRINGS['billing.plan_activated'], 'Plan activated!');
          void resp; // resp available for future use (e.g. period_end display)
        },
        onTimeout: () => {
          // NOT a failure — webhook may be delayed. Show reassuring copy.
          this.checkoutState.set('pending-timeout');
          this.activeTier.set(null);
          this._clearPoll();
        },
      },
    ).subscribe({
      error: () => {
        // Poll network error — treat same as timeout (non-alarming)
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

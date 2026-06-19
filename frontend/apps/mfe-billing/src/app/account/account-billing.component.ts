/**
 * AccountBillingComponent — current subscription status + cancel flow.
 *
 * Displays:
 *  - Current plan label, entitlement, status, period-end
 *  - "Scheduled to cancel" badge when cancel_scheduled === true
 *  - Cancel CTA → MeeConfirmService confirm dialog → POST /billing/cancel
 *  - LTD-perpetual rule: cancel button hidden when plan === 'ltd'
 *  - none_active graceful handling (404/409 on cancel → informational copy)
 *  - FEATURE_BILLING_ENABLED off (404 on load) → graceful unavailable state
 *  - Upgrade CTA when entitlement === 'free'
 *
 * Lifecycle:
 *  - ngOnInit → GET /billing/subscription → populate subscription()
 *  - Cancel confirm → POST /billing/cancel → refresh subscription()
 *
 * Auth pattern:
 *  - auth.refreshUser() called after cancel 200 (entitlement unchanged until period_end,
 *    but shell sidebar stays in sync)
 */

import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';

import { AuthService } from '@mesell/core';
import { MeeConfirmService, MeeToastService } from '@mesell/ui-kit';

import { BillingApiService } from '../billing-api.service';
import { BILLING_STRINGS } from '../billing.constants';

import type { BillingSubscriptionResponse, BillingErrorShape } from '../billing.model';

@Component({
  selector: 'app-account-billing',
  standalone: true,
  imports: [CommonModule, DatePipe, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; padding: var(--mee-space-4, 16px); }

    .account-billing-header {
      margin-bottom: var(--mee-space-6, 24px);
    }
    .account-billing-title {
      font-size: 24px;
      font-weight: 700;
      color: var(--mee-color-on-surface, #1a1a1a);
      margin: 0 0 var(--mee-space-1, 4px);
    }
    .account-billing-subtitle {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted, #666);
      margin: 0;
    }

    /* Skeleton */
    .skeleton {
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
      border-radius: var(--mee-radius-md, 8px);
    }
    @keyframes shimmer { to { background-position: -200% 0; } }
    .skeleton--line { height: 20px; margin-bottom: 12px; }
    .skeleton--wide { width: 60%; }
    .skeleton--medium { width: 40%; }

    /* Subscription card */
    .sub-card {
      max-width: 640px;
      border: 1px solid var(--mee-color-outline-variant, #e0e0e0);
      border-radius: var(--mee-radius-lg, 12px);
      overflow: hidden;
    }
    .sub-card__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--mee-space-5, 20px);
      background: var(--mee-color-surface-variant, #f9f9f9);
      border-bottom: 1px solid var(--mee-color-outline-variant, #e0e0e0);
      flex-wrap: wrap;
      gap: var(--mee-space-3, 12px);
    }
    .sub-card__plan-name {
      font-size: 20px;
      font-weight: 700;
      color: var(--mee-color-on-surface, #1a1a1a);
      margin: 0;
    }
    .sub-card__body {
      padding: var(--mee-space-5, 20px);
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4, 16px);
    }

    /* Info row */
    .info-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: var(--mee-space-4, 16px);
      font-size: 14px;
      padding-bottom: var(--mee-space-3, 12px);
      border-bottom: 1px solid var(--mee-color-outline-variant, #e0e0e0);
    }
    .info-row:last-child { border-bottom: none; padding-bottom: 0; }
    .info-row__label {
      color: var(--mee-color-on-surface-muted, #666);
      font-weight: 500;
    }
    .info-row__value {
      color: var(--mee-color-on-surface, #1a1a1a);
      font-weight: 600;
      text-align: right;
    }

    /* Badges */
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 10px;
      border-radius: var(--mee-radius-full, 999px);
      font-size: 12px;
      font-weight: 600;
    }
    .badge--active { background: rgba(34,197,94,0.15); color: var(--mee-color-success, #22c55e); }
    .badge--cancelled { background: rgba(239,68,68,0.1); color: var(--mee-color-error, #ef4444); }
    .badge--pro { background: rgba(242,107,35,0.12); color: var(--mee-color-primary, #F26B23); }
    .badge--free { background: var(--mee-color-surface-variant, #f0f0f0); color: var(--mee-color-on-surface-muted, #666); }
    .badge--cancel-scheduled {
      background: rgba(234,179,8,0.15);
      color: var(--mee-color-warning, #ca8a04);
    }

    /* Actions */
    .sub-card__actions {
      padding: var(--mee-space-4, 16px) var(--mee-space-5, 20px);
      border-top: 1px solid var(--mee-color-outline-variant, #e0e0e0);
      display: flex;
      gap: var(--mee-space-3, 12px);
      flex-wrap: wrap;
      align-items: center;
    }
    .btn-cancel {
      min-height: 44px;
      padding: 0 var(--mee-space-5, 20px);
      background: transparent;
      border: 1px solid var(--mee-color-error, #ef4444);
      border-radius: var(--mee-radius-md, 8px);
      color: var(--mee-color-error, #ef4444);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
    }
    .btn-cancel:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-upgrade {
      min-height: 44px;
      padding: 0 var(--mee-space-5, 20px);
      background: var(--mee-color-primary, #F26B23);
      border: none;
      border-radius: var(--mee-radius-md, 8px);
      color: #fff;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
    }
    .btn-upgrade:hover { opacity: 0.9; }

    /* Error banner */
    .error-banner {
      padding: var(--mee-space-3, 12px) var(--mee-space-4, 16px);
      background: rgba(239,68,68,0.08);
      border: 1px solid var(--mee-color-error, #ef4444);
      border-radius: var(--mee-radius-md, 8px);
      color: var(--mee-color-error, #ef4444);
      font-size: 14px;
      margin-bottom: var(--mee-space-4, 16px);
    }

    /* Unavailable / free states */
    .unavailable-notice {
      max-width: 480px;
      padding: var(--mee-space-8, 32px) var(--mee-space-6, 24px);
      text-align: center;
      color: var(--mee-color-on-surface-muted, #666);
      font-size: 15px;
    }
    .free-state {
      max-width: 480px;
      padding: var(--mee-space-6, 24px);
      border: 1px dashed var(--mee-color-outline-variant, #e0e0e0);
      border-radius: var(--mee-radius-lg, 12px);
      text-align: center;
    }
    .free-state__title {
      font-size: 18px;
      font-weight: 600;
      color: var(--mee-color-on-surface, #1a1a1a);
      margin: 0 0 var(--mee-space-3, 12px);
    }
    .free-state__body {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted, #666);
      margin: 0 0 var(--mee-space-5, 20px);
    }

    /* LTD perpetual notice */
    .ltd-notice {
      padding: var(--mee-space-3, 12px) var(--mee-space-4, 16px);
      background: rgba(242,107,35,0.08);
      border: 1px solid var(--mee-color-primary-light, rgba(242,107,35,0.3));
      border-radius: var(--mee-radius-md, 8px);
      font-size: 14px;
      color: var(--mee-color-on-surface-muted, #666);
      font-style: italic;
    }
  `],
  template: `
    <header class="account-billing-header">
      <h1 class="account-billing-title">Billing &amp; Subscription</h1>
      <p class="account-billing-subtitle">Manage your current plan and billing details.</p>
    </header>

    <!-- === LOADING skeleton === -->
    @if (loading()) {
      <div aria-live="polite" aria-label="Loading subscription details" role="status">
        <div class="skeleton skeleton--line skeleton--wide"></div>
        <div class="skeleton skeleton--line skeleton--medium"></div>
        <div class="skeleton skeleton--line skeleton--wide"></div>
      </div>
    }

    <!-- === BILLING UNAVAILABLE (FEATURE_BILLING_ENABLED=off) === -->
    @if (!loading() && billingUnavailable()) {
      <div class="unavailable-notice" role="status">
        <p>Billing is not available yet. Check back soon.</p>
      </div>
    }

    <!-- === ERROR banner (non-404 load error) === -->
    @if (!loading() && errorMessage()) {
      <div class="error-banner" role="alert">{{ errorMessage() }}</div>
    }

    <!-- === FREE tier — no active subscription === -->
    @if (!loading() && !billingUnavailable() && isFree()) {
      <div class="free-state">
        <p class="free-state__title">You're on the Free plan</p>
        <p class="free-state__body">
          Upgrade to unlock unlimited listings, priority AI queue, and more.
        </p>
        <a class="btn-upgrade" routerLink="/billing/plans" aria-label="View upgrade plans">
          View plans
        </a>
      </div>
    }

    <!-- === ACTIVE SUBSCRIPTION === -->
    @if (!loading() && !billingUnavailable() && subscription() && !isFree()) {
      <div class="sub-card">
        <!-- Card header: plan name + badges -->
        <div class="sub-card__header">
          <h2 class="sub-card__plan-name">{{ subscription()!.tier_label }}</h2>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <!-- Cancel-scheduled badge -->
            @if (subscription()!.cancel_scheduled) {
              <span
                class="badge badge--cancel-scheduled"
                role="status"
                aria-label="Cancellation scheduled"
              >
                Cancellation scheduled
              </span>
            }
            <!-- Entitlement badge -->
            <span
              class="badge"
              [class.badge--active]="subscription()!.status === 'active' || subscription()!.status === 'authenticated'"
              [class.badge--cancelled]="subscription()!.cancel_scheduled"
              [class.badge--pro]="subscription()!.entitlement === 'pro' || subscription()!.entitlement === 'business'"
              [class.badge--free]="subscription()!.entitlement === 'free' || subscription()!.entitlement === 'starter'"
              aria-label="Current entitlement: {{ subscription()!.entitlement }}"
            >
              {{ entitlementLabel() }}
            </span>
          </div>
        </div>

        <!-- Card body: info rows -->
        <div class="sub-card__body">
          <!-- Status row (subscription only — not for LTD/free) -->
          @if (subscription()!.status) {
            <div class="info-row">
              <span class="info-row__label">Status</span>
              <span class="info-row__value">{{ subscription()!.status | titlecase }}</span>
            </div>
          }

          <!-- Period end (null for LTD/free → show "Lifetime" or omit) -->
          @if (subscription()!.plan === 'ltd') {
            <div class="info-row">
              <span class="info-row__label">Expires</span>
              <span class="info-row__value">Never — Lifetime access</span>
            </div>
          } @else if (subscription()!.current_period_end) {
            <div class="info-row">
              <span class="info-row__label">
                {{ subscription()!.cancel_scheduled ? 'Access until' : 'Next billing date' }}
              </span>
              <span class="info-row__value">
                {{ subscription()!.current_period_end | date:'mediumDate' }}
              </span>
            </div>
          }

          <!-- Trial end (when on trial) -->
          @if (subscription()!.trial_ends_at) {
            <div class="info-row">
              <span class="info-row__label">Trial ends</span>
              <span class="info-row__value">
                {{ subscription()!.trial_ends_at | date:'mediumDate' }}
              </span>
            </div>
          }

          <!-- LTD perpetual notice -->
          @if (subscription()!.plan === 'ltd') {
            <div class="ltd-notice" role="note" aria-label="Lifetime plan information">
              Your Lifetime plan never expires — there is nothing to cancel.
            </div>
          }
        </div>

        <!-- Card actions -->
        <div class="sub-card__actions">
          <!-- Upgrade CTA (for starter/pro → higher tier) -->
          @if (showUpgradeCTA()) {
            <a class="btn-upgrade" routerLink="/billing/plans" aria-label="Upgrade your plan">
              Upgrade plan
            </a>
          }

          <!-- Cancel CTA — hidden for LTD and when already scheduled -->
          @if (showCancelCTA()) {
            <button
              class="btn-cancel"
              type="button"
              [disabled]="cancelPending()"
              (click)="openCancelConfirm()"
              aria-label="Cancel plan at end of billing cycle"
            >
              @if (cancelPending()) {
                Cancelling&hellip;
              } @else {
                Cancel plan
              }
            </button>
          }
        </div>
      </div>
    }
  `,
})
export class AccountBillingComponent implements OnInit {
  // ── Service injections ────────────────────────────────────────────────────
  protected readonly auth     = inject(AuthService);
  private readonly billing    = inject(BillingApiService);
  private readonly confirm    = inject(MeeConfirmService);
  private readonly toast      = inject(MeeToastService);

  // ── State signals ─────────────────────────────────────────────────────────

  readonly loading            = signal(true);
  readonly subscription       = signal<BillingSubscriptionResponse | null>(null);
  readonly billingUnavailable = signal(false);
  readonly errorMessage       = signal('');
  readonly cancelPending      = signal(false);

  /** True when the user is on the free plan (no paid subscription). */
  readonly isFree = computed(() => {
    const sub = this.subscription();
    if (!sub) return true;
    return sub.entitlement === 'free' && !sub.trial_ends_at;
  });

  /** Show upgrade CTA for starter/pro (not business, not LTD). */
  readonly showUpgradeCTA = computed(() => {
    const sub = this.subscription();
    if (!sub) return false;
    return sub.entitlement === 'starter' || sub.entitlement === 'pro';
  });

  /** Show cancel CTA only when: plan !== 'ltd' && !cancel_scheduled. */
  readonly showCancelCTA = computed(() => {
    const sub = this.subscription();
    if (!sub) return false;
    if (sub.plan === 'ltd') return false;
    if (sub.cancel_scheduled) return false;
    if (sub.entitlement === 'free' && !sub.trial_ends_at) return false;
    return true;
  });

  /** Human-readable entitlement label. */
  readonly entitlementLabel = computed(() => {
    const sub = this.subscription();
    if (!sub) return '';
    const map: Record<string, string> = {
      free: 'Free',
      starter: 'Starter',
      pro: 'Pro',
      business: 'Business',
    };
    return map[sub.entitlement] ?? sub.entitlement;
  });

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  ngOnInit(): void {
    this._loadSubscription();
  }

  // ── Action methods ────────────────────────────────────────────────────────

  /**
   * Open the MeeConfirmService confirm dialog for cancellation.
   * The dialog is a PrimeNG ConfirmDialog hosted in the shell template.
   * LTD plans bypass this (button hidden in template; guard here as defence).
   */
  openCancelConfirm(): void {
    if (this.subscription()?.plan === 'ltd') {
      // Defensive guard — button should be hidden, but handle the race.
      this.toast.info(BILLING_STRINGS['billing.subscription.none_active']);
      return;
    }

    const entitledUntil = this.subscription()?.current_period_end;
    const message = entitledUntil
      ? `Your plan stays active until ${new Date(entitledUntil).toLocaleDateString()}. Cancel anyway?`
      : 'Cancel your current subscription? Your access continues until the end of the billing period.';

    this.confirm.confirm({
      header: 'Cancel subscription',
      message,
      accept: () => this.confirmCancel(),
      reject: () => {/* dismiss — no-op */},
    });
  }

  /** Confirmed cancel — POST /billing/cancel. */
  confirmCancel(): void {
    this.cancelPending.set(true);
    this.errorMessage.set('');

    this.billing.cancel().subscribe({
      next: () => {
        this.cancelPending.set(false);
        this.toast.info(BILLING_STRINGS['billing.cancel_scheduled'], 'Cancellation scheduled');
        // Refresh subscription to show cancel_scheduled badge.
        this._loadSubscription();
        // Re-hydrate auth user (entitlement unchanged until period_end).
        this.auth.refreshUser().subscribe();
      },
      error: (err: BillingErrorShape) => {
        this.cancelPending.set(false);
        this._handleCancelError(err);
      },
    });
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
        if (err.kind === 'billing_error' && err.status === 404) {
          // FEATURE_BILLING_ENABLED off — degrade gracefully (no error toast).
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
      (err.code === 'billing.subscription.none_active' ||
        err.status === 404 || err.status === 409)
    ) {
      // LTD-perpetual or no active subscription — informational, not alarming.
      this.toast.info(BILLING_STRINGS['billing.subscription.none_active'], 'Nothing to cancel');
      this._loadSubscription();
    } else if (err.kind === 'provider_unavailable') {
      this.errorMessage.set(BILLING_STRINGS['billing.provider_unavailable']);
    } else {
      this.errorMessage.set(BILLING_STRINGS['billing.generic_error']);
    }
  }
}

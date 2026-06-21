/**
 * PlanCardComponent — one tier card for the Plans page.
 *
 * Inputs:
 *   tier: TierDisplay — the pricing/feature data for this tier
 *   currentEntitlement: EntitlementLiteral — the user's current effective entitlement
 *   isInitiating: boolean — true when this tier's checkout is in the 'initiating' state
 *
 * Outputs:
 *   subscribe: EventEmitter<SubscribableTier> — emitted when the CTA is clicked
 *
 * CTA label logic (per WAVE5_FRONTEND_TASKSPEC §6 + D-FE5):
 *   - tier.tier === 'free' → no CTA (free tier is never subscribable)
 *   - tier.entitlement === currentEntitlement → "Your current plan"
 *   - tier entitlement rank < current → hidden (D-FE5: hide downgrades)
 *   - otherwise → "Upgrade to <name>" / "Switch to <name>" / "Get Lifetime"
 */

import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
  computed,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import type { TierDisplay } from '../billing.constants';
import type { SubscribableTier, EntitlementLiteral } from '../billing.model';

/** Entitlement rank for upgrade/downgrade logic. */
const ENTITLEMENT_RANK: Record<EntitlementLiteral, number> = {
  free: 0,
  starter: 1,
  pro: 2,
  business: 3,
};

@Component({
  selector: 'app-plan-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; }

    .plan-card {
      position: relative;
      display: flex;
      flex-direction: column;
      border: 2px solid var(--mee-color-outline-variant, #e0e0e0);
      border-radius: var(--mee-radius-lg, 12px);
      padding: var(--mee-space-5, 20px);
      background: var(--mee-color-surface, #fff);
      transition: box-shadow 0.2s ease;
      height: 100%;
    }
    .plan-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.10);
    }
    .plan-card--current {
      border-color: var(--mee-color-primary, #F26B23);
      background: rgba(242,107,35,0.03);
    }

    .plan-card__badge {
      position: absolute;
      top: -12px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--mee-color-primary, #F26B23);
      color: #fff;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: var(--mee-radius-full, 999px);
      white-space: nowrap;
    }

    .plan-card__name {
      font-size: 18px;
      font-weight: 700;
      color: var(--mee-color-on-surface, #2a3547);
      margin: 0 0 var(--mee-space-2, 8px);
    }

    .plan-card__price-row {
      display: flex;
      align-items: baseline;
      gap: var(--mee-space-1, 4px);
      margin-bottom: var(--mee-space-1, 4px);
    }
    .plan-card__price {
      font-size: 32px;
      font-weight: 800;
      color: var(--mee-color-on-surface, #2a3547);
    }
    .plan-card__period {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted, #5a6a85);
    }
    .plan-card__annual-note {
      font-size: 12px;
      color: var(--mee-color-on-surface-muted, #5a6a85);
      margin: 0 0 var(--mee-space-3, 12px);
    }

    .plan-card__features {
      list-style: none;
      margin: var(--mee-space-3, 12px) 0;
      padding: 0;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2, 8px);
    }
    .plan-card__feature {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted, #5a6a85);
      display: flex;
      align-items: flex-start;
      gap: var(--mee-space-2, 8px);
    }
    .plan-card__feature-check {
      color: var(--mee-color-success, #16A34A);
      font-size: 14px;
      flex-shrink: 0;
      margin-top: 1px;
    }

    .plan-card__cta {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      width: 100%;
      padding: 0 var(--mee-space-4, 16px);
      margin-top: var(--mee-space-4, 16px);
      border-radius: var(--mee-radius-md, 8px);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.15s ease, background 0.15s ease;
      border: none;
      text-align: center;
    }
    .plan-card__cta--upgrade {
      background: var(--mee-color-primary, #F26B23);
      color: #fff;
    }
    .plan-card__cta--upgrade:hover { opacity: 0.9; }
    .plan-card__cta--current {
      background: var(--mee-color-surface-variant, #f2f6fa);
      color: var(--mee-color-primary, #F26B23);
      cursor: default;
      border: 1px solid var(--mee-color-primary-light, rgba(242,107,35,0.12));
    }
    .plan-card__cta:disabled { opacity: 0.6; cursor: not-allowed; }

    /* prefers-reduced-motion: disable card hover + CTA transitions */
    @media (prefers-reduced-motion: reduce) {
      .plan-card { transition: none; }
      .plan-card__cta { transition: none; }
    }

    /* Mobile ≤479px: badge stacking safety — badge may clip above card at 360px if card
       has no top margin. Add padding-top to give the absolutely-positioned badge room. */
    .plan-card {
      margin-top: 14px; /* room for the absolute-positioned badge (-12px from top) */
    }
  `],
  template: `
    <div
      class="plan-card"
      [class.plan-card--current]="isCurrent()"
      [attr.aria-label]="tier.name + ' plan'"
    >
      <!-- Badge (Most Popular / Best Value / Limited spots etc.) -->
      @if (tier.badge) {
        <span class="plan-card__badge" aria-label="Badge: {{ tier.badge }}">
          {{ tier.badge }}
        </span>
      }

      <!-- Tier name -->
      <h2 class="plan-card__name">{{ tier.name }}</h2>

      <!-- Price -->
      <div class="plan-card__price-row">
        @if (tier.priceMonthly === 0) {
          <span class="plan-card__price">Free</span>
        } @else if (tier.isOneTime) {
          <span class="plan-card__price">&#x20B9;{{ tier.priceMonthly | number }}</span>
          <span class="plan-card__period">one-time</span>
        } @else if (tier.priceAnnual) {
          <span class="plan-card__price">&#x20B9;{{ tier.priceAnnual | number }}</span>
          <span class="plan-card__period">{{ tier.periodLabel }}</span>
        } @else {
          <span class="plan-card__price">&#x20B9;{{ tier.priceMonthly | number }}</span>
          <span class="plan-card__period">{{ tier.periodLabel }}</span>
        }
      </div>

      <!-- Annual equivalent note -->
      @if (tier.priceAnnual && !tier.isOneTime) {
        <p class="plan-card__annual-note">
          (&#x20B9;{{ tier.priceMonthly }}/mo equivalent &bull; save 2 months)
        </p>
      }

      <!-- Feature list -->
      <ul class="plan-card__features" aria-label="{{ tier.name }} features">
        @for (feature of tier.features; track feature) {
          <li class="plan-card__feature">
            <span class="plan-card__feature-check" aria-hidden="true">&#x2713;</span>
            {{ feature }}
          </li>
        }
      </ul>

      <!-- CTA -->
      @if (tier.tier !== 'free') {
        @if (isCurrent()) {
          <button
            class="plan-card__cta plan-card__cta--current"
            type="button"
            disabled
            aria-label="Your current plan: {{ tier.name }}"
          >
            Your current plan
          </button>
        } @else if (isUpgrade()) {
          <button
            class="plan-card__cta plan-card__cta--upgrade"
            type="button"
            data-testid="upgrade-prompt"
            [disabled]="isInitiating"
            (click)="onCTAClick()"
            [attr.aria-label]="ctaLabel() + ': ' + tier.name"
            [attr.aria-busy]="isInitiating ? 'true' : null"
          >
            @if (isInitiating) {
              Opening payment&hellip;
            } @else {
              {{ ctaLabel() }}
            }
          </button>
        }
        <!-- downgrade CTAs hidden per D-FE5 -->
      }
    </div>
  `,
})
export class PlanCardComponent {
  @Input({ required: true }) tier!: TierDisplay;
  @Input() currentEntitlement: EntitlementLiteral = 'free';
  @Input() isInitiating = false;

  /** Emitted when the upgrade CTA is clicked. */
  @Output() subscribe = new EventEmitter<SubscribableTier>();

  /** True when this tier's entitlement matches the user's current entitlement. */
  isCurrent(): boolean {
    return this.tier.entitlement === this.currentEntitlement;
  }

  /**
   * True when this tier represents an upgrade from the current entitlement.
   * Downgrade CTAs are hidden per D-FE5.
   */
  isUpgrade(): boolean {
    if (this.tier.tier === 'free') return false;
    const tierRank = ENTITLEMENT_RANK[this.tier.entitlement] ?? 0;
    const currentRank = ENTITLEMENT_RANK[this.currentEntitlement] ?? 0;
    return tierRank > currentRank;
  }

  /** CTA button label. */
  ctaLabel(): string {
    if (this.tier.isOneTime) return 'Get Lifetime';
    if (this.currentEntitlement === 'free') return `Upgrade to ${this.tier.name}`;
    return `Switch to ${this.tier.name}`;
  }

  onCTAClick(): void {
    if (this.tier.tier !== 'free') {
      this.subscribe.emit(this.tier.tier as SubscribableTier);
    }
  }
}

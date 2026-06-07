// features/pricing/pnl-breakdown/pnl-breakdown.component.ts
// Selector: mee-pnl-breakdown
// Renders P&L line-item breakdown table for a PricingCalc result

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { InrCurrencyPipe } from '@shared/pipes/inr-currency.pipe';
import { PricingCalc } from '../pricing-api.service';

@Component({
  selector: 'mee-pnl-breakdown',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [InrCurrencyPipe, DecimalPipe],
  styles: [`
    :host { display: block; }
    .pnl-table {
      width: 100%;
      border-collapse: collapse;
    }
    .pnl-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 9px 0;
      font-size: 14px;
      border-bottom: 1px solid var(--mee-color-bg);
    }
    .pnl-row:last-child {
      border-bottom: none;
    }
    .pnl-label {
      color: var(--mee-color-on-surface);
    }
    .pnl-value-neutral {
      color: var(--mee-color-on-surface);
      font-weight: 500;
    }
    .pnl-value-deduction {
      color: var(--mee-color-error);
    }
    .pnl-divider {
      border: none;
      border-top: 2px solid var(--mee-color-on-surface);
      margin: 6px 0;
    }
    .pnl-row-total {
      font-weight: 700;
      font-size: 15px;
      padding: 10px 0 6px;
    }
    .pnl-payout-positive {
      color: var(--mee-color-success);
    }
    .pnl-payout-zero {
      color: var(--mee-color-on-surface);
    }
    .pnl-margin-positive {
      color: var(--mee-color-success);
    }
    .pnl-margin-warning {
      color: #D97706; /* amber — no semantic token */
    }
    .pnl-margin-negative {
      color: var(--mee-color-error);
    }
  `],
  template: `
    <div role="table" aria-label="Pricing breakdown">
      <!-- MRP row -->
      <div class="pnl-row" role="row">
        <span class="pnl-label" role="cell">MRP</span>
        <span class="pnl-value-neutral" role="cell">{{ calc().mrp | inrCurrency }}</span>
      </div>

      <!-- Commission row -->
      <div class="pnl-row" role="row">
        <span class="pnl-label" role="cell">Commission ({{ calc().commission_pct }}%)</span>
        <span class="pnl-value-deduction" role="cell">-{{ calc().commission | inrCurrency }}</span>
      </div>

      <!-- GST row -->
      <div class="pnl-row" role="row">
        <span class="pnl-label" role="cell">GST ({{ calc().gst_pct }}%)</span>
        <span class="pnl-value-deduction" role="cell">-{{ calc().gst | inrCurrency }}</span>
      </div>

      <!-- Platform fee row -->
      <div class="pnl-row" role="row">
        <span class="pnl-label" role="cell">Platform fee ({{ calc().platform_fee_pct }}%)</span>
        <span class="pnl-value-deduction" role="cell">-{{ calc().platform_fee | inrCurrency }}</span>
      </div>

      <!-- Logistics row -->
      <div class="pnl-row" role="row">
        <span class="pnl-label" role="cell">Logistics</span>
        <span class="pnl-value-deduction" role="cell">-{{ calc().logistics_deduction | inrCurrency }}</span>
      </div>

      <hr class="pnl-divider" aria-hidden="true" />

      <!-- Seller payout row -->
      <div class="pnl-row pnl-row-total" role="row">
        <span class="pnl-label" role="cell">Your payout</span>
        <span
          [class]="payoutClass()"
          role="cell"
          [attr.aria-label]="'Your payout: ' + (calc().seller_payout | inrCurrency)"
        >
          {{ calc().seller_payout | inrCurrency }}
        </span>
      </div>

      <!-- Net margin row -->
      <div class="pnl-row" role="row">
        <span class="pnl-label" role="cell">Net margin</span>
        <span
          [class]="marginClass()"
          role="cell"
          [attr.aria-label]="'Net margin: ' + calc().net_margin_pct + '%'"
        >
          {{ calc().net_margin_pct | number:'1.1-1' }}%
        </span>
      </div>
    </div>
  `,
})
export class PnlBreakdownComponent {
  readonly calc = input.required<PricingCalc>();

  readonly payoutClass = computed<string>(() => {
    return this.calc().seller_payout > 0 ? 'pnl-payout-positive' : 'pnl-payout-zero';
  });

  readonly marginClass = computed<string>(() => {
    const pct = this.calc().net_margin_pct;
    if (pct >= 15) return 'pnl-margin-positive';
    if (pct < 0) return 'pnl-margin-negative';
    return 'pnl-margin-warning';
  });
}

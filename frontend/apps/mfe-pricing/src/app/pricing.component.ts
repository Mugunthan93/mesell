/**
 * pricing.component.ts — PricingComponent (§12.M forward estimator, 2026-06-18).
 *
 * Route: /catalogs/:id/pricing
 * MFE:   mfe-pricing (standalone bootstrap + federated via shell)
 *
 * CONTRACT (§12.M):
 *   Request primary:  meesho_price (listed selling price) — seller enters this.
 *   Request inputs:   input_cost (required), commission_pct (default 4%), return_rate_pct (default 0%).
 *   Request display:  mrp (optional struck-through reference).
 *   Response hero:    estimated_payout ("You pocket ₹X").
 *   Response 3-price: mrp (null → "—") | meesho_price | wdrp_price.
 *   Response deductions table: referral_commission, shipping_charge, logistics_fee,
 *     fixed_fee, gst_on_fees, tcs, tds, rto_expected_loss → total_deductions.
 *   Response ratios:  margin_pct (% of meesho_price), markup_pct (% of input_cost).
 *   Alerts (server):  NEGATIVE_PAYOUT→error, LOW_MARGIN→warning, SHIPPING_DOMINATES→info.
 *
 * DECISIONS:
 *   DECISION-1: No local P&L math — server-calc only (R-W6-1, ruled 2026-06-11).
 *   DECISION-2: Live recalc via form.valueChanges → debounceTime(350) → switchMap(calc).
 *               "Calculate" button is kept as explicit fallback + a11y affordance.
 *   DECISION-3: estimated_payout drives hero + positive/negative badge; profit drives
 *               marginIsPositive (both are in the response; profit = payout - input_cost).
 *
 * DELETED vs §12.E component:
 *   - target_margin_pct form control (request field removed in §12.M)
 *   - targetMarginError() signal
 *   - commission_missing error state + commissionMissingDetail signal (422 dead §12.M (4))
 *   - _handleErrorShape 'commission_missing' case
 *   - "Shipping not included in V1" disclaimer (shipping NOW in deduction breakdown)
 *   - MRP as an output field only (§12.M: MRP is optional request input + echoed in response)
 */

import {
  AfterViewChecked,
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  OnInit,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs';

import { MeeAlertBannerComponent }  from '@mesell/composites';
import { MeeOfflineBannerComponent } from '@mesell/composites';
import { PageHeaderComponent }       from '@mesell/composites';
import { MeeBadgeComponent }         from '@mesell/ui-kit';
import { MeeButtonComponent }        from '@mesell/ui-kit';
import { MeeCardComponent }          from '@mesell/ui-kit';
import { MeeInputComponent }         from '@mesell/ui-kit';

import { formatRupee, parseDecimal } from './pricing.utils';
import { PricingApiService }         from './pricing.service';
import type { PriceCalcRequest, PriceCalcResponse, PriceCalcErrorShape } from './pricing.model';
import { ALERT_MESSAGES } from './pricing.model';

// ── Error-state type (§3.1 degradation matrix) ──────────────────────────────
// null          = initial / cleared
// unavailable   = 404 (flag-off or product not found)
// validation    = 400 (Pydantic constraint violation)
// server_error  = 5xx / network error
// commission_missing DELETED — 422 path dead in §12.M (4)
export type PricingErrorState =
  | 'unavailable'
  | 'validation'
  | 'server_error'
  | null;

// ── Alert code → MeeAlertBanner variant mapping ──────────────────────────────
// NEGATIVE_PAYOUT → error (red); LOW_MARGIN → warning (amber); SHIPPING_DOMINATES → info
type AlertVariant = 'error' | 'warning' | 'info';
const ALERT_VARIANT_MAP: Record<string, AlertVariant> = {
  NEGATIVE_PAYOUT:    'error',
  LOW_MARGIN:         'warning',
  SHIPPING_DOMINATES: 'info',
};

@Component({
  selector: 'app-pricing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [PricingApiService],
  imports: [
    ReactiveFormsModule,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
    PageHeaderComponent,
    MeeBadgeComponent,
    MeeButtonComponent,
    MeeCardComponent,
    MeeInputComponent,
  ],

  // ─── Component-scoped CSS ─────────────────────────────────────────────────
  // All values use var(--mee-*) tokens. Zero hardcoded hex (lane guard).
  // --mee-color-surface-variant not in Layer 1 — local scope bridge only.
  styles: [`
    :host {
      --mee-color-surface-variant: #f2f6fa;
    }

    /* ── Spinner ────────────────────────────────────────────────────────── */
    /* MeeSpinnerComponent is a queued ui-kit amendment (NOT yet available).
       Local spinner bridge used until the ui-kit component lands. */
    .mee-pricing__spinner {
      display: inline-block;
      width: 32px;
      height: 32px;
      border: 3px solid var(--mee-color-outline);
      border-top-color: var(--mee-color-primary);
      border-radius: 50%;
      animation: mee-pricing-spin 0.8s linear infinite;
    }

    @media (prefers-reduced-motion: reduce) {
      .mee-pricing__spinner {
        animation: mee-pricing-fade 1.2s ease-in-out infinite;
        border-top-color: var(--mee-color-primary);
      }
    }

    @keyframes mee-pricing-spin {
      to { transform: rotate(360deg); }
    }

    @keyframes mee-pricing-fade {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.35; }
    }

    /* ── Hero payout card ───────────────────────────────────────────────── */
    .mee-pricing__hero {
      padding: var(--mee-space-4);
      border-radius: var(--mee-radius-md);
      text-align: center;
    }

    .mee-pricing__hero--positive {
      background: color-mix(in srgb, var(--mee-color-success) 10%, transparent);
      border: 1px solid var(--mee-color-success);
    }

    .mee-pricing__hero--negative {
      background: color-mix(in srgb, var(--mee-color-error) 10%, transparent);
      border: 1px solid var(--mee-color-error);
    }

    .mee-pricing__hero-label {
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--mee-color-on-surface-muted);
      margin-bottom: var(--mee-space-1);
    }

    .mee-pricing__hero-amount {
      font-size: 2rem;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
      line-height: 1.1;
    }

    .mee-pricing__hero-amount--positive {
      color: var(--mee-color-success);
    }

    .mee-pricing__hero-amount--negative {
      color: var(--mee-color-error);
    }

    .mee-pricing__hero-wdrp {
      font-size: 0.75rem;
      color: var(--mee-color-on-surface-muted);
      margin-top: var(--mee-space-1);
    }

    /* ── 3-price strip ──────────────────────────────────────────────────── */
    .mee-pricing__price-strip {
      display: flex;
      gap: var(--mee-space-3);
      justify-content: space-between;
      padding: var(--mee-space-3) 0;
      border-top: 1px solid var(--mee-color-outline);
      border-bottom: 1px solid var(--mee-color-outline);
    }

    .mee-pricing__price-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      flex: 1;
      gap: 2px;
    }

    .mee-pricing__price-item-label {
      font-size: 0.6875rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--mee-color-on-surface-muted);
    }

    .mee-pricing__price-item-value {
      font-size: 0.9375rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      color: var(--mee-color-on-surface);
    }

    .mee-pricing__price-item-value--null {
      color: var(--mee-color-on-surface-muted);
    }

    /* ── Secondary ratios row (margin + markup) ─────────────────────────── */
    .mee-pricing__ratios {
      display: flex;
      gap: var(--mee-space-4);
      padding: var(--mee-space-2) 0;
    }

    .mee-pricing__ratio-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .mee-pricing__ratio-label {
      font-size: 0.6875rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--mee-color-on-surface-muted);
    }

    .mee-pricing__ratio-value {
      font-size: 0.875rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      color: var(--mee-color-on-surface);
    }

    /* ── Deduction breakdown table ──────────────────────────────────────── */
    .mee-pricing__table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }

    .mee-pricing__table td {
      padding: var(--mee-space-2) 0;
      vertical-align: middle;
    }

    .mee-pricing__table-label {
      color: var(--mee-color-on-surface-muted);
      text-align: left;
    }

    .mee-pricing__table-value {
      color: var(--mee-color-on-surface);
      text-align: right;
      font-variant-numeric: tabular-nums;
      font-weight: 500;
      white-space: nowrap;
    }

    .mee-pricing__row {
      border-bottom: 1px solid var(--mee-color-outline);
    }

    .mee-pricing__row--total {
      border-top: 2px solid var(--mee-color-outline);
      border-bottom: none;
    }

    .mee-pricing__row--total .mee-pricing__table-label {
      color: var(--mee-color-on-surface);
      font-weight: 700;
    }

    .mee-pricing__row--total .mee-pricing__table-value {
      font-weight: 700;
    }

    .mee-pricing__value--positive {
      color: var(--mee-color-success) !important;
    }

    .mee-pricing__value--negative {
      color: var(--mee-color-error) !important;
    }

    @media (max-width: 400px) {
      .mee-pricing__table-label {
        max-width: 140px;
        word-break: break-word;
      }
      .mee-pricing__table {
        font-size: 0.8125rem;
      }
    }

    /* ── Empty / first-visit state ──────────────────────────────────────── */
    .mee-pricing__empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: var(--mee-space-10) var(--mee-space-4);
      gap: var(--mee-space-3);
      text-align: center;
    }

    .mee-pricing__empty-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: var(--mee-color-primary-light);
      color: var(--mee-color-primary);
      font-size: 1.25rem;
    }

    .mee-pricing__empty-title {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--mee-color-on-surface);
    }

    .mee-pricing__empty-hint {
      font-size: 0.8125rem;
      color: var(--mee-color-on-surface-muted);
    }

    /* ── Form layout ────────────────────────────────────────────────────── */
    .mee-pricing__form {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
      padding: var(--mee-space-3);
    }

    /* ── Result region wrapper ──────────────────────────────────────────── */
    .mee-pricing__result-region {
      outline: none;
    }

    /* ── Calculating state ──────────────────────────────────────────────── */
    .mee-pricing__calculating {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--mee-space-3);
      padding: var(--mee-space-10) 0;
    }

    .mee-pricing__calculating-label {
      font-size: 0.875rem;
      color: var(--mee-color-on-surface-muted);
    }

    /* ── Section headings ───────────────────────────────────────────────── */
    .mee-pricing__section-title {
      font-size: 0.9375rem;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin-bottom: var(--mee-space-1);
    }

    /* ── Results footer badges + alerts ─────────────────────────────────── */
    .mee-pricing__results-footer {
      padding-top: var(--mee-space-3);
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
    }

    /* ── 44px touch targets ─────────────────────────────────────────────── */
    .mee-pricing__calculate-area {
      min-height: 44px;
    }
  `],

  template: `
    <div class="max-w-5xl mx-auto px-4 py-6 space-y-6">

      <!-- Offline banner (R-W6-1 degradation matrix) -->
      <mee-offline-banner />

      <mee-page-header
        title="Price Calculator"
        subtitle="Enter your selling price to estimate your net payout"
      />

      <div class="flex flex-col gap-6 lg:flex-row lg:items-start">

        <!-- INPUT SECTION -->
        <div class="lg:w-2/5">
          <mee-card>
            <form
              [formGroup]="form"
              aria-label="Pricing calculation form"
              class="mee-pricing__form"
            >
              <h2 class="mee-pricing__section-title">Enter pricing details</h2>

              <!-- Meesho Price: primary forward-estimator input (§12.M) -->
              <mee-input
                label="Meesho Price (selling price)"
                type="number"
                prefix="&#8377;"
                placeholder="e.g. 499"
                formControlName="meesho_price"
                [error]="meeshoPriceError()"
              />

              <!-- Input cost (COGS per unit) -->
              <mee-input
                label="Input cost (COGS per unit)"
                type="number"
                prefix="&#8377;"
                placeholder="e.g. 300"
                formControlName="input_cost"
                [error]="inputCostError()"
              />

              <!-- Referral commission % — seller-entered, default 4% -->
              <mee-input
                label="Referral commission %"
                type="number"
                suffix="%"
                placeholder="e.g. 4"
                formControlName="commission_pct"
                [error]="commissionPctError()"
              />

              <!-- Expected return rate % (RTO) — optional, default 0% -->
              <mee-input
                label="Expected return rate % (RTO)"
                type="number"
                suffix="%"
                placeholder="e.g. 0"
                formControlName="return_rate_pct"
                [error]="returnRatePctError()"
              />

              <!-- MRP reference — optional display-only, does not drive payout -->
              <mee-input
                label="MRP (reference)"
                type="number"
                prefix="&#8377;"
                placeholder="Optional struck-through price"
                formControlName="mrp"
                [error]="mrpError()"
              />

              <!-- Explicit Calculate button (a11y fallback; live recalc via valueChanges) -->
              <div class="mee-pricing__calculate-area">
                <mee-button
                  label="Calculate"
                  variant="primary"
                  [fullWidth]="true"
                  [disabled]="form.invalid || calculating()"
                  (clicked)="onCalculate()"
                />
              </div>
            </form>
          </mee-card>
        </div>

        <!-- RESULTS + ERROR STATES -->
        <div class="lg:w-3/5">
          <mee-card>
            <div class="p-3 space-y-4">
              <h2 class="mee-pricing__section-title">Your payout estimate</h2>

              <!--
                Error banners: role="alert" + aria-live="assertive" handled inside
                MeeAlertBannerComponent. Focus shifts to #resultRegion after any
                state transition via _focusPending (AfterViewChecked).
              -->

              <!-- 404 — flag off or product not found. NO local math (DECISION-1). -->
              @if (errorState() === 'unavailable') {
                <mee-alert-banner
                  variant="error"
                  message="Price Calculator is unavailable. Please try again later or contact support."
                />
              }

              <!-- 400 — Pydantic constraint violation (form validators prevent most) -->
              @if (errorState() === 'validation') {
                <mee-alert-banner
                  variant="warning"
                  [message]="validationDetail()"
                />
              }

              <!-- 5xx / network — manual re-submit (§3.2) -->
              @if (errorState() === 'server_error') {
                <mee-alert-banner
                  variant="error"
                  message="Couldn't calculate price — please try again."
                />
              }

              <!--
                Calculating spinner.
                FLAG: replace .mee-pricing__spinner with <mee-spinner /> when ui-kit amendment lands.
                prefers-reduced-motion: CSS @media switches animation → opacity pulse.
              -->
              @if (calculating()) {
                <div
                  role="status"
                  aria-live="polite"
                  aria-label="Calculating price, please wait"
                  class="mee-pricing__calculating"
                >
                  <span class="mee-pricing__spinner" aria-hidden="true"></span>
                  <span class="mee-pricing__calculating-label">Calculating…</span>
                </div>
              }

              <!--
                Results region.
                tabindex="-1" + programmatic focus after calc (AfterViewChecked → _focusPending).
                aria-live="polite" announces new results to screen readers.
              -->
              <div
                #resultRegion
                class="mee-pricing__result-region"
                tabindex="-1"
                role="region"
                aria-label="Pricing results"
                aria-live="polite"
                aria-atomic="false"
              >

                @if (breakdown()) {

                  <!-- HERO: estimated_payout — "You pocket ₹X" -->
                  <div
                    class="mee-pricing__hero"
                    [class.mee-pricing__hero--positive]="payoutIsPositive()"
                    [class.mee-pricing__hero--negative]="!payoutIsPositive()"
                    aria-label="Net payout"
                  >
                    <p class="mee-pricing__hero-label">You pocket</p>
                    <p
                      class="mee-pricing__hero-amount"
                      [class.mee-pricing__hero-amount--positive]="payoutIsPositive()"
                      [class.mee-pricing__hero-amount--negative]="!payoutIsPositive()"
                      [attr.aria-label]="'Estimated payout: ' + formatRupeeLabel(breakdown()!.estimated_payout) + (payoutIsPositive() ? ', positive' : ', negative')"
                    >
                      {{ formatRupeeLabel(breakdown()!.estimated_payout) }}
                    </p>
                    <p class="mee-pricing__hero-wdrp">
                      If returned defective, you'd get
                      <strong>{{ formatRupeeLabel(breakdown()!.estimated_payout_wdrp) }}</strong>
                    </p>
                  </div>

                  <!-- 3-PRICE STRIP: MRP (or —) · Meesho Price · WDRP -->
                  <div class="mee-pricing__price-strip" aria-label="Price breakdown">
                    <div class="mee-pricing__price-item">
                      <span class="mee-pricing__price-item-label">MRP</span>
                      <span
                        class="mee-pricing__price-item-value"
                        [class.mee-pricing__price-item-value--null]="!breakdown()!.mrp"
                      >
                        {{ breakdown()!.mrp ? formatRupeeLabel(breakdown()!.mrp!) : '—' }}
                      </span>
                    </div>
                    <div class="mee-pricing__price-item">
                      <span class="mee-pricing__price-item-label">Meesho Price</span>
                      <span class="mee-pricing__price-item-value">
                        {{ formatRupeeLabel(breakdown()!.meesho_price) }}
                      </span>
                    </div>
                    <div class="mee-pricing__price-item">
                      <span class="mee-pricing__price-item-label">WDRP</span>
                      <span class="mee-pricing__price-item-value">
                        {{ formatRupeeLabel(breakdown()!.wdrp_price) }}
                      </span>
                    </div>
                  </div>

                  <!-- SECONDARY RATIOS: Margin (% of meesho_price) · Markup (% of input_cost) -->
                  <div class="mee-pricing__ratios">
                    <div class="mee-pricing__ratio-item">
                      <span class="mee-pricing__ratio-label">Margin</span>
                      <span
                        class="mee-pricing__ratio-value"
                        [class.mee-pricing__value--positive]="marginIsPositive()"
                        [class.mee-pricing__value--negative]="!marginIsPositive()"
                      >
                        {{ breakdown()!.margin_pct }}%
                      </span>
                    </div>
                    <div class="mee-pricing__ratio-item">
                      <span class="mee-pricing__ratio-label">Markup</span>
                      <span
                        class="mee-pricing__ratio-value"
                        [class.mee-pricing__value--positive]="marginIsPositive()"
                        [class.mee-pricing__value--negative]="!marginIsPositive()"
                      >
                        {{ breakdown()!.markup_pct }}%
                      </span>
                    </div>
                  </div>

                  <!-- DEDUCTION BREAKDOWN TABLE: "Where my money goes" -->
                  <div>
                    <h3 class="mee-pricing__section-title" style="font-size: 0.8125rem; margin-top: var(--mee-space-3)">
                      Where your money goes
                    </h3>
                    <table
                      class="mee-pricing__table"
                      aria-label="P&L breakdown"
                    >
                      <thead class="sr-only">
                        <tr>
                          <th scope="col">Item</th>
                          <th scope="col">Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr class="mee-pricing__row">
                          <td class="mee-pricing__table-label" scope="row">
                            Referral commission ({{ breakdown()!.commission_pct }}%)
                          </td>
                          <td class="mee-pricing__table-value">
                            {{ formatRupeeLabel(breakdown()!.referral_commission) }}
                          </td>
                        </tr>
                        <tr class="mee-pricing__row">
                          <td class="mee-pricing__table-label" scope="row">Shipping charge</td>
                          <td class="mee-pricing__table-value">
                            {{ formatRupeeLabel(breakdown()!.shipping_charge) }}
                          </td>
                        </tr>
                        <tr class="mee-pricing__row">
                          <td class="mee-pricing__table-label" scope="row">Logistics fee</td>
                          <td class="mee-pricing__table-value">
                            {{ formatRupeeLabel(breakdown()!.logistics_fee) }}
                          </td>
                        </tr>
                        <tr class="mee-pricing__row">
                          <td class="mee-pricing__table-label" scope="row">Fixed fee</td>
                          <td class="mee-pricing__table-value">
                            {{ formatRupeeLabel(breakdown()!.fixed_fee) }}
                          </td>
                        </tr>
                        <tr class="mee-pricing__row">
                          <td class="mee-pricing__table-label" scope="row">
                            GST on fees ({{ breakdown()!.gst_pct }}%)
                          </td>
                          <td class="mee-pricing__table-value">
                            {{ formatRupeeLabel(breakdown()!.gst_on_fees) }}
                          </td>
                        </tr>
                        <tr class="mee-pricing__row">
                          <td class="mee-pricing__table-label" scope="row">TCS</td>
                          <td class="mee-pricing__table-value">
                            {{ formatRupeeLabel(breakdown()!.tcs) }}
                          </td>
                        </tr>
                        <tr class="mee-pricing__row">
                          <td class="mee-pricing__table-label" scope="row">TDS</td>
                          <td class="mee-pricing__table-value">
                            {{ formatRupeeLabel(breakdown()!.tds) }}
                          </td>
                        </tr>
                        <tr class="mee-pricing__row">
                          <td class="mee-pricing__table-label" scope="row">
                            RTO expected loss ({{ breakdown()!.return_rate_pct }}%)
                          </td>
                          <td class="mee-pricing__table-value">
                            {{ formatRupeeLabel(breakdown()!.rto_expected_loss) }}
                          </td>
                        </tr>
                        <!-- Total deductions — bold summary row -->
                        <tr class="mee-pricing__row--total">
                          <td class="mee-pricing__table-label" scope="row">Total deductions</td>
                          <td class="mee-pricing__table-value">
                            {{ formatRupeeLabel(breakdown()!.total_deductions) }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <!-- POSITIVE / NEGATIVE badge + server alerts -->
                  <div class="mee-pricing__results-footer">
                    <div class="flex items-center gap-2">
                      <mee-badge
                        [value]="payoutIsPositive() ? 'POSITIVE' : 'NEGATIVE'"
                        [severity]="payoutIsPositive() ? 'success' : 'danger'"
                      />
                    </div>

                    <!--
                      Server-issued alert banners via MeeAlertBannerComponent.
                      NEGATIVE_PAYOUT → error (red)
                      LOW_MARGIN      → warning (amber)
                      SHIPPING_DOMINATES → info
                      Copy resolved from ALERT_MESSAGES[message_id] ?? message_id.
                    -->
                    @if (breakdown()!.alerts.length > 0) {
                      <div role="list" aria-label="Pricing alerts" class="flex flex-col gap-2">
                        @for (alert of breakdown()!.alerts; track alert.code) {
                          <div role="listitem">
                            <mee-alert-banner
                              [variant]="resolveAlertVariant(alert.code)"
                              [message]="resolveAlertMessage(alert.message_id)"
                            />
                          </div>
                        }
                      </div>
                    }

                  </div>

                } @else if (!calculating() && !errorState()) {

                  <!-- Empty / first-visit state -->
                  <div class="mee-pricing__empty" aria-label="No results yet">
                    <div class="mee-pricing__empty-icon" aria-hidden="true">&#8377;</div>
                    <p class="mee-pricing__empty-title">Ready to calculate</p>
                    <p class="mee-pricing__empty-hint">
                      Enter your Meesho price and cost to see your payout.
                    </p>
                  </div>

                }
              </div><!-- /#resultRegion -->

            </div>
          </mee-card>
        </div>

      </div>

      <!-- Save & Continue: full-width, min 44px touch target via mee-button internals -->
      <div class="pt-2">
        <mee-button
          label="Save &amp; Continue"
          variant="primary"
          [fullWidth]="true"
          (clicked)="onSaveContinue()"
        />
      </div>

    </div>
  `,
})
export class PricingComponent implements OnInit, AfterViewChecked {
  private readonly fb         = inject(FormBuilder);
  private readonly route      = inject(ActivatedRoute);
  private readonly router     = inject(Router);
  private readonly service    = inject(PricingApiService);
  private readonly destroyRef = inject(DestroyRef);

  /** Reference to the P&L result region — used for programmatic focus after calculate. */
  @ViewChild('resultRegion') private resultRegionEl?: ElementRef<HTMLElement>;

  /** Pending focus flag: set true after a calc completes/errors; consumed in AfterViewChecked. */
  private _focusPending = false;

  private productId = '';

  readonly formatRupeeLabel    = formatRupee;
  readonly resolveAlertMessage = (messageId: string): string =>
    ALERT_MESSAGES[messageId] ?? messageId;
  readonly resolveAlertVariant = (code: string): AlertVariant =>
    ALERT_VARIANT_MAP[code] ?? 'info';

  // ── Reactive form (§12.M forward estimator) ─────────────────────────────
  // meesho_price: primary required input (listed/selling price).
  // input_cost:   required COGS per unit.
  // commission_pct: optional, default "4", 0–100%.
  // return_rate_pct: optional, default "0", 0–100%.
  // mrp: optional display reference (does NOT drive payout — DECISION-1).
  readonly form = this.fb.group({
    meesho_price:    ['',  [Validators.required, Validators.min(0.01)]],
    input_cost:      ['',  [Validators.required, Validators.min(0.01)]],
    commission_pct:  ['4', [Validators.required, Validators.min(0), Validators.max(100)]],
    return_rate_pct: ['0', [Validators.min(0), Validators.max(100)]],
    mrp:             ['',  [Validators.min(0.01)]],
  });

  // P&L breakdown — null until successful server response; stays null on error (R-W6-1).
  readonly breakdown = signal<PriceCalcResponse | null>(null);

  // True while HTTP POST is in-flight.
  readonly calculating = signal<boolean>(false);

  // Typed error state per §3.1 degradation matrix. null = no error.
  readonly errorState = signal<PricingErrorState>(null);

  // Detail copy for 400 validation — set from server response.
  readonly validationDetail = signal<string>('Invalid pricing input.');

  // DECISION-3: estimated_payout drives payoutIsPositive (hero + badge).
  // profit drives marginIsPositive (ratios colour). Both are present in §12.M response.
  readonly payoutIsPositive = computed<boolean>(
    () => parseDecimal(this.breakdown()?.estimated_payout ?? '0') > 0,
  );

  readonly marginIsPositive = computed<boolean>(
    () => parseDecimal(this.breakdown()?.profit ?? '0') > 0,
  );

  // ── Field error signals (show only after touch) ──────────────────────────
  readonly meeshoPriceError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.meesho_price;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Meesho price is required.';
    if (ctrl.hasError('min'))      return 'Meesho price must be greater than 0.';
    return 'Invalid Meesho price.';
  });

  readonly inputCostError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.input_cost;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Input cost is required.';
    if (ctrl.hasError('min'))      return 'Input cost must be greater than 0.';
    return 'Invalid input cost.';
  });

  readonly commissionPctError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.commission_pct;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Commission % is required.';
    if (ctrl.hasError('min'))      return 'Commission cannot be negative.';
    if (ctrl.hasError('max'))      return 'Commission cannot exceed 100%.';
    return 'Invalid commission %.';
  });

  readonly returnRatePctError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.return_rate_pct;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('min')) return 'Return rate cannot be negative.';
    if (ctrl.hasError('max')) return 'Return rate cannot exceed 100%.';
    return 'Invalid return rate %.';
  });

  readonly mrpError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.mrp;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('min')) return 'MRP must be greater than 0.';
    return 'Invalid MRP.';
  });

  ngOnInit(): void {
    this.productId = this.route.snapshot.paramMap.get('id') ?? '';

    // DECISION-2: live recalc — form.valueChanges → debounceTime(350) → switchMap(calc).
    // Cancels in-flight request on every keystroke (switchMap last-write-wins semantics).
    // Skips when form is invalid (required fields empty).
    this.form.valueChanges
      .pipe(
        debounceTime(350),
        distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        if (this.form.valid) {
          this._runCalc();
        }
      });
  }

  /**
   * After Angular updates the view: if a focus is pending (result or error arrived),
   * shift focus to the result region so screen readers announce the updated content.
   * Deferred microtask avoids NG0100 ExpressionChangedAfterChecked.
   */
  ngAfterViewChecked(): void {
    if (this._focusPending && this.resultRegionEl) {
      this._focusPending = false;
      const el = this.resultRegionEl.nativeElement;
      Promise.resolve().then(() => el.focus());
    }
  }

  /**
   * Explicit "Calculate" button handler — a11y fallback for live recalc.
   * Also fires on first submit when the user hasn't triggered valueChanges yet.
   * DECISION-1: NEVER compute locally. Server-calc only.
   */
  onCalculate(): void {
    if (this.form.invalid) return;
    this._runCalc();
  }

  onSaveContinue(): void {
    void this.router.navigate(['/catalogs', this.productId, 'export']);
  }

  // ── Internal: runs the actual HTTP POST and wires up the state machine ───
  private _runCalc(): void {
    this.calculating.set(true);
    this.errorState.set(null);
    this.breakdown.set(null);

    const raw = this.form.getRawValue();
    const body = this._buildRequestBody(raw);

    this.service.calc(this.productId, body).subscribe({
      next: (result) => {
        this.calculating.set(false);
        if ('kind' in result) {
          this._handleErrorShape(result);
        } else {
          this.breakdown.set(result);
        }
        this._focusPending = true;
      },
      error: () => {
        // Service absorbs all errors via catchError. Defensive guard.
        this.calculating.set(false);
        this.errorState.set('server_error');
        this._focusPending = true;
      },
      complete: () => {
        // Fires on EMPTY (401). Ensure calculating is cleared.
        this.calculating.set(false);
      },
    });
  }

  /** Builds a PriceCalcRequest from raw form values, omitting optional empty fields. */
  private _buildRequestBody(raw: typeof this.form.value): PriceCalcRequest {
    const body: PriceCalcRequest = {
      meesho_price: String(raw.meesho_price ?? ''),
      input_cost:   String(raw.input_cost ?? ''),
    };

    // commission_pct: always send (has a default; validator ensures it is present)
    if (raw.commission_pct !== null && raw.commission_pct !== '') {
      body.commission_pct = String(raw.commission_pct);
    }

    // return_rate_pct: send if non-empty (default "0" in form, but omit if cleared)
    if (raw.return_rate_pct !== null && raw.return_rate_pct !== '') {
      body.return_rate_pct = String(raw.return_rate_pct);
    }

    // mrp: optional — only send if user provided a value
    if (raw.mrp !== null && raw.mrp !== '') {
      body.mrp = String(raw.mrp);
    }

    return body;
  }

  /** Maps typed error shapes to PricingErrorState per §3.1 degradation matrix. */
  private _handleErrorShape(shape: PriceCalcErrorShape): void {
    switch (shape.kind) {
      case 'unavailable':
        this.errorState.set('unavailable');
        break;
      case 'validation':
        this.errorState.set('validation');
        this.validationDetail.set(shape.detail);
        break;
      case 'server_error':
        this.errorState.set('server_error');
        break;
    }
  }
}

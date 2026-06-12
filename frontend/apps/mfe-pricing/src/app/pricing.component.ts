import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { MeeAlertBannerComponent }  from '@mesell/composites';
import { MeeOfflineBannerComponent } from '@mesell/composites';
import { PageHeaderComponent }       from '@mesell/composites';
import { MeeBadgeComponent }         from '@mesell/ui-kit';
import { MeeButtonComponent }        from '@mesell/ui-kit';
import { MeeCardComponent }          from '@mesell/ui-kit';
import { MeeInputComponent }         from '@mesell/ui-kit';

import { formatRupee, parseDecimal } from './pricing.utils';
import { PricingApiService }         from './pricing.service';
import type { PriceCalcResponse, PriceCalcErrorShape } from './pricing.model';
import { ALERT_MESSAGES } from './pricing.model';

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
  template: `
    <div class="max-w-5xl mx-auto px-4 py-6 space-y-6">

      <!-- Offline banner (R-W6-1 degradation matrix) -->
      <mee-offline-banner />

      <!-- Page Header -->
      <mee-page-header
        title="Price Calculator"
        subtitle="Enter your cost and target margin to calculate pricing"
      />

      <!-- Main layout: stacked on mobile, 2-col on desktop -->
      <div class="flex flex-col gap-6 lg:flex-row lg:items-start">

        <!-- INPUT SECTION -->
        <div class="lg:w-2/5">
          <mee-card>
            <form [formGroup]="form" class="space-y-4 p-2">

              <h2 class="text-base font-semibold" style="color: var(--mee-color-on-surface)">
                Enter pricing details
              </h2>

              <!-- Input cost field (COGS per unit — replaces the retired MRP input, DECISION-1) -->
              <mee-input
                label="Input cost (COGS per unit)"
                type="number"
                prefix="&#8377;"
                placeholder="e.g. 300"
                formControlName="input_cost"
                [error]="inputCostError()"
              />

              <!-- Target margin (% of input_cost) — replaces retired target_margin (INR) -->
              <mee-input
                label="Target margin %"
                type="number"
                suffix="%"
                placeholder="e.g. 30"
                formControlName="target_margin_pct"
                [error]="targetMarginError()"
              />

              <!-- Calculate button — server round-trip on click; NO auto-fire on input (§3.3) -->
              <mee-button
                label="Calculate"
                variant="primary"
                [fullWidth]="true"
                [disabled]="form.invalid || calculating()"
                (clicked)="onCalculate()"
              />

            </form>
          </mee-card>
        </div>

        <!-- P&L BREAKDOWN + ERROR STATES -->
        <div class="lg:w-3/5">
          <mee-card>
            <div class="p-2 space-y-4">

              <h2 class="text-base font-semibold" style="color: var(--mee-color-on-surface)">
                P&amp;L Breakdown
              </h2>

              <!-- Error: 404 — flag off or product not found (NO local math, DECISION-1) -->
              @if (errorState() === 'unavailable') {
                <mee-alert-banner
                  variant="error"
                  message="Price Calculator is unavailable. Please try again later or contact support."
                />
              }

              <!-- Error: 422 — category has no usable commission rate -->
              @if (errorState() === 'commission_missing') {
                <mee-alert-banner
                  variant="warning"
                  [message]="commissionMissingDetail()"
                />
              }

              <!-- Error: 400 — Pydantic validation failure -->
              @if (errorState() === 'validation') {
                <mee-alert-banner
                  variant="warning"
                  [message]="validationDetail()"
                />
              }

              <!-- Error: 5xx / network — manual re-submit (export-lane pattern, §3.2) -->
              @if (errorState() === 'server_error') {
                <mee-alert-banner
                  variant="error"
                  message="Couldn't calculate price — please try again."
                />
              }

              <!-- Calculating in-flight spinner (a11y live region) -->
              @if (calculating()) {
                <div
                  role="status"
                  aria-live="polite"
                  aria-label="Calculating price..."
                  class="flex items-center justify-center py-8"
                >
                  <!--
                    Raw CSS spinner: MeeSpinnerComponent not yet in @mesell/ui-kit.
                    Builder-3 (ui-styler) TODO: replace when MeeSpinnerComponent ships.
                  -->
                  <div
                    class="mee-pricing-spinner"
                    style="
                      width: 32px; height: 32px;
                      border: 3px solid var(--mee-color-outline);
                      border-top-color: var(--mee-color-primary);
                      border-radius: 50%;
                      animation: mee-spin 0.8s linear infinite;
                    "
                  ></div>
                  <style>
                    @keyframes mee-spin { to { transform: rotate(360deg); } }
                  </style>
                </div>
              }

              <!-- P&L result table: real server keys, Decimal strings parsed for display -->
              @if (breakdown()) {
                <table
                  class="w-full text-sm"
                  aria-label="Pricing breakdown"
                  role="region"
                  aria-live="polite"
                >
                  <tbody>
                    <tr class="border-b" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">MRP (server-computed)</td>
                      <td class="py-2 text-right font-medium" style="color: var(--mee-color-on-surface)">
                        {{ formatRupeeLabel(breakdown()!.mrp) }}
                      </td>
                    </tr>
                    <tr class="border-b" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">Meesho Price</td>
                      <td class="py-2 text-right font-medium" style="color: var(--mee-color-on-surface)">
                        {{ formatRupeeLabel(breakdown()!.meesho_price) }}
                      </td>
                    </tr>
                    <tr class="border-b" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">Seller Price</td>
                      <td class="py-2 text-right font-medium" style="color: var(--mee-color-on-surface)">
                        {{ formatRupeeLabel(breakdown()!.seller_price) }}
                      </td>
                    </tr>
                    <tr class="border-b" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">
                        Commission ({{ breakdown()!.commission_pct }}%)
                      </td>
                      <td class="py-2 text-right" style="color: var(--mee-color-on-surface)">
                        {{ formatRupeeLabel(breakdown()!.commission_amount) }}
                      </td>
                    </tr>
                    <tr class="border-b" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">
                        GST ({{ breakdown()!.gst_pct }}%)
                      </td>
                      <td class="py-2 text-right" style="color: var(--mee-color-on-surface)">
                        {{ formatRupeeLabel(breakdown()!.gst_amount) }}
                      </td>
                    </tr>
                    <tr class="border-b-2" style="border-color: var(--mee-color-outline)">
                      <td class="py-2 font-semibold" style="color: var(--mee-color-on-surface)">Profit</td>
                      <td
                        class="py-2 text-right font-semibold"
                        [style.color]="marginIsPositive()
                          ? 'var(--mee-color-success)'
                          : 'var(--mee-color-error)'"
                      >
                        {{ formatRupeeLabel(breakdown()!.profit) }}
                      </td>
                    </tr>
                    <tr>
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">Profit %</td>
                      <td
                        class="py-2 text-right font-medium"
                        [style.color]="marginIsPositive()
                          ? 'var(--mee-color-success)'
                          : 'var(--mee-color-error)'"
                      >
                        {{ breakdown()!.profit_pct }}%
                      </td>
                    </tr>
                  </tbody>
                </table>

                <!-- Margin status badge (driven off profit, not retired net_margin) -->
                <div class="flex items-center gap-2 pt-2">
                  <mee-badge
                    [value]="marginIsPositive() ? 'POSITIVE' : 'NEGATIVE'"
                    [severity]="marginIsPositive() ? 'success' : 'danger'"
                  />
                </div>

                <!-- Server-issued alerts: LOW_MARGIN / HIGH_MRP_MULTIPLIER / THIN_PROFIT -->
                @if (breakdown()!.alerts.length > 0) {
                  <div class="space-y-2 pt-2" aria-label="Pricing alerts">
                    @for (alert of breakdown()!.alerts; track alert.code) {
                      <mee-alert-banner
                        [variant]="alert.severity === 'warning' ? 'warning' : 'info'"
                        [message]="resolveAlertMessage(alert.message_id)"
                      />
                    }
                  </div>
                }

                <!-- V1 shipping disclaimer -->
                <p class="text-xs mt-2" style="color: var(--mee-color-on-surface-muted)">
                  Shipping costs are not included in V1 calculations.
                </p>

              } @else if (!calculating() && !errorState()) {
                <!-- Empty state: no result, no error — initial view -->
                <p class="text-sm py-6 text-center" style="color: var(--mee-color-on-surface-muted)">
                  Enter your input cost and target margin, then click "Calculate".
                </p>
              }

            </div>
          </mee-card>
        </div>

      </div>

      <!-- Save & Continue -->
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
export class PricingComponent implements OnInit {
  private readonly fb      = inject(FormBuilder);
  private readonly route   = inject(ActivatedRoute);
  private readonly router  = inject(Router);
  private readonly service = inject(PricingApiService);

  /** Display helpers exposed to the template. */
  readonly formatRupeeLabel = formatRupee;
  readonly resolveAlertMessage = (messageId: string): string =>
    ALERT_MESSAGES[messageId] ?? messageId;

  /**
   * Reactive form: input_cost + target_margin_pct.
   * DECISION-1 (RULED 2026-06-11): MRP input + MRP slider are DEAD.
   * input_cost = COGS per unit (was mrp); target_margin_pct = % (was target_margin in INR).
   * Defaults are numbers but form controls are string (FormBuilder infers from the default).
   */
  readonly form = this.fb.group({
    input_cost:        ['300',  [Validators.required, Validators.min(0.01)]],
    target_margin_pct: ['30',   [Validators.required, Validators.min(0), Validators.max(500)]],
  });

  /**
   * Server-computed P&L breakdown — null until a successful Calculate response.
   * Stays null on any error; component renders explicit error state instead (R-W6-1).
   */
  readonly breakdown = signal<PriceCalcResponse | null>(null);

  /** True while the HTTP POST is in-flight. */
  readonly calculating = signal<boolean>(false);

  /**
   * Typed error state.
   * null = no error (initial or after cleared).
   * Set from PriceCalcErrorShape.kind or 'server_error' for 5xx EMPTY path.
   */
  readonly errorState = signal<
    'unavailable' | 'commission_missing' | 'validation' | 'server_error' | null
  >(null);

  /** Detail text for 422 commission_missing (from server response). */
  readonly commissionMissingDetail = signal<string>(
    'Pricing is not available for this category yet.',
  );

  /** Detail text for 400 validation failure. */
  readonly validationDetail = signal<string>('Invalid pricing input.');

  private productId = '';

  /**
   * True when profit is strictly positive.
   * Drives POSITIVE/NEGATIVE badge and colour (was driven off net_margin).
   */
  readonly marginIsPositive = computed<boolean>(
    () => parseDecimal(this.breakdown()?.profit ?? '0') > 0,
  );

  // ── Form validation computed signals ──────────────────────────────────────

  readonly inputCostError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.input_cost;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Input cost is required.';
    if (ctrl.hasError('min'))      return 'Input cost must be greater than 0.';
    return 'Invalid input cost.';
  });

  readonly targetMarginError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.target_margin_pct;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Target margin is required.';
    if (ctrl.hasError('min'))      return 'Target margin cannot be negative.';
    if (ctrl.hasError('max'))      return 'Target margin cannot exceed 500%.';
    return 'Invalid target margin.';
  });

  ngOnInit(): void {
    this.productId = this.route.snapshot.paramMap.get('id') ?? '';
  }

  /**
   * Trigger SERVER-SIDE price calculation.
   * Sends {input_cost, target_margin_pct} to POST /price-calc.
   * DECISION-1: NEVER computes locally — server-calc only.
   * No ApiClient retry: defective (retries all errors) + POST is non-idempotent (§3.2).
   * Explicit 5xx error + manual re-submit (export-lane pattern).
   */
  onCalculate(): void {
    if (this.form.invalid) return;

    this.calculating.set(true);
    this.errorState.set(null);
    this.breakdown.set(null);

    const raw = this.form.getRawValue();
    const body = {
      input_cost:        String(raw.input_cost ?? ''),
      target_margin_pct: String(raw.target_margin_pct ?? ''),
    };

    this.service.calc(this.productId, body).subscribe({
      next: (result) => {
        this.calculating.set(false);
        if ('kind' in result) {
          // Typed error shape from catchError — map to error state (never local math)
          this._handleErrorShape(result);
        } else {
          this.breakdown.set(result);
        }
      },
      error: () => {
        // Defensive: service absorbs all errors via catchError + EMPTY.
        // This should not be reached but guards against unexpected throws.
        this.calculating.set(false);
        this.errorState.set('server_error');
      },
      complete: () => {
        // EMPTY path (401 / 5xx): calculating must be set false; breakdown stays null.
        // The 'complete' callback fires on both normal completion AND EMPTY.
        this.calculating.set(false);
      },
    });
  }

  /** Navigate forward to the export step. */
  onSaveContinue(): void {
    void this.router.navigate(['/catalogs', this.productId, 'export']);
  }

  /** Map PriceCalcErrorShape to component error state signals. Never calls local math. */
  private _handleErrorShape(shape: PriceCalcErrorShape): void {
    switch (shape.kind) {
      case 'unavailable':
        this.errorState.set('unavailable');
        break;
      case 'commission_missing':
        this.errorState.set('commission_missing');
        this.commissionMissingDetail.set(shape.detail);
        break;
      case 'validation':
        this.errorState.set('validation');
        this.validationDetail.set(shape.detail);
        break;
    }
  }
}

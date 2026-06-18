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

import { MeeBadgeComponent }       from '@mesell/ui-kit';
import { MeeButtonComponent }       from '@mesell/ui-kit';
import { MeeCardComponent }         from '@mesell/ui-kit';
import { MeeInputComponent }        from '@mesell/ui-kit';
import { MeeProgressBarComponent }  from '@mesell/ui-kit';
import { PageHeaderComponent }      from '@mesell/composites';

import { computePnlBreakdown, formatRupee } from './pricing.utils';
import type { PnlBreakdown } from './pricing.model';

@Component({
  selector: 'app-pricing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MeeBadgeComponent,
    MeeButtonComponent,
    MeeCardComponent,
    MeeInputComponent,
    MeeProgressBarComponent,
    PageHeaderComponent,
  ],
  styles: [`
    :host {
      display: block;
    }

    .pricing-page {
      max-width: 1200px;
      margin: 0 auto;
      padding: var(--mee-space-6) var(--mee-space-4);
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-6);
    }

    .pricing-layout {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-6);
    }

    @media (min-width: 1024px) {
      .pricing-layout {
        flex-direction: row;
        align-items: flex-start;
      }
    }

    .pricing-input-col {
      min-width: 0;
      width: 100%;
    }

    @media (min-width: 1024px) {
      .pricing-input-col { width: 40%; }
    }

    .pricing-result-col {
      min-width: 0;
      width: 100%;
    }

    @media (min-width: 1024px) {
      .pricing-result-col { width: 60%; }
    }

    .form-body {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
      padding: var(--mee-space-2);
    }

    .form-heading {
      font-size: 15px;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin: 0;
    }

    /* Slider */
    .slider-wrap {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
    }

    .slider-label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: var(--mee-color-on-surface);
    }

    .slider-input {
      width: 100%;
      min-height: 44px;
      cursor: pointer;
      display: block;
      accent-color: var(--mee-color-primary);
      border-radius: var(--mee-radius-full);
      outline: none;
      appearance: auto;
    }

    .slider-range-row {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--mee-color-on-surface-muted);
    }

    .slider-current {
      font-weight: 500;
      color: var(--mee-color-on-surface);
    }

    /* Result card */
    .result-body {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
      padding: var(--mee-space-2);
    }

    .result-heading {
      font-size: 15px;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin: 0;
    }

    /* P&L table */
    .pnl-table {
      width: 100%;
      font-size: 14px;
      border-collapse: collapse;
    }

    .pnl-row {
      border-bottom: 1px solid var(--mee-color-outline);
    }

    .pnl-row--total {
      border-bottom: 2px solid var(--mee-color-outline);
    }

    .pnl-label {
      padding: var(--mee-space-2) 0;
      color: var(--mee-color-on-surface-muted);
    }

    .pnl-label--bold {
      color: var(--mee-color-on-surface);
      font-weight: 600;
    }

    .pnl-value {
      padding: var(--mee-space-2) 0;
      text-align: right;
      font-weight: 500;
      color: var(--mee-color-on-surface);
    }

    .pnl-value--bold {
      font-weight: 600;
    }

    .pnl-value--positive {
      color: var(--mee-color-success);
    }

    .pnl-value--negative {
      color: var(--mee-color-error);
    }

    /* Margin visual section */
    .margin-visual {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
      padding-top: var(--mee-space-2);
      border-top: 1px solid var(--mee-color-outline);
    }

    .margin-headline {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .margin-label {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
    }

    .margin-pct {
      font-size: 22px;
      font-weight: 700;
    }

    .margin-pct--healthy    { color: var(--mee-color-success); }
    .margin-pct--borderline { color: var(--mee-color-warning); }
    .margin-pct--negative   { color: var(--mee-color-error); }

    .margin-rec {
      font-size: 13px;
      font-weight: 500;
      padding: var(--mee-space-2) var(--mee-space-3);
      border-radius: var(--mee-radius-sm);
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
    }

    .margin-rec--healthy {
      background: rgba(22, 163, 74, 0.1);
      color: var(--mee-color-success);
    }

    .margin-rec--borderline {
      background: rgba(217, 119, 6, 0.1);
      color: var(--mee-color-warning);
    }

    .margin-rec--negative {
      background: rgba(220, 38, 38, 0.08);
      color: var(--mee-color-error);
    }

    /* Badge row */
    .status-row {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
      padding-top: var(--mee-space-2);
    }

    /* Empty state */
    .result-empty {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      text-align: center;
      padding: var(--mee-space-8) 0;
      margin: 0;
    }

    /* Disclaimer */
    .result-disclaimer {
      font-size: 12px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }

    /* Save row */
    .save-row {
      padding-top: var(--mee-space-2);
    }
  `],
  template: `
    <div class="pricing-page">

      <!-- Page Header -->
      <mee-page-header
        title="Price Calculator"
        subtitle="Set your MRP and see the margin breakdown"
      />

      <!-- Main layout: stacked on mobile, 2-col on desktop -->
      <div class="pricing-layout">

        <!-- INPUT SECTION -->
        <div class="pricing-input-col">
          <mee-card>
            <form [formGroup]="form" class="form-body">

              <h2 class="form-heading">Enter pricing details</h2>

              <!-- MRP field -->
              <mee-input
                label="MRP"
                type="number"
                prefix="&#8377;"
                placeholder="e.g. 899"
                formControlName="mrp"
                (change)="onMrpInput()"
                [error]="mrpError()"
              />

              <!-- Target margin field -->
              <mee-input
                label="Target margin"
                type="number"
                prefix="&#8377;"
                placeholder="e.g. 150"
                formControlName="target_margin"
                [error]="targetMarginError()"
              />

              <!-- Native range slider (no mee-slider primitive exists in UI Kit) -->
              <div class="slider-wrap">
                <label class="slider-label">
                  Adjust MRP via slider
                </label>
                <input
                  type="range"
                  [value]="sliderMrp()"
                  min="100"
                  max="5000"
                  step="50"
                  (input)="onSliderInput($event)"
                  class="slider-input"
                  aria-label="Adjust MRP"
                />
                <div class="slider-range-row">
                  <span>&#8377;100</span>
                  <span class="slider-current">
                    Current: {{ formatRupeeLabel(sliderMrp()) }}
                  </span>
                  <span>&#8377;5,000</span>
                </div>
              </div>

              <!-- Calculate button -->
              <mee-button
                class="block"
                label="Calculate"
                variant="primary"
                [fullWidth]="true"
                [disabled]="form.invalid"
                (clicked)="onCalculate()"
              />

            </form>
          </mee-card>
        </div>

        <!-- P&L BREAKDOWN -->
        <div class="pricing-result-col">
          <mee-card>
            <div class="result-body">

              <h2 class="result-heading">P&amp;L Breakdown</h2>

              @if (breakdown()) {
                <table class="pnl-table" aria-label="Pricing breakdown">
                  <tbody>
                    <tr class="pnl-row">
                      <td class="pnl-label">MRP</td>
                      <td class="pnl-value">
                        {{ formatRupeeLabel(breakdown()!.mrp) }}
                      </td>
                    </tr>
                    <tr class="pnl-row">
                      <td class="pnl-label">Meesho Price</td>
                      <td class="pnl-value">
                        {{ formatRupeeLabel(breakdown()!.meesho_price) }}
                      </td>
                    </tr>
                    <tr class="pnl-row">
                      <td class="pnl-label">
                        Commission ({{ breakdown()!.commission_pct }}%)
                      </td>
                      <td class="pnl-value">
                        {{ formatRupeeLabel(breakdown()!.commission_amt) }}
                      </td>
                    </tr>
                    <tr class="pnl-row">
                      <td class="pnl-label">
                        GST ({{ breakdown()!.gst_pct }}%)
                      </td>
                      <td class="pnl-value">
                        {{ formatRupeeLabel(breakdown()!.gst_amt) }}
                      </td>
                    </tr>
                    <tr class="pnl-row pnl-row--total">
                      <td class="pnl-label pnl-label--bold">Seller Payout</td>
                      <td class="pnl-value pnl-value--bold">
                        {{ formatRupeeLabel(breakdown()!.seller_payout) }}
                      </td>
                    </tr>
                    <tr class="pnl-row">
                      <td class="pnl-label pnl-label--bold">Net Margin</td>
                      <td
                        class="pnl-value pnl-value--bold"
                        [class.pnl-value--positive]="marginIsPositive()"
                        [class.pnl-value--negative]="!marginIsPositive()"
                      >
                        {{ formatRupeeLabel(breakdown()!.net_margin) }}
                      </td>
                    </tr>
                    <tr>
                      <td class="pnl-label">Net Margin %</td>
                      <td
                        class="pnl-value"
                        [class.pnl-value--positive]="marginIsPositive()"
                        [class.pnl-value--negative]="!marginIsPositive()"
                      >
                        {{ breakdown()!.net_margin_pct }}%
                      </td>
                    </tr>
                  </tbody>
                </table>

                <!-- Margin visual -->
                <div class="margin-visual">
                  <div class="margin-headline">
                    <span class="margin-label">Net margin</span>
                    <span class="margin-pct" [class]="'margin-pct--' + marginTier()">
                      {{ breakdown()!.net_margin_pct }}%
                    </span>
                  </div>
                  <mee-progress-bar [value]="marginBarValue()" />
                  <div class="margin-rec" [class]="'margin-rec--' + marginTier()">
                    {{ marginRecommendation() }}
                  </div>
                </div>

                <!-- Margin status badge -->
                <div class="status-row">
                  <mee-badge
                    [value]="marginIsPositive() ? 'POSITIVE' : 'NEGATIVE'"
                    [severity]="marginIsPositive() ? 'success' : 'danger'"
                  />
                </div>

                <!-- V1 shipping disclaimer -->
                <p class="result-disclaimer">
                  Shipping costs are not included in V1 calculations.
                </p>

              } @else {
                <p class="result-empty">
                  Enter MRP and target margin above, then click "Calculate" to see your P&amp;L.
                </p>
              }

            </div>
          </mee-card>
        </div>

      </div>

      <!-- Save & Continue -->
      <div class="save-row">
        <mee-button
          class="block"
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
  private readonly fb     = inject(FormBuilder);
  private readonly route  = inject(ActivatedRoute);
  private readonly router = inject(Router);

  /** Exposed to template (avoids TS strict no-property-access-from-index). */
  readonly formatRupeeLabel = formatRupee;

  /** Reactive form: MRP + target margin. */
  readonly form = this.fb.group({
    mrp:           [899,  [Validators.required, Validators.min(1), Validators.max(99999)]],
    target_margin: [150,  [Validators.required, Validators.min(0)]],
  });

  /** Mirrors slider thumb position (synced two-way with form MRP control). */
  readonly sliderMrp = signal<number>(899);

  /** Computed P&L breakdown — null until Calculate is first clicked. */
  readonly breakdown = signal<PnlBreakdown | null>(null);

  /** Reserved for future async API wiring. */
  readonly calculating = signal<boolean>(false);

  /** Extracted from route params in ngOnInit. */
  private productId = '';

  /** True when net_margin is strictly positive. */
  readonly marginIsPositive = computed<boolean>(
    () => (this.breakdown()?.net_margin ?? -1) > 0
  );

  /** Three-tier margin health classification. */
  readonly marginTier = computed<'healthy' | 'borderline' | 'negative'>(() => {
    const pct = this.breakdown()?.net_margin_pct ?? 0;
    if (pct >= 25) return 'healthy';
    if (pct >= 15) return 'borderline';
    return 'negative';
  });

  /** Human-readable recommendation driven by marginTier. */
  readonly marginRecommendation = computed<string>(() => {
    const tier = this.marginTier();
    if (tier === 'healthy')    return '✓ Healthy margin — good to go';
    if (tier === 'borderline') return '⚠ Borderline — consider raising MRP';
    return '✗ Below threshold — raise MRP to improve margin';
  });

  /** Clamped 0–100 value for the progress bar. */
  readonly marginBarValue = computed<number>(() => {
    const pct = this.breakdown()?.net_margin_pct ?? 0;
    return Math.min(Math.max(pct, 0), 100);
  });

  // ── Form validation error messages ──

  readonly mrpError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.mrp;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'MRP is required.';
    if (ctrl.hasError('min'))      return 'MRP must be at least 1.';
    if (ctrl.hasError('max'))      return 'MRP cannot exceed 99,999.';
    return 'Invalid MRP.';
  });

  readonly targetMarginError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.target_margin;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Target margin is required.';
    if (ctrl.hasError('min'))      return 'Target margin cannot be negative.';
    return 'Invalid target margin.';
  });

  ngOnInit(): void {
    this.productId = this.route.snapshot.paramMap.get('id') ?? '';
  }

  /**
   * Native range slider moved — sync slider signal AND form MRP control.
   * Pattern: "native range for V1 margin slider" (no mee-slider primitive exists).
   */
  onSliderInput(event: Event): void {
    const val = (event.target as HTMLInputElement).valueAsNumber;
    this.sliderMrp.set(val);
    this.form.patchValue({ mrp: val });
  }

  /**
   * MRP text field changed — clamp and sync slider signal from form value.
   */
  onMrpInput(): void {
    const val = this.form.controls.mrp.value;
    if (val !== null && val !== undefined && !isNaN(Number(val))) {
      const clamped = Math.min(Math.max(Number(val), 100), 5000);
      this.sliderMrp.set(clamped);
    }
  }

  /** Run client-side P&L calculation. Synchronous — no HTTP in V1 simulation. */
  onCalculate(): void {
    if (this.form.invalid) return;
    this.calculating.set(true);
    const mrp    = this.form.controls.mrp.value ?? 0;
    const margin = this.form.controls.target_margin.value ?? 0;
    this.breakdown.set(computePnlBreakdown(mrp, margin));
    this.calculating.set(false);
  }

  /** Navigate forward to the export step. */
  onSaveContinue(): void {
    void this.router.navigate(['/catalogs', this.productId, 'export']);
  }
}

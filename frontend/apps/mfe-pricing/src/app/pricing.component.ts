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

import { MeeBadgeComponent }   from '@mesell/ui-kit';
import { MeeButtonComponent }  from '@mesell/ui-kit';
import { MeeCardComponent }    from '@mesell/ui-kit';
import { MeeInputComponent }   from '@mesell/ui-kit';
import { PageHeaderComponent } from '@mesell/composites';

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
    PageHeaderComponent,
  ],
  template: `
    <div class="max-w-5xl mx-auto px-4 py-6 space-y-6">

      <!-- Page Header -->
      <mee-page-header
        title="Price Calculator"
        subtitle="Set your MRP and see the margin breakdown"
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
              <div class="space-y-2">
                <label
                  class="block text-sm font-medium"
                  style="color: var(--mee-color-on-surface)"
                >
                  Adjust MRP via slider
                </label>
                <input
                  type="range"
                  [value]="sliderMrp()"
                  min="100"
                  max="5000"
                  step="50"
                  (input)="onSliderInput($event)"
                  class="w-full rounded-full outline-none"
                  style="
                    accent-color: var(--mee-color-primary);
                    min-height: 44px;
                    cursor: pointer;
                    display: block;
                  "
                  aria-label="Adjust MRP"
                />
                <div class="flex justify-between text-xs" style="color: var(--mee-color-on-surface-muted)">
                  <span>&#8377;100</span>
                  <span class="font-medium" style="color: var(--mee-color-on-surface)">
                    Current: {{ formatRupeeLabel(sliderMrp()) }}
                  </span>
                  <span>&#8377;5,000</span>
                </div>
              </div>

              <!-- Calculate button -->
              <mee-button
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
        <div class="lg:w-3/5">
          <mee-card>
            <div class="p-2 space-y-4">

              <h2 class="text-base font-semibold" style="color: var(--mee-color-on-surface)">
                P&amp;L Breakdown
              </h2>

              @if (breakdown()) {
                <table class="w-full text-sm" aria-label="Pricing breakdown">
                  <tbody>
                    <tr class="border-b" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">MRP</td>
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
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">
                        Commission ({{ breakdown()!.commission_pct }}%)
                      </td>
                      <td class="py-2 text-right" style="color: var(--mee-color-on-surface)">
                        {{ formatRupeeLabel(breakdown()!.commission_amt) }}
                      </td>
                    </tr>
                    <tr class="border-b" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">
                        GST ({{ breakdown()!.gst_pct }}%)
                      </td>
                      <td class="py-2 text-right" style="color: var(--mee-color-on-surface)">
                        {{ formatRupeeLabel(breakdown()!.gst_amt) }}
                      </td>
                    </tr>
                    <tr class="border-b-2" style="border-color: var(--mee-color-outline)">
                      <td class="py-2 font-semibold" style="color: var(--mee-color-on-surface)">
                        Seller Payout
                      </td>
                      <td class="py-2 text-right font-semibold" style="color: var(--mee-color-on-surface)">
                        {{ formatRupeeLabel(breakdown()!.seller_payout) }}
                      </td>
                    </tr>
                    <tr class="border-b" style="border-color: var(--mee-color-outline)">
                      <td class="py-2 font-semibold" style="color: var(--mee-color-on-surface)">
                        Net Margin
                      </td>
                      <td
                        class="py-2 text-right font-semibold"
                        [style.color]="marginIsPositive()
                          ? 'var(--mee-color-success)'
                          : 'var(--mee-color-error)'"
                      >
                        {{ formatRupeeLabel(breakdown()!.net_margin) }}
                      </td>
                    </tr>
                    <tr>
                      <td class="py-2" style="color: var(--mee-color-on-surface-muted)">Net Margin %</td>
                      <td
                        class="py-2 text-right font-medium"
                        [style.color]="marginIsPositive()
                          ? 'var(--mee-color-success)'
                          : 'var(--mee-color-error)'"
                      >
                        {{ breakdown()!.net_margin_pct }}%
                      </td>
                    </tr>
                  </tbody>
                </table>

                <!-- Margin status badge -->
                <div class="flex items-center gap-2 pt-2">
                  <mee-badge
                    [value]="marginIsPositive() ? 'POSITIVE' : 'NEGATIVE'"
                    [severity]="marginIsPositive() ? 'success' : 'danger'"
                  />
                </div>

                <!-- V1 shipping disclaimer -->
                <p class="text-xs mt-2" style="color: var(--mee-color-on-surface-muted)">
                  Shipping costs are not included in V1 calculations.
                </p>

              } @else {
                <p class="text-sm py-6 text-center" style="color: var(--mee-color-on-surface-muted)">
                  Enter MRP and target margin above, then click "Calculate" to see your P&amp;L.
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

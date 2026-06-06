// features/pricing/pricing/pricing.component.ts
// Visual shell — stub data only, no service injection per task scope.

import { ChangeDetectionStrategy, Component, signal, inject } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';

interface PricingResult {
  sellingPrice: number;
  commission: number;
  shipping: number;
  cogs: number;
  grossProfit: number;
  marginPct: number;
}

function calcPricing(mrp: number, cogs: number, shipping: number, commissionPct: number): PricingResult {
  const commission = Math.round(mrp * commissionPct / 100);
  const grossProfit = mrp - commission - shipping - cogs;
  const marginPct = mrp > 0 ? Math.round((grossProfit / mrp) * 1000) / 10 : 0;
  return { sellingPrice: mrp, commission, shipping, cogs, grossProfit, marginPct };
}

@Component({
  selector: 'mee-pricing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  template: `
    <!-- Page header -->
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:24px;">
      <div>
        <h1 style="font-size:22px; font-weight:700; color:#1F2937; margin:0;">Pricing Calculator</h1>
        <p style="font-size:13px; color:#6B7280; margin:4px 0 0 0;">Calculate optimal price for maximum profit</p>
      </div>
    </div>

    <!-- Two-column layout -->
    <div [style]="gridStyle">
      <!-- Left — Input card -->
      <div style="flex:1 1 0; min-width:280px; background:#ffffff; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <h2 style="font-size:14px; font-weight:700; color:#374151; margin:0 0 20px 0;">Product Cost Details</h2>

        <form [formGroup]="form">
          <!-- MRP -->
          <div style="margin-bottom:16px;">
            <label for="mrp" style="display:block; font-size:13px; font-weight:500; color:#374151; margin-bottom:6px;">MRP (₹)</label>
            <input
              id="mrp"
              formControlName="mrp"
              type="number"
              style="width:100%; height:44px; box-sizing:border-box; border:1px solid #D1D5DB; border-radius:8px; padding:0 14px; font-size:14px; color:#1F2937; background:#fff; outline:none; transition:border-color 0.15s;"
              (focus)="onFocus($event)"
              (blur)="onBlur($event)"
            />
          </div>

          <!-- Cost of Goods -->
          <div style="margin-bottom:16px;">
            <label for="cogs" style="display:block; font-size:13px; font-weight:500; color:#374151; margin-bottom:6px;">Cost of Goods (₹)</label>
            <input
              id="cogs"
              formControlName="cogs"
              type="number"
              style="width:100%; height:44px; box-sizing:border-box; border:1px solid #D1D5DB; border-radius:8px; padding:0 14px; font-size:14px; color:#1F2937; background:#fff; outline:none; transition:border-color 0.15s;"
              (focus)="onFocus($event)"
              (blur)="onBlur($event)"
            />
          </div>

          <!-- Shipping -->
          <div style="margin-bottom:16px;">
            <label for="shipping" style="display:block; font-size:13px; font-weight:500; color:#374151; margin-bottom:6px;">Shipping Charge (₹)</label>
            <input
              id="shipping"
              formControlName="shipping"
              type="number"
              style="width:100%; height:44px; box-sizing:border-box; border:1px solid #D1D5DB; border-radius:8px; padding:0 14px; font-size:14px; color:#1F2937; background:#fff; outline:none; transition:border-color 0.15s;"
              (focus)="onFocus($event)"
              (blur)="onBlur($event)"
            />
            <p style="font-size:12px; color:#9CA3AF; margin:4px 0 0 0;">Meesho's platform shipping charge</p>
          </div>

          <!-- Platform Commission -->
          <div style="margin-bottom:16px;">
            <label for="commission" style="display:block; font-size:13px; font-weight:500; color:#374151; margin-bottom:6px;">Platform Commission (%)</label>
            <input
              id="commission"
              formControlName="commission"
              type="number"
              style="width:100%; height:44px; box-sizing:border-box; border:1px solid #D1D5DB; border-radius:8px; padding:0 14px; font-size:14px; color:#1F2937; background:#fff; outline:none; transition:border-color 0.15s;"
              (focus)="onFocus($event)"
              (blur)="onBlur($event)"
            />
            <p style="font-size:12px; color:#9CA3AF; margin:4px 0 0 0;">Standard 18% for apparel</p>
          </div>

          <!-- Calculate button -->
          <button
            type="button"
            (click)="calculate()"
            style="display:block; width:100%; height:44px; background:#F26B23; color:#ffffff; border:none; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; margin-top:8px;"
          >
            Calculate
          </button>
        </form>
      </div>

      <!-- Right — Result card -->
      <div style="flex:0 0 340px; min-width:280px; background:#ffffff; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <h2 style="font-size:14px; font-weight:700; color:#374151; margin:0 0 20px 0;">Profit Analysis</h2>

        <!-- Big selling price -->
        <div style="text-align:center;">
          <div style="font-size:32px; font-weight:700; color:#1F2937;">₹ {{ result().sellingPrice }}</div>
          <div style="font-size:12px; color:#6B7280; margin-top:4px;">Recommended selling price</div>
        </div>

        <!-- Divider -->
        <div style="border-top:1px solid #F3F4F6; margin:16px 0;"></div>

        <!-- Breakdown rows -->
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; font-size:14px; padding:8px 0; border-bottom:1px solid #F9FAFB;">
            <span style="color:#1F2937;">Platform Commission</span>
            <span style="color:#DC2626;">₹ {{ result().commission }}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; font-size:14px; padding:8px 0; border-bottom:1px solid #F9FAFB;">
            <span style="color:#1F2937;">Shipping</span>
            <span style="color:#DC2626;">₹ {{ result().shipping }}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; font-size:14px; padding:8px 0; border-bottom:1px solid #F9FAFB;">
            <span style="color:#1F2937;">Cost of Goods</span>
            <span style="color:#DC2626;">₹ {{ result().cogs }}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; font-size:14px; padding:8px 0; border-bottom:1px solid #F9FAFB;">
            <span style="color:#1F2937;">Gross Profit</span>
            <span style="color:#16A34A; font-weight:700;">₹ {{ result().grossProfit }}</span>
          </div>
        </div>

        <!-- Margin badge -->
        <div style="text-align:center; margin-top:16px;">
          <span style="display:inline-block; background:#DCFCE7; color:#15803D; border-radius:999px; padding:6px 16px; font-size:13px; font-weight:600;">
            Margin: {{ result().marginPct }}%
          </span>
        </div>
      </div>
    </div>
  `,
})
export class PricingComponent {
  private readonly fb = inject(FormBuilder);

  readonly form: FormGroup = this.fb.group({
    mrp: [599],
    cogs: [220],
    shipping: [45],
    commission: [18],
  });

  readonly result = signal<PricingResult>(
    calcPricing(599, 220, 45, 18)
  );

  // Responsive two-column: flex-wrap collapses to single column on narrow screens.
  // Left card grows to fill; right card is min 300px capped at 340px.
  readonly gridStyle = 'display:flex; flex-wrap:wrap; gap:24px; align-items:flex-start;';

  calculate(): void {
    const v = this.form.value;
    const mrp = Number(v.mrp) || 0;
    const cogs = Number(v.cogs) || 0;
    const shipping = Number(v.shipping) || 0;
    const commission = Number(v.commission) || 0;
    this.result.set(calcPricing(mrp, cogs, shipping, commission));
  }

  onFocus(event: Event): void {
    (event.target as HTMLInputElement).style.borderColor = '#F26B23';
  }

  onBlur(event: Event): void {
    (event.target as HTMLInputElement).style.borderColor = '#D1D5DB';
  }
}

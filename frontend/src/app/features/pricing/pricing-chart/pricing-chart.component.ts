// features/pricing/pricing-chart/pricing-chart.component.ts
// Stub — full implementation by meesell-angular-component-builder per §14.B
// Uses chart.js + ng2-charts (per §6 pick #8)

import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { PricingCalc } from '@core/models/pricing-calc.model';

@Component({
  selector: 'mee-pricing-chart',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="mee-pricing-chart"><!-- Pricing chart stub --></div>`,
})
export class PricingChartComponent {
  readonly calc = input.required<PricingCalc>();
}

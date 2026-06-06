// features/pricing/pnl-breakdown/pnl-breakdown.component.ts
// Stub — full implementation by meesell-angular-component-builder per §14.B

import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { PricingCalc } from '@core/models/pricing-calc.model';

@Component({
  selector: 'mee-pnl-breakdown',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="mee-pnl-breakdown"><!-- PnL breakdown stub --></div>`,
})
export class PnlBreakdownComponent {
  readonly calc = input.required<PricingCalc>();
}

// features/pricing/margin-slider/margin-slider.component.ts
// Stub — full implementation by meesell-angular-component-builder per §14.B

import { ChangeDetectionStrategy, Component, EventEmitter, input, Output } from '@angular/core';

@Component({
  selector: 'mee-margin-slider',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="mee-margin-slider"><!-- Margin slider stub --></div>`,
})
export class MarginSliderComponent {
  readonly mrp = input.required<number>();
  @Output() readonly mrpChange = new EventEmitter<number>();
  @Output() readonly mrpCommit = new EventEmitter<number>();
}

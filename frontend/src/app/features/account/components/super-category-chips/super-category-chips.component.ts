// features/account/components/super-category-chips/super-category-chips.component.ts
// Stub — full implementation by meesell-angular-component-builder per §7

import { ChangeDetectionStrategy, Component, EventEmitter, Output } from '@angular/core';

@Component({
  selector: 'mee-super-category-chips',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="mee-super-category-chips"><!-- Super category chips stub --></div>`,
})
export class SuperCategoryChipsComponent {
  @Output() readonly selectionChange = new EventEmitter<string[]>();
}

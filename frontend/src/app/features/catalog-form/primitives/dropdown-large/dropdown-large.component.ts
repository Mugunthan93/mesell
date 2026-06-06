// features/catalog-form/primitives/dropdown-large/dropdown-large.component.ts
// Stub — full implementation by meesell-angular-component-builder per §18.E

import { ChangeDetectionStrategy, Component, EventEmitter, input, Output } from '@angular/core';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { ValueChange } from '../primitive.contract';

@Component({
  selector: 'mee-dropdown-large',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="mee-primitive mee-primitive--dropdown-large"><!-- dropdown-large primitive stub --></div>`,
})
export class UdropdownUlargePrimitiveComponent {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  @Output() readonly valueChange = new EventEmitter<ValueChange>();
}

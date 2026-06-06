// features/catalog-form/wizard-renderer/field-dispatcher.component.ts
// Stub — full implementation by meesell-angular-component-builder per §18.C

import { ChangeDetectionStrategy, Component, EventEmitter, input, Output } from '@angular/core';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { ValueChange } from '../primitives/primitive.contract';

@Component({
  selector: 'mee-field-dispatcher',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="mee-field-dispatcher"><!-- Field dispatcher stub --></div>`,
})
export class FieldDispatcherComponent {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  @Output() readonly valueChange = new EventEmitter<ValueChange>();
}

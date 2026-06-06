// features/catalog-form/wizard-renderer/wizard-renderer.component.ts
// Stub — full implementation by meesell-angular-component-builder per §18.B

import { ChangeDetectionStrategy, Component, EventEmitter, input, Output } from '@angular/core';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { FieldSchema } from '@core/models/field-schema.model';
import { ValueChange } from '../primitives/primitive.contract';

export interface WizardStep {
  readonly id: string;
  readonly title: Record<string, string>;
  readonly fields: readonly FieldSchema[];
}

@Component({
  selector: 'mee-wizard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="mee-wizard"><!-- Wizard renderer stub --></div>`,
})
export class WizardRendererComponent {
  readonly steps = input.required<WizardStep[]>();
  readonly model = input.required<Record<string, unknown>>();
  readonly aiSuggestions = input<Record<string, AiSuggestion>>({});

  @Output() readonly valueChange = new EventEmitter<ValueChange>();
}

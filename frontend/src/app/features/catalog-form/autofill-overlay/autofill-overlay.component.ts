// features/catalog-form/autofill-overlay/autofill-overlay.component.ts
// Stub — full implementation by meesell-angular-component-builder per §18.G

import { ChangeDetectionStrategy, Component, EventEmitter, input, Output } from '@angular/core';
import { AiSuggestion } from '@core/models/ai-suggestion.model';

export interface AutofillDecision {
  readonly canonicalName: string;
  readonly action: 'accept' | 'reject';
  readonly rejectedReason?: string;
}

@Component({
  selector: 'mee-autofill-overlay',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="mee-autofill-overlay"><!-- Autofill overlay stub --></div>`,
})
export class AutofillOverlayComponent {
  readonly fieldName = input.required<string>();
  readonly suggestion = input.required<AiSuggestion>();

  @Output() readonly decision = new EventEmitter<AutofillDecision>();
}

// features/catalog-form/wizard-renderer/field-dispatcher.component.ts
// B3: Dispatches to the correct primitive based on schema().primitive per §18.C
// Uses Angular 18 @switch control flow with all 11 PrimitiveKind literals.
// CRITICAL: 'dropdown_api_search' (not 'dropdown_api') — silently breaks without this exact string.

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { ValueChange } from '../primitives/primitive.contract';
import { TextShortPrimitiveComponent } from '../primitives/text-short/text-short.component';
import { TextLongPrimitiveComponent } from '../primitives/text-long/text-long.component';
import { NumberPrimitiveComponent } from '../primitives/number/number.component';
import { NumberWithUnitPrimitiveComponent } from '../primitives/number-with-unit/number-with-unit.component';
import { CurrencyPrimitiveComponent } from '../primitives/currency/currency.component';
import { DropdownSmallPrimitiveComponent } from '../primitives/dropdown-small/dropdown-small.component';
import { DropdownMediumPrimitiveComponent } from '../primitives/dropdown-medium/dropdown-medium.component';
import { DropdownLargePrimitiveComponent } from '../primitives/dropdown-large/dropdown-large.component';
import { DropdownApiPrimitiveComponent } from '../primitives/dropdown-api/dropdown-api.component';
import { ImageUploadPrimitiveComponent } from '../primitives/image-upload/image-upload.component';
import { AddressGroupPrimitiveComponent } from '../primitives/address-group/address-group.component';

@Component({
  selector: 'mee-field-dispatcher',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    TextShortPrimitiveComponent,
    TextLongPrimitiveComponent,
    NumberPrimitiveComponent,
    NumberWithUnitPrimitiveComponent,
    CurrencyPrimitiveComponent,
    DropdownSmallPrimitiveComponent,
    DropdownMediumPrimitiveComponent,
    DropdownLargePrimitiveComponent,
    DropdownApiPrimitiveComponent,
    ImageUploadPrimitiveComponent,
    AddressGroupPrimitiveComponent,
  ],
  template: `
    @switch (schema().primitive) {
      @case ('text_short') {
        <mee-text-short
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('text_long') {
        <mee-text-long
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('number') {
        <mee-number
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('number_with_unit') {
        <mee-number-unit
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('currency') {
        <mee-currency
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('dropdown_small') {
        <mee-dropdown-small
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('dropdown_medium') {
        <mee-dropdown-medium
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('dropdown_large') {
        <mee-dropdown-large
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('dropdown_api_search') {
        <mee-dropdown-api
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('image_upload') {
        <mee-image-upload
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
      @case ('address_group') {
        <mee-address-group
          [schema]="schema()"
          [value]="value()"
          [aiSuggestion]="aiSuggestion()"
          [disabled]="disabled()"
          (valueChange)="onChange($event)"
        />
      }
    }
  `,
})
export class FieldDispatcherComponent {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  readonly valueChange = output<ValueChange>();

  onChange(change: ValueChange): void {
    this.valueChange.emit(change);
  }
}

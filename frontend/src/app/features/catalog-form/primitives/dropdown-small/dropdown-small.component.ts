// features/catalog-form/primitives/dropdown-small/dropdown-small.component.ts
// Primitive 6: ≤20 options rendered as mat-radio-group per §18.E
// Implements ControlValueAccessor. Emits ValueChange on selection.
//
// ENUM OPTIONS SOURCE:
// FieldSchema (@core/models/field-schema.model.ts) does not yet have an enumOptions
// field. The backend is expected to include it as part of the category schema response.
// Using (schema() as any).enumOptions as a fallback until the core model is updated.
// TODO(cross-cutting): add `enumOptions?: Array<{code: string; label: LocaleMap}>` to
// FieldSchema, then remove the `as any` cast here.

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  forwardRef,
  input,
  output,
  signal,
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { MatRadioModule, MatRadioChange } from '@angular/material/radio';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { LocaleLabelPipe } from '@shared/pipes/locale-label.pipe';
import { LocaleMap } from '@core/models/locale-map.model';
import { ValueChange } from '../primitive.contract';

export interface DropdownOption {
  readonly code: string;
  readonly label: LocaleMap;
}

@Component({
  selector: 'mee-dropdown-small',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatRadioModule, MatFormFieldModule, LocaleLabelPipe],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => DropdownSmallPrimitiveComponent),
      multi: true,
    },
  ],
  template: `
    <div class="mee-dropdown-small w-full" role="group" [attr.aria-labelledby]="labelId">
      <div class="mat-mdc-form-field-label-wrapper" style="padding-bottom:4px">
        <span [id]="labelId" style="font-size:12px; color:var(--mee-color-on-surface)">
          {{ schema().displayLabel | localeLabel }}
          @if (schema().marker === 'compulsory') {
            <span style="color:var(--mee-color-error)" aria-hidden="true"> *</span>
          }
        </span>
      </div>
      <mat-radio-group
        [value]="innerValue()"
        [disabled]="disabled()"
        (change)="onSelectionChange($event)"
        style="display:flex; flex-direction:column; gap:8px"
      >
        @for (option of options(); track option.code) {
          <mat-radio-button [value]="option.code" style="min-height:44px">
            {{ option.label | localeLabel }}
          </mat-radio-button>
        }
      </mat-radio-group>
      @if (schema().displayHelp) {
        <div style="font-size:12px; color:var(--mee-color-on-surface); margin-top:4px">
          {{ schema().displayHelp | localeLabel }}
        </div>
      }
      @if (touched() && !innerValue() && schema().marker === 'compulsory') {
        <div style="font-size:12px; color:var(--mee-color-error); margin-top:4px" role="alert">
          {{ schema().validationMessage ? (schema().validationMessage | localeLabel) : 'Please select an option' }}
        </div>
      }
    </div>
  `,
})
export class DropdownSmallPrimitiveComponent implements ControlValueAccessor {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  readonly valueChange = output<ValueChange>();

  readonly innerValue = signal<string>('');
  readonly touched = signal(false);

  // TODO(cross-cutting): remove as-any cast once FieldSchema has enumOptions
  readonly options = computed<DropdownOption[]>(() => {
    const raw = (this.schema() as unknown as { enumOptions?: DropdownOption[] }).enumOptions;
    return raw ?? [];
  });

  readonly labelId = `mee-ds-label-${Math.random().toString(36).slice(2)}`;

  private _onChange: (v: unknown) => void = () => {};
  private _onTouched: () => void = () => {};

  writeValue(val: unknown): void {
    this.innerValue.set(val != null ? String(val) : '');
  }

  registerOnChange(fn: (v: unknown) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  onSelectionChange(event: MatRadioChange): void {
    this.touched.set(true);
    this.innerValue.set(event.value);
    this._onChange(event.value);
    this._onTouched();
    this.valueChange.emit({
      canonicalName: this.schema().canonicalName,
      value: event.value,
      source: 'seller',
    });
  }
}

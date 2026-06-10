// features/catalog-form/primitives/currency/currency.component.ts
// Primitive 5: INR currency input per §18.E
// Prefix ₹, raw number editing on focus, formatted display on blur.
// Implements ControlValueAccessor. Emits ValueChange on blur.

import {
  ChangeDetectionStrategy,
  Component,
  forwardRef,
  input,
  output,
  signal,
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { LocaleLabelPipe } from '@shared/pipes/locale-label.pipe';
import { ValueChange } from '../primitive.contract';

@Component({
  selector: 'mee-currency',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, MatFormFieldModule, MatInputModule, LocaleLabelPipe],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CurrencyPrimitiveComponent),
      multi: true,
    },
  ],
  template: `
    <mat-form-field appearance="outline" class="w-full">
      <mat-label>
        {{ schema().displayLabel | localeLabel }}
        @if (schema().marker === 'compulsory') {
          <span style="color:var(--mee-color-error)" aria-hidden="true"> *</span>
        }
      </mat-label>
      <span matPrefix>₹&nbsp;</span>
      <input
        matInput
        type="number"
        step="0.01"
        [value]="innerValue()"
        [disabled]="disabled()"
        [min]="schema().minValue ?? null"
        [max]="schema().maxValue ?? null"
        [placeholder]="schema().displayPlaceholder | localeLabel"
        (input)="onInput($event)"
        (blur)="onBlur()"
      />
      @if (schema().displayHelp) {
        <mat-hint>{{ schema().displayHelp | localeLabel }}</mat-hint>
      }
      @if (touched() && innerValue() === null && schema().marker === 'compulsory') {
        <mat-error>{{ schema().validationMessage ? (schema().validationMessage | localeLabel) : 'This field is required' }}</mat-error>
      }
    </mat-form-field>
  `,
})
export class CurrencyPrimitiveComponent implements ControlValueAccessor {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  readonly valueChange = output<ValueChange>();

  readonly innerValue = signal<number | null>(null);
  readonly touched = signal(false);

  private _onChange: (v: unknown) => void = () => {};
  private _onTouched: () => void = () => {};

  writeValue(val: unknown): void {
    if (val === null || val === undefined || val === '') {
      this.innerValue.set(null);
    } else {
      const parsed = parseFloat(String(val));
      this.innerValue.set(isNaN(parsed) ? null : parsed);
    }
  }

  registerOnChange(fn: (v: unknown) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  onInput(event: Event): void {
    const raw = (event.target as HTMLInputElement).value;
    const parsed = raw === '' ? null : parseFloat(raw);
    this.innerValue.set(isNaN(parsed as number) ? null : parsed);
    this._onChange(this.innerValue());
  }

  onBlur(): void {
    this.touched.set(true);
    this._onTouched();
    this.valueChange.emit({
      canonicalName: this.schema().canonicalName,
      value: this.innerValue(),
      source: 'seller',
    });
  }
}

// features/catalog-form/primitives/text-short/text-short.component.ts
// Primitive 1: single-line text input per §18.E
// Implements ControlValueAccessor for CVA + emits ValueChange on blur.

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
  selector: 'mee-text-short',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, MatFormFieldModule, MatInputModule, LocaleLabelPipe],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => TextShortPrimitiveComponent),
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
      <input
        matInput
        [value]="innerValue()"
        [disabled]="disabled()"
        [attr.maxlength]="schema().maxLength ?? 524288"
        [placeholder]="schema().displayPlaceholder | localeLabel"
        (input)="onInput($event)"
        (blur)="onBlur()"
      />
      @if (schema().displayHelp) {
        <mat-hint>{{ schema().displayHelp | localeLabel }}</mat-hint>
      }
      @if (schema().maxLength) {
        <mat-hint align="end">{{ innerValue()?.length ?? 0 }} / {{ schema().maxLength }}</mat-hint>
      }
      @if (touched() && !innerValue() && schema().marker === 'compulsory') {
        <mat-error>{{ schema().validationMessage ? (schema().validationMessage | localeLabel) : 'This field is required' }}</mat-error>
      }
    </mat-form-field>
  `,
})
export class TextShortPrimitiveComponent implements ControlValueAccessor {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  readonly valueChange = output<ValueChange>();

  readonly innerValue = signal<string>('');
  readonly touched = signal(false);

  // CVA callbacks
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

  onInput(event: Event): void {
    const v = (event.target as HTMLInputElement).value;
    this.innerValue.set(v);
    this._onChange(v);
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

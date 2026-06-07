// features/catalog-form/primitives/address-group/address-group.component.ts
// Primitive 11: composite address group per §18.E
// Renders address_line_1, city, and pincode (6-digit validator).
// Implements ControlValueAccessor with object value: {address_line_1, city, pincode}.
// Emits ValueChange on each sub-field blur.

import {
  ChangeDetectionStrategy,
  Component,
  forwardRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import {
  AbstractControl,
  ControlValueAccessor,
  FormBuilder,
  FormGroup,
  NG_VALUE_ACCESSOR,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { TextFieldModule } from '@angular/cdk/text-field';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { LocaleLabelPipe } from '@shared/pipes/locale-label.pipe';
import { ValueChange } from '../primitive.contract';

export interface AddressValue {
  address_line_1: string;
  city: string;
  pincode: string;
}

/** Validates exactly 6 decimal digits. Returns null when valid or when value is empty. */
function pincodeValidator(control: AbstractControl): ValidationErrors | null {
  const v = control.value as string;
  if (!v) return null;
  return /^\d{6}$/.test(v) ? null : { pincode: true };
}

@Component({
  selector: 'mee-address-group',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, MatFormFieldModule, MatInputModule, TextFieldModule, LocaleLabelPipe],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => AddressGroupPrimitiveComponent),
      multi: true,
    },
  ],
  template: `
    <fieldset style="border:1px solid var(--mee-color-outline); border-radius:var(--mee-radius-sm); padding:12px 16px">
      <legend style="font-size:14px; color:var(--mee-color-on-surface); padding:0 4px">
        {{ schema().displayLabel | localeLabel }}
        @if (schema().marker === 'compulsory') {
          <span style="color:var(--mee-color-error)" aria-hidden="true"> *</span>
        }
      </legend>

      <div [formGroup]="form" class="flex flex-col gap-3">

        <!-- Address line 1 -->
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Address</mat-label>
          <textarea
            matInput
            cdkTextareaAutosize
            cdkAutosizeMinRows="2"
            cdkAutosizeMaxRows="4"
            formControlName="address_line_1"
            placeholder="Full address"
            [disabled]="disabled()"
            (blur)="onSubBlur()"
          ></textarea>
        </mat-form-field>

        <!-- City -->
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>City</mat-label>
          <input
            matInput
            formControlName="city"
            placeholder="City"
            [disabled]="disabled()"
            (blur)="onSubBlur()"
          />
        </mat-form-field>

        <!-- Pincode -->
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>Pincode</mat-label>
          <input
            matInput
            type="text"
            formControlName="pincode"
            placeholder="6-digit pincode"
            maxlength="6"
            inputmode="numeric"
            pattern="\\d{6}"
            [disabled]="disabled()"
            (blur)="onSubBlur()"
          />
          @if (form.get('pincode')?.touched && form.get('pincode')?.hasError('pincode')) {
            <mat-error>Please enter a valid 6-digit pincode</mat-error>
          }
        </mat-form-field>

      </div>

      @if (schema().displayHelp) {
        <div style="font-size:12px; color:var(--mee-color-on-surface); margin-top:4px">
          {{ schema().displayHelp | localeLabel }}
        </div>
      }
    </fieldset>
  `,
})
export class AddressGroupPrimitiveComponent implements ControlValueAccessor {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  readonly valueChange = output<ValueChange>();

  private readonly fb = inject(FormBuilder);

  readonly form: FormGroup = this.fb.group({
    address_line_1: ['', Validators.required],
    city: ['', Validators.required],
    pincode: ['', [Validators.required, pincodeValidator]],
  });

  private _onChange: (v: unknown) => void = () => {};
  private _onTouched: () => void = () => {};

  writeValue(val: unknown): void {
    if (val && typeof val === 'object') {
      const addr = val as Partial<AddressValue>;
      this.form.patchValue({
        address_line_1: addr.address_line_1 ?? '',
        city: addr.city ?? '',
        pincode: addr.pincode ?? '',
      }, { emitEvent: false });
    } else {
      this.form.reset({ address_line_1: '', city: '', pincode: '' }, { emitEvent: false });
    }
  }

  registerOnChange(fn: (v: unknown) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  onSubBlur(): void {
    this._onTouched();
    const currentValue: AddressValue = this.form.getRawValue() as AddressValue;
    this._onChange(currentValue);
    this.valueChange.emit({
      canonicalName: this.schema().canonicalName,
      value: currentValue,
      source: 'seller',
    });
  }
}

// features/auth/components/phone-input/phone-input.component.ts
// Reusable +91 phone input — ControlValueAccessor for use inside parent Reactive Forms.
// Standalone, OnPush, selector: mee-phone-input.

import {
  ChangeDetectionStrategy,
  Component,
  forwardRef,
  Input,
  signal,
} from '@angular/core';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR,
  ReactiveFormsModule,
} from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { TranslocoModule } from '@jsverse/transloco';

@Component({
  selector: 'mee-phone-input',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    TranslocoModule,
  ],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => PhoneInputComponent),
      multi: true,
    },
  ],
  template: `
    <mat-form-field appearance="outline" class="w-full">
      <mat-label>{{ label }}</mat-label>
      <div class="flex items-center">
        <span class="text-on-surface-variant mr-2 shrink-0 text-sm">+91</span>
        <input
          matInput
          type="tel"
          inputmode="numeric"
          [attr.aria-label]="label"
          [value]="displayValue()"
          (input)="onInput($event)"
          (blur)="onBlur()"
          placeholder="98765 43210"
          class="min-h-[44px]"
          maxlength="10"
        />
      </div>
      @if (touched() && !isValid()) {
        <mat-hint class="mee-phone-error text-red-600 text-xs" role="alert">
          {{ 'auth.phone.error.invalid' | transloco }}
        </mat-hint>
      }
    </mat-form-field>
  `,
})
export class PhoneInputComponent implements ControlValueAccessor {
  /** Transloco key resolved by parent and passed as plain string label */
  @Input() label = '';

  readonly displayValue = signal<string>('');
  readonly touched = signal<boolean>(false);

  // CVA plumbing
  private _onChange: (value: string) => void = () => {};
  private _onTouched: () => void = () => {};

  isValid(): boolean {
    return /^\d{10}$/.test(this.displayValue());
  }

  onInput(event: Event): void {
    const raw = (event.target as HTMLInputElement).value;
    // Strip non-digits, limit to 10 chars
    const digits = raw.replace(/\D/g, '').slice(0, 10);
    this.displayValue.set(digits);

    // Emit E.164 if valid, empty string if not — parent form decides validity
    const e164 = digits.length === 10 ? `+91${digits}` : '';
    this._onChange(e164);
  }

  onBlur(): void {
    this.touched.set(true);
    this._onTouched();
  }

  // ControlValueAccessor implementation

  writeValue(value: string | null): void {
    if (!value) {
      this.displayValue.set('');
      return;
    }
    // Accept E.164 (+91XXXXXXXXXX) or bare 10-digit
    const digits = value.startsWith('+91')
      ? value.slice(3)
      : value.replace(/\D/g, '').slice(0, 10);
    this.displayValue.set(digits);
  }

  registerOnChange(fn: (value: string) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  setDisabledState(_isDisabled: boolean): void {
    // Disabled state controlled by mat-form-field; no additional action needed
  }
}

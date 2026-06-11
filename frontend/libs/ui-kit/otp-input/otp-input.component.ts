import {
  ChangeDetectionStrategy,
  Component,
  forwardRef,
  input,
  output,
  signal,
} from '@angular/core';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR,
  FormsModule,
} from '@angular/forms';
import { InputOtp } from 'primeng/inputotp';

@Component({
  selector: 'mee-otp-input',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [InputOtp, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeeOtpInputComponent),
      multi: true,
    },
  ],
  template: `
    <p-inputotp
      [length]="length()"
      [integerOnly]="true"
      [ngModel]="innerValue()"
      (ngModelChange)="onOtpChange($event)"
      [style]="{ gap: '8px', minHeight: '44px' }"
    />
  `,
})
export class MeeOtpInputComponent implements ControlValueAccessor {
  readonly length = input<number>(6);
  readonly disabled = input<boolean>(false);

  readonly completed = output<string>();

  readonly innerValue = signal<string | null>(null);

  private _onChange: (v: string) => void = () => {};
  private _onTouched: () => void = () => {};

  onOtpChange(value: string | null): void {
    const val = value ?? '';
    this.innerValue.set(val);
    this._onChange(val);
    if (val.length === this.length()) {
      this.completed.emit(val);
    }
  }

  writeValue(value: string | null): void {
    this.innerValue.set(value ?? null);
  }

  registerOnChange(fn: (v: string) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  setDisabledState(_isDisabled: boolean): void {
    // Handled via input binding
  }
}

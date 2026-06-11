import {
  ChangeDetectionStrategy,
  Component,
  forwardRef,
  input,
  signal,
} from '@angular/core';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR,
  FormsModule,
} from '@angular/forms';
import { Password } from 'primeng/password';

@Component({
  selector: 'mee-password-input',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Password, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeePasswordInputComponent),
      multi: true,
    },
  ],
  template: `
    @if (label()) {
      <label class="block text-sm font-medium mb-1" style="color: var(--mee-color-on-surface)">
        {{ label() }}
      </label>
    }
    <p-password
      [ngModel]="innerValue()"
      (ngModelChange)="onModelChange($event)"
      [placeholder]="placeholder() ?? ''"
      [disabled]="disabled()"
      [toggleMask]="toggleMask()"
      [feedback]="feedback()"
      [fluid]="true"
      [style]="{ minHeight: '44px' }"
    />
  `,
})
export class MeePasswordInputComponent implements ControlValueAccessor {
  readonly label = input<string | undefined>(undefined);
  readonly placeholder = input<string | undefined>(undefined);
  readonly disabled = input<boolean>(false);
  readonly toggleMask = input<boolean>(true);
  readonly feedback = input<boolean>(false);

  readonly innerValue = signal<string>('');

  private _onChange: (v: string) => void = () => {};
  private _onTouched: () => void = () => {};

  onModelChange(value: string | null): void {
    const val = value ?? '';
    this.innerValue.set(val);
    this._onChange(val);
  }

  writeValue(value: string | null): void {
    this.innerValue.set(value ?? '');
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

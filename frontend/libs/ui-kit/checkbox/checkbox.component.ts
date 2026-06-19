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
  FormsModule,
  NG_VALUE_ACCESSOR,
} from '@angular/forms';
import { Checkbox } from 'primeng/checkbox';

/** CVA Pattern A — lean, no NgControl self-inject needed for checkbox/radio. */
@Component({
  selector: 'mee-checkbox',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Checkbox, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeeCheckboxComponent),
      multi: true,
    },
  ],
  template: `
    <div class="flex items-center gap-2">
      <p-checkbox
        [inputId]="cbId"
        [binary]="binary()"
        [value]="value()"
        [disabled]="disabled()"
        [invalid]="!!error()"
        [ngModel]="innerValue()"
        (ngModelChange)="onModelChange($event)"
        (onBlur)="onTouched()"
      />
      @if (label()) {
        <label
          [for]="cbId"
          class="text-sm select-none"
          style="color: var(--mee-color-on-surface); min-height: 44px; display: inline-flex; align-items: center; cursor: pointer;"
        >
          {{ label() }}
          @if (required()) {
            <span aria-hidden="true" style="color: var(--mee-color-error)"> *</span>
          }
        </label>
      }
    </div>
    @if (error()) {
      <small role="alert" class="block mt-1 text-xs" style="color: var(--mee-color-error)">
        {{ error() }}
      </small>
    } @else if (hint()) {
      <small class="block mt-1 text-xs" style="color: var(--mee-color-on-surface-muted)">
        {{ hint() }}
      </small>
    }
  `,
})
export class MeeCheckboxComponent implements ControlValueAccessor {
  readonly label    = input<string | undefined>(undefined);
  readonly disabled = input<boolean>(false);
  readonly required = input<boolean>(false);
  readonly binary   = input<boolean>(true);
  readonly value    = input<unknown | undefined>(undefined);
  readonly error    = input<string | undefined>(undefined);
  readonly hint     = input<string | undefined>(undefined);

  /** Emits on every toggle alongside CVA propagation. */
  readonly changed = output<boolean>();

  readonly cbId = `mee-checkbox-${Math.random().toString(36).slice(2)}`;
  readonly innerValue = signal<boolean>(false);

  private _onChange: (v: boolean) => void = () => {};
  private _onTouched: () => void = () => {};

  onModelChange(value: boolean): void {
    this.innerValue.set(value);
    this._onChange(value);
    this.changed.emit(value);
  }

  onTouched(): void {
    this._onTouched();
  }

  writeValue(value: boolean | null): void {
    this.innerValue.set(value ?? false);
  }

  registerOnChange(fn: (v: boolean) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  setDisabledState(_isDisabled: boolean): void {
    // Handled via disabled() input binding
  }
}

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
import { InputNumber } from 'primeng/inputnumber';
import { Tooltip } from 'primeng/tooltip';
import { meeIconClass } from '../icon/icon.registry';

@Component({
  selector: 'mee-input-number',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [InputNumber, Tooltip, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeeInputNumberComponent),
      multi: true,
    },
  ],
  template: `
    @if (label()) {
      <label [for]="inputId" class="flex items-center gap-1 text-sm font-medium mb-1" style="color: var(--mee-color-on-surface)">
        <span>{{ label() }}</span>
        @if (required()) {
          <span aria-hidden="true" style="color: var(--mee-color-error)"> *</span>
        }
        @if (tooltip()) {
          <i [class]="helpIconClass"
             style="color: var(--mee-color-on-surface-muted); cursor: help;"
             [pTooltip]="tooltip()!"
             tooltipPosition="top"
             [tooltipOptions]="{ tooltipStyleClass: 'mee-help-tooltip' }"
             tabindex="0"
             [attr.aria-label]="'Help: ' + tooltip()"
             role="img"></i>
        }
      </label>
    }
    <p-inputNumber
      [ngModel]="innerValue()"
      (ngModelChange)="onModelChange($event)"
      (onBlur)="onBlur()"
      [showButtons]="false"
      [useGrouping]="false"
      [disabled]="disabled()"
      [invalid]="!!error()"
      [inputStyleClass]="inputStyleClass()"
      [inputId]="inputId"
      [attr.data-testid]="testId()"
    />
    @if (error()) {
      <small role="alert" style="color: var(--mee-color-error)" class="block mt-1 text-xs">
        {{ error() }}
      </small>
    }
  `,
})
export class MeeInputNumberComponent implements ControlValueAccessor {
  readonly label          = input<string | undefined>(undefined);
  readonly tooltip        = input<string | undefined>(undefined);
  readonly error          = input<string | undefined>(undefined);
  readonly required       = input<boolean>(false);
  readonly disabled       = input<boolean>(false);
  readonly testId         = input<string | undefined>(undefined);
  /** Tailwind / PrimeNG class applied to the inner <input> for width sizing. */
  readonly inputStyleClass = input<string>('w-full');

  /** Emits the numeric value (or null) whenever the model changes. */
  readonly value_change = output<number | null>();
  /** Emits the numeric value (or null) on blur. */
  readonly blur = output<number | null>();

  readonly inputId = `mee-input-number-${Math.random().toString(36).slice(2)}`;
  readonly innerValue = signal<number | null>(null);

  /** FE-2: help-tooltip icon class resolved via the icon registry (no raw literal). */
  protected readonly helpIconClass = meeIconClass('info-circle') + ' text-xs';

  private _onChange: (v: number | null) => void = () => {};
  private _onTouched: () => void = () => {};

  onModelChange(value: number | null): void {
    this.innerValue.set(value);
    this._onChange(value);
    this.value_change.emit(value);
  }

  onBlur(): void {
    this._onTouched();
    this.blur.emit(this.innerValue());
  }

  writeValue(value: number | null): void {
    this.innerValue.set(value ?? null);
  }

  registerOnChange(fn: (v: number | null) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  setDisabledState(_isDisabled: boolean): void {
    // Handled via disabled() input binding
  }
}

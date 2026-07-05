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
import { InputText } from 'primeng/inputtext';
import { Tooltip } from 'primeng/tooltip';
import type { MeeInputType } from './input.types';
import { meeIconClass } from '../icon/icon.registry';

@Component({
  selector: 'mee-input',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [InputText, Tooltip, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeeInputComponent),
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
    <div class="relative flex items-center">
      @if (prefix()) {
        <span class="absolute left-3 text-sm select-none" style="color: var(--mee-color-on-surface-muted)">
          {{ prefix() }}
        </span>
      }
      <input
        pInputText
        [id]="inputId"
        [type]="type()"
        [placeholder]="placeholder()"
        [disabled]="disabled()"
        [class]="prefix() ? 'pl-10 w-full' : 'w-full'"
        [invalid]="!!error()"
        [ngModel]="innerValue()"
        (ngModelChange)="onModelChange($event)"
        (blur)="onBlur()"
        style="min-height: 44px;"
        [attr.data-testid]="testId()"
      />
    </div>
    @if (error()) {
      <small role="alert" style="color: var(--mee-color-error)" class="block mt-1 text-xs">
        {{ error() }}
      </small>
    } @else if (hint()) {
      <small class="block mt-1 text-xs" style="color: var(--mee-color-on-surface-muted)">
        {{ hint() }}
      </small>
    }
  `,
})
export class MeeInputComponent implements ControlValueAccessor {
  readonly label = input<string | undefined>(undefined);
  readonly placeholder = input<string>('');
  readonly type = input<MeeInputType>('text');
  readonly prefix = input<string | undefined>(undefined);
  readonly error = input<string | undefined>(undefined);
  readonly hint = input<string | undefined>(undefined);
  readonly disabled = input<boolean>(false);
  readonly required = input<boolean>(false);
  readonly testId = input<string | undefined>(undefined);
  readonly tooltip = input<string | undefined>(undefined);

  readonly blur = output<string>();

  readonly inputId = `mee-input-${Math.random().toString(36).slice(2)}`;
  readonly innerValue = signal<string>('');

  /** FE-2: help-tooltip icon class resolved via the icon registry (no raw literal). */
  protected readonly helpIconClass = meeIconClass('info-circle') + ' text-xs';

  private _onChange: (v: string) => void = () => {};
  private _onTouched: () => void = () => {};

  onModelChange(value: string): void {
    this.innerValue.set(value);
    this._onChange(value);
  }

  onTouched(): void {
    this._onTouched();
  }

  onBlur(): void {
    this._onTouched();
    this.blur.emit(this.innerValue());
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

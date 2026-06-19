/**
 * mee-radio — radio button GROUP wrapper (CVA Pattern A).
 *
 * RadioButtonGroup is NOT exported by primeng/radiobutton v21.
 * Fallback: shared [ngModel] across individual p-radiobutton instances.
 * Each p-radiobutton has a [value] binding; ngModel on each radio reflects
 * the currently selected value — PrimeNG's own CVA on RadioButton handles
 * the comparison. The group CVA seam is on this wrapper component.
 */
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
import { RadioButton } from 'primeng/radiobutton';
import type { MeeSelectOption } from '../select/select.types';

@Component({
  selector: 'mee-radio',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RadioButton, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeeRadioComponent),
      multi: true,
    },
  ],
  template: `
    @if (label()) {
      <span
        class="block text-sm font-medium mb-1"
        style="color: var(--mee-color-on-surface)"
      >
        {{ label() }}
        @if (required()) {
          <span aria-hidden="true" style="color: var(--mee-color-error)"> *</span>
        }
      </span>
    }
    <div [class]="direction() === 'row' ? 'flex gap-4' : 'flex flex-col gap-2'">
      @for (opt of options(); track opt.value; let i = $index) {
        <div class="flex items-center gap-2" style="min-height: 44px;">
          <p-radiobutton
            [inputId]="rId + '-' + i"
            [name]="rId"
            [value]="opt.value"
            [disabled]="disabled()"
            [ngModel]="innerValue()"
            (ngModelChange)="onModelChange($event)"
          />
          <label
            [for]="rId + '-' + i"
            class="text-sm select-none"
            style="color: var(--mee-color-on-surface); cursor: pointer;"
          >
            {{ opt.label }}
          </label>
        </div>
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
export class MeeRadioComponent implements ControlValueAccessor {
  readonly options   = input.required<MeeSelectOption[]>();
  readonly label     = input<string | undefined>(undefined);
  readonly disabled  = input<boolean>(false);
  readonly required  = input<boolean>(false);
  readonly direction = input<'row' | 'column'>('column');
  readonly error     = input<string | undefined>(undefined);
  readonly hint      = input<string | undefined>(undefined);

  /** Emits the selected value on each change. */
  readonly changed = output<unknown>();

  readonly rId = `mee-radio-${Math.random().toString(36).slice(2)}`;
  readonly innerValue = signal<unknown>(null);

  private _onChange: (v: unknown) => void = () => {};
  private _onTouched: () => void = () => {};

  onModelChange(value: unknown): void {
    this.innerValue.set(value);
    this._onChange(value);
    this.changed.emit(value);
  }

  onTouched(): void {
    this._onTouched();
  }

  writeValue(value: unknown): void {
    this.innerValue.set(value ?? null);
  }

  registerOnChange(fn: (v: unknown) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  setDisabledState(_isDisabled: boolean): void {
    // Handled via disabled() input binding
  }
}

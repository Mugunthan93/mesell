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
import { Select } from 'primeng/select';
import type { SelectChangeEvent } from 'primeng/select';
import type { MeeSelectOption } from './select.types';

@Component({
  selector: 'mee-select',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Select, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeeSelectComponent),
      multi: true,
    },
  ],
  styles: [`
    :host { display: block; }
    .mee-label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      margin-bottom: var(--mee-space-1);
      color: var(--mee-color-on-surface);
    }
    ::ng-deep p-select { display: block; width: 100%; }
    ::ng-deep p-select .p-select { min-height: 44px; width: 100%; }
    .mee-error {
      display: block;
      margin-top: var(--mee-space-1);
      font-size: 12px;
      color: var(--mee-color-error);
    }
  `],
  template: `
    @if (label()) {
      <label class="mee-label">
        {{ label() }}
      </label>
    }
    <p-select
      [options]="options()"
      [placeholder]="placeholder()"
      [disabled]="disabled()"
      optionLabel="label"
      optionValue="value"
      [ngModel]="innerValue()"
      (ngModelChange)="onSelectChange($event)"
    />
    @if (error()) {
      <small role="alert" class="mee-error">
        {{ error() }}
      </small>
    }
  `,
})
export class MeeSelectComponent implements ControlValueAccessor {
  readonly options = input.required<MeeSelectOption[]>();
  readonly placeholder = input<string>('Select');
  readonly disabled = input<boolean>(false);
  readonly label = input<string | undefined>(undefined);
  readonly error = input<string | undefined>(undefined);

  readonly value_change = output<unknown>();

  readonly innerValue = signal<unknown>(null);

  private _onChange: (v: unknown) => void = () => {};
  private _onTouched: () => void = () => {};

  onSelectChange(value: unknown): void {
    this.innerValue.set(value);
    this._onChange(value);
    this.value_change.emit(value);
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
    // Handled via input binding
  }
}

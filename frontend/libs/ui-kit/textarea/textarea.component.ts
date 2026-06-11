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
import { Textarea } from 'primeng/textarea';

@Component({
  selector: 'mee-textarea',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Textarea, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeeTextareaComponent),
      multi: true,
    },
  ],
  template: `
    @if (label()) {
      <label [for]="textareaId" class="block text-sm font-medium mb-1" style="color: var(--mee-color-on-surface)">
        {{ label() }}
        @if (required()) {
          <span aria-hidden="true" style="color: var(--mee-color-error)"> *</span>
        }
      </label>
    }
    <textarea
      pTextarea
      [id]="textareaId"
      [rows]="rows()"
      [placeholder]="placeholder()"
      [disabled]="disabled()"
      [autoResize]="autoResize()"
      [invalid]="!!error()"
      [ngModel]="innerValue()"
      (ngModelChange)="onModelChange($event)"
      (blur)="onTouched()"
      class="w-full"
      style="min-height: 44px;"
    ></textarea>
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
export class MeeTextareaComponent implements ControlValueAccessor {
  readonly label = input<string | undefined>(undefined);
  readonly placeholder = input<string>('');
  readonly rows = input<number>(4);
  readonly error = input<string | undefined>(undefined);
  readonly hint = input<string | undefined>(undefined);
  readonly disabled = input<boolean>(false);
  readonly required = input<boolean>(false);
  readonly autoResize = input<boolean>(false);

  readonly textareaId = `mee-textarea-${Math.random().toString(36).slice(2)}`;
  readonly innerValue = signal<string>('');

  private _onChange: (v: string) => void = () => {};
  private _onTouched: () => void = () => {};

  onModelChange(value: string): void {
    this.innerValue.set(value);
    this._onChange(value);
  }

  onTouched(): void {
    this._onTouched();
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

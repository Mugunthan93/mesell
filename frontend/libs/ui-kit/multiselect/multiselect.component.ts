import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  OnInit,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  ControlValueAccessor,
  FormsModule,
  NgControl,
  ValidationErrors,
} from '@angular/forms';
import { MultiSelect } from 'primeng/multiselect';
import { merge } from 'rxjs';
import type { MeeSelectOption } from '../select/select.types';

/** When to surface validation errors from the bound form control. */
export type MeeShowErrorOn = 'touched' | 'dirty' | 'always';

function resolveErrorMessage(errors: ValidationErrors): string {
  if (errors['required'])  return 'This field is required';
  if (errors['minlength']) return `At least ${errors['minlength'].requiredLength} items required`;
  if (errors['maxlength']) return `No more than ${errors['maxlength'].requiredLength} items allowed`;
  if (errors['min'])       return `Select at least ${errors['min'].min} item(s)`;
  if (errors['max'])       return `Select at most ${errors['max'].max} item(s)`;
  return 'Invalid selection';
}

@Component({
  selector: 'mee-multiselect',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MultiSelect, FormsModule],
  styles: [`
    :host { display: block; }
    .mee-label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      margin-bottom: var(--mee-space-1);
      color: var(--mee-color-on-surface);
    }
    .mee-required { color: var(--mee-color-error); }
    ::ng-deep p-multiselect { display: block; width: 100%; }
    ::ng-deep p-multiselect .p-multiselect { min-height: 44px; width: 100%; }
    ::ng-deep p-multiselect .p-multiselect-chip .p-chip {
      background: var(--mee-color-primary-light);
      color: var(--mee-color-primary);
      border-radius: var(--mee-radius-full);
      font-size: 12px;
      font-weight: 500;
    }
    .mee-error {
      display: block;
      margin-top: var(--mee-space-1);
      font-size: 12px;
      color: var(--mee-color-error);
    }
    .mee-hint {
      display: block;
      margin-top: var(--mee-space-1);
      font-size: 12px;
      color: var(--mee-color-on-surface-muted);
    }
  `],
  template: `
    @if (label()) {
      <label class="mee-label">
        {{ label() }}
        @if (required()) {
          <span aria-hidden="true" class="mee-required"> *</span>
        }
      </label>
    }
    <p-multiselect
      [options]="options()"
      [placeholder]="placeholder()"
      [disabled]="disabled()"
      [showClear]="showClear()"
      [maxSelectedLabels]="maxSelectedLabels()"
      [filter]="filter()"
      [display]="display()"
      optionLabel="label"
      optionValue="value"
      [invalid]="!!computedError()"
      [ngModel]="innerValue()"
      (ngModelChange)="onModelChange($event)"
      (onPanelHide)="onTouched()"
    />
    @if (computedError()) {
      <small role="alert" class="mee-error">{{ computedError() }}</small>
    } @else if (hint()) {
      <small class="mee-hint">{{ hint() }}</small>
    }
  `,
})
export class MeeMultiselectComponent implements ControlValueAccessor, OnInit {
  /** Injected NgControl — used instead of NG_VALUE_ACCESSOR provider to avoid circular dep. */
  private readonly ngControl = inject(NgControl, { optional: true, self: true });
  private readonly destroyRef = inject(DestroyRef);

  // ── Inputs ──────────────────────────────────────────────────────────────────
  readonly options          = input.required<MeeSelectOption[]>();
  readonly placeholder      = input<string>('Select options');
  readonly label            = input<string | undefined>(undefined);
  readonly error            = input<string | undefined>(undefined);
  readonly hint             = input<string | undefined>(undefined);
  readonly disabled         = input<boolean>(false);
  readonly required         = input<boolean>(false);
  readonly showClear        = input<boolean>(true);
  readonly maxSelectedLabels = input<number>(3);
  readonly filter           = input<boolean>(true);
  readonly display          = input<'comma' | 'chip'>('chip');
  /**
   * When to show validation errors from the bound form control.
   * - 'touched' (default) — after the user closes the panel at least once
   * - 'dirty'  — as soon as the selection changes
   * - 'always' — always show, even before interaction (useful after form submit)
   */
  readonly showErrorOn      = input<MeeShowErrorOn>('touched');

  // ── Internal state ───────────────────────────────────────────────────────────
  readonly innerValue = signal<unknown[]>([]);

  /** Reactive bridge: triggers `computedError` recomputation on status/value change. */
  private readonly _controlStatus = signal<string>('VALID');

  private _onChange: (v: unknown[]) => void = () => {};
  readonly onTouched: () => void = () => { this._onTouched(); };
  private _onTouched: () => void = () => {};

  constructor() {
    // Assign self as value accessor without providing NG_VALUE_ACCESSOR
    // (avoids ExpressionChangedAfterItHasBeenChecked / circular dep).
    if (this.ngControl) {
      this.ngControl.valueAccessor = this;
    }
  }

  ngOnInit(): void {
    const ctrl = this.ngControl?.control;
    if (ctrl) {
      merge(ctrl.statusChanges, ctrl.valueChanges)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe(() => this._controlStatus.set(ctrl.status));
    }
  }

  /** Resolved error message — explicit [error] input wins over auto-validator messages. */
  readonly computedError = computed<string | null>(() => {
    if (this.error()) return this.error()!;

    this._controlStatus(); // subscribe as reactive dependency

    const ctrl = this.ngControl?.control;
    if (!ctrl) return null;

    const on = this.showErrorOn();
    const shouldShow =
      on === 'always' ||
      (on === 'touched' && ctrl.touched) ||
      (on === 'dirty'   && ctrl.dirty);

    if (!shouldShow || ctrl.valid) return null;
    return resolveErrorMessage(ctrl.errors!);
  });

  // ── CVA ──────────────────────────────────────────────────────────────────────
  onModelChange(value: unknown[] | null): void {
    const val = value ?? [];
    this.innerValue.set(val);
    this._onChange(val);
  }

  writeValue(value: unknown[] | null): void {
    this.innerValue.set(value ?? []);
  }

  registerOnChange(fn: (v: unknown[]) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  setDisabledState(_isDisabled: boolean): void {
    // Disabled state handled reactively via the disabled() input binding.
  }
}

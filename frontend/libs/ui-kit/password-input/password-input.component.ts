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
import { Password } from 'primeng/password';
import { merge } from 'rxjs';

function resolveErrorMessage(errors: ValidationErrors): string {
  if (errors['required'])  return 'This field is required';
  if (errors['minlength']) return 'Password does not meet requirements';
  if (errors['maxlength']) return 'Password does not meet requirements';
  if (errors['pattern'])   return 'Password does not meet requirements';
  return 'Password does not meet requirements';
}

@Component({
  selector: 'mee-password-input',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Password, FormsModule],
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
    ::ng-deep p-password { display: block; width: 100%; }
    ::ng-deep p-password .p-password { display: flex; width: 100%; min-height: 44px; }
    ::ng-deep p-password .p-inputtext { min-height: 44px; width: 100%; flex: 1; }
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
    <p-password
      [ngModel]="innerValue()"
      (ngModelChange)="onModelChange($event)"
      [placeholder]="placeholder() ?? ''"
      [disabled]="disabled()"
      [toggleMask]="toggleMask()"
      [feedback]="feedback()"
      [fluid]="true"
      [invalid]="!!computedError()"
    />
    @if (computedError()) {
      <small role="alert" class="mee-error">{{ computedError() }}</small>
    } @else if (hint()) {
      <small class="mee-hint">{{ hint() }}</small>
    }
  `,
})
export class MeePasswordInputComponent implements ControlValueAccessor, OnInit {
  /** Injected NgControl — used instead of NG_VALUE_ACCESSOR provider to avoid circular dep. */
  private readonly ngControl  = inject(NgControl, { optional: true, self: true });
  private readonly destroyRef = inject(DestroyRef);

  // ── Inputs ──────────────────────────────────────────────────────────────────
  readonly label       = input<string | undefined>(undefined);
  readonly placeholder = input<string | undefined>(undefined);
  readonly disabled    = input<boolean>(false);
  readonly toggleMask  = input<boolean>(true);
  readonly feedback    = input<boolean>(false);
  readonly required    = input<boolean>(false);
  readonly hint        = input<string | undefined>(undefined);
  /**
   * When to show validation errors from the bound form control.
   * - 'touched' (default) — after the user blurs the field at least once
   * - 'dirty'  — as soon as the value changes
   * - 'always' — always show, even before interaction (useful after form submit)
   */
  readonly showErrorOn = input<'touched' | 'dirty' | 'always'>('touched');

  // ── Internal state ───────────────────────────────────────────────────────────
  readonly innerValue = signal<string>('');

  /** Reactive bridge: triggers `computedError` recomputation on status/value change. */
  private readonly _controlStatus = signal<string>('VALID');

  private _onChange:  (v: string) => void = () => {};
  private _onTouched: () => void           = () => {};

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
    // Disabled state handled reactively via the disabled() input binding.
  }
}

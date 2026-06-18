import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  OnInit,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  ControlValueAccessor,
  FormsModule,
  NgControl,
  ValidationErrors,
} from '@angular/forms';
import { Select } from 'primeng/select';
import type { SelectChangeEvent, SelectFilterEvent } from 'primeng/select';
import { Subject, debounceTime, merge } from 'rxjs';
import type { MeeSelectOption } from './select.types';

export type MeeShowErrorOn = 'touched' | 'dirty' | 'always';

function resolveErrorMessage(errors: ValidationErrors): string {
  if (errors['required'])  return 'This field is required';
  if (errors['minlength']) return `At least ${errors['minlength'].requiredLength} characters required`;
  if (errors['maxlength']) return `No more than ${errors['maxlength'].requiredLength} characters allowed`;
  if (errors['min'])       return `Value must be at least ${errors['min'].min}`;
  if (errors['max'])       return `Value must be at most ${errors['max'].max}`;
  return 'Invalid selection';
}

@Component({
  selector: 'mee-select',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Select, FormsModule],
  // NO providers[] — NgControl injected directly to avoid circular dep
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
    ::ng-deep p-select { display: block; width: 100%; }
    ::ng-deep p-select .p-select { min-height: 44px; width: 100%; }
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
    <p-select
      [options]="options()"
      [placeholder]="placeholder()"
      [disabled]="disabled()"
      [filter]="filter()"
      [virtualScroll]="virtualScroll()"
      [virtualScrollItemSize]="virtualScrollItemSize()"
      [loading]="loading()"
      optionLabel="label"
      optionValue="value"
      [invalid]="!!computedError()"
      [ngModel]="innerValue()"
      (ngModelChange)="onSelectChange($event)"
      (onChange)="value_change.emit($event.value)"
      (onFilter)="onFilter($event)"
      (onHide)="onTouched()"
    />
    @if (computedError()) {
      <small role="alert" class="mee-error">{{ computedError() }}</small>
    } @else if (hint()) {
      <small class="mee-hint">{{ hint() }}</small>
    }
  `,
})
export class MeeSelectComponent implements ControlValueAccessor, OnInit {
  private readonly ngControl      = inject(NgControl, { optional: true, self: true });
  private readonly destroyRef     = inject(DestroyRef);

  // ── Inputs ────────────────────────────────────────────────────────────────────
  readonly options              = input.required<MeeSelectOption[]>();
  readonly placeholder          = input<string>('Select');
  readonly disabled             = input<boolean>(false);
  readonly label                = input<string | undefined>(undefined);
  readonly error                = input<string | undefined>(undefined);
  readonly hint                 = input<string | undefined>(undefined);
  readonly required             = input<boolean>(false);
  readonly showErrorOn          = input<MeeShowErrorOn>('touched');
  /** Show filter input inside the dropdown. */
  readonly filter               = input<boolean>(false);
  /** Enable PrimeNG virtual scroll for large option lists (e.g. 3,772 categories). */
  readonly virtualScroll        = input<boolean>(false);
  /** Row height in px — must match actual option height for virtual scroll accuracy. */
  readonly virtualScrollItemSize = input<number>(38);
  /** Show loading spinner in the dropdown trigger. */
  readonly loading              = input<boolean>(false);
  /**
   * Debounce time in ms for server-side filter events.
   * Only applies when filter=true. Parent receives (search) output.
   */
  readonly filterDebounce       = input<number>(300);

  // ── Outputs ───────────────────────────────────────────────────────────────────
  /** Emits the selected value on change (mirrors formControl value). */
  readonly value_change = output<unknown>();
  /**
   * Emits the debounced filter query string for server-side search.
   * Parent should update [options] in response. Empty string = reset to full list.
   */
  readonly search = output<string>();

  // ── Internal state ─────────────────────────────────────────────────────────────
  readonly innerValue             = signal<unknown>(null);
  private readonly _controlStatus = signal<string>('VALID');
  private readonly _filterSubject = new Subject<string>();

  private _onChange: (v: unknown) => void = () => {};
  private _onTouched: () => void = () => {};
  readonly onTouched = () => this._onTouched();

  constructor() {
    if (this.ngControl) this.ngControl.valueAccessor = this;
  }

  ngOnInit(): void {
    const ctrl = this.ngControl?.control;
    if (ctrl) {
      merge(ctrl.statusChanges, ctrl.valueChanges)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe(() => this._controlStatus.set(ctrl.status));
    }
    // Wire debounced search — takeUntilDestroyed handles cleanup
    this._filterSubject
      .pipe(debounceTime(this.filterDebounce()), takeUntilDestroyed(this.destroyRef))
      .subscribe(q => this.search.emit(q));
  }

  readonly computedError = computed<string | null>(() => {
    if (this.error()) return this.error()!;
    this._controlStatus();
    const ctrl = this.ngControl?.control;
    if (!ctrl) return null;
    const on = this.showErrorOn();
    const shouldShow = on === 'always' || (on === 'touched' && ctrl.touched) || (on === 'dirty' && ctrl.dirty);
    if (!shouldShow || ctrl.valid) return null;
    return resolveErrorMessage(ctrl.errors!);
  });

  onSelectChange(value: unknown): void {
    this.innerValue.set(value);
    this._onChange(value);
  }

  onFilter(event: SelectFilterEvent): void {
    this._filterSubject.next(event.filter ?? '');
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

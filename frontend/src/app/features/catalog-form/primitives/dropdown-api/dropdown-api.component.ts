// features/catalog-form/primitives/dropdown-api/dropdown-api.component.ts
// Primitive 9: server-side debounced autocomplete per §18.E
// PrimitiveKind: 'dropdown_api_search' — selector: mee-dropdown-api
// Implements ControlValueAccessor. Emits ValueChange on option selection.

import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  forwardRef,
  inject,
  input,
  OnInit,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule, MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute } from '@angular/router';
import { Subject, switchMap, debounceTime, distinctUntilChanged, of, catchError } from 'rxjs';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { LocaleLabelPipe } from '@shared/pipes/locale-label.pipe';
import { ValueChange } from '../primitive.contract';
import { EnumLookupService, EnumValue } from '../../enum-lookup.service';

@Component({
  selector: 'mee-dropdown-api',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    MatProgressSpinnerModule,
    LocaleLabelPipe,
  ],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => DropdownApiPrimitiveComponent),
      multi: true,
    },
  ],
  template: `
    <mat-form-field appearance="outline" class="w-full">
      <mat-label>
        {{ schema().displayLabel | localeLabel }}
        @if (schema().marker === 'compulsory') {
          <span style="color:var(--mee-color-error)" aria-hidden="true"> *</span>
        }
      </mat-label>
      <input
        matInput
        [matAutocomplete]="autoApi"
        [value]="displayText()"
        [disabled]="disabled()"
        [placeholder]="schema().displayPlaceholder | localeLabel"
        (input)="onSearchInput($event)"
        (blur)="onBlur()"
      />
      @if (loading()) {
        <mat-spinner matSuffix diameter="16" style="margin-right:8px"></mat-spinner>
      }
      <mat-autocomplete #autoApi="matAutocomplete" (optionSelected)="onOptionSelected($event)">
        @for (option of options(); track option.code) {
          <mat-option [value]="option.code" style="min-height:44px">
            {{ option.label }}
          </mat-option>
        }
      </mat-autocomplete>
      @if (schema().displayHelp) {
        <mat-hint>{{ schema().displayHelp | localeLabel }}</mat-hint>
      }
      @if (touched() && !innerValue() && schema().marker === 'compulsory') {
        <mat-error>{{ schema().validationMessage ? (schema().validationMessage | localeLabel) : 'Please select an option' }}</mat-error>
      }
    </mat-form-field>
  `,
})
export class DropdownApiPrimitiveComponent implements ControlValueAccessor, OnInit {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  readonly valueChange = output<ValueChange>();

  readonly innerValue = signal<string>('');
  readonly displayText = signal<string>('');
  readonly options = signal<EnumValue[]>([]);
  readonly loading = signal(false);
  readonly touched = signal(false);

  private readonly enumLookup = inject(EnumLookupService);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly search$ = new Subject<string>();

  private _onChange: (v: unknown) => void = () => {};
  private _onTouched: () => void = () => {};

  ngOnInit(): void {
    const categoryId = this.route.snapshot.params['id'] as string | undefined;
    if (!categoryId) {
      console.warn(`[mee-dropdown-api] No categoryId in route params for field "${this.schema().canonicalName}". Showing empty list.`);
    }

    this.search$
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap(query => {
          if (!categoryId) return of([]);
          this.loading.set(true);
          return this.enumLookup
            .lookupEnum(categoryId, this.schema().canonicalName, query)
            .pipe(catchError(() => of([])));
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(results => {
        this.loading.set(false);
        this.options.set(results);
      });
  }

  writeValue(val: unknown): void {
    const str = val != null ? String(val) : '';
    this.innerValue.set(str);
    this.displayText.set(str);
  }

  registerOnChange(fn: (v: unknown) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  onSearchInput(event: Event): void {
    const q = (event.target as HTMLInputElement).value;
    this.displayText.set(q);
    this.innerValue.set('');
    this.search$.next(q);
  }

  onOptionSelected(event: MatAutocompleteSelectedEvent): void {
    const code = event.option.value as string;
    const label = event.option.viewValue;
    this.innerValue.set(code);
    this.displayText.set(label);
    this.touched.set(true);
    this._onChange(code);
    this._onTouched();
    this.valueChange.emit({
      canonicalName: this.schema().canonicalName,
      value: code,
      source: 'seller',
    });
  }

  onBlur(): void {
    this.touched.set(true);
    this._onTouched();
  }
}

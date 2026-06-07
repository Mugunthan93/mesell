// features/catalog-form/primitives/dropdown-medium/dropdown-medium.component.ts
// Primitive 7: 21-100 options with in-memory autocomplete filter per §18.E
// Implements ControlValueAccessor. Emits ValueChange on option selection.
//
// ENUM OPTIONS SOURCE: same as dropdown-small — uses (schema() as any).enumOptions.
// TODO(cross-cutting): add `enumOptions?: Array<{code: string; label: LocaleMap}>` to
// FieldSchema once the core model is updated.

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  forwardRef,
  input,
  output,
  signal,
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule, MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { LocaleLabelPipe } from '@shared/pipes/locale-label.pipe';
import { LocaleMap } from '@core/models/locale-map.model';
import { ValueChange } from '../primitive.contract';

export interface DropdownOption {
  readonly code: string;
  readonly label: LocaleMap;
}

@Component({
  selector: 'mee-dropdown-medium',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    LocaleLabelPipe,
  ],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => DropdownMediumPrimitiveComponent),
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
        [matAutocomplete]="auto"
        [value]="displayText()"
        [disabled]="disabled()"
        [placeholder]="schema().displayPlaceholder | localeLabel"
        (input)="onSearchInput($event)"
        (blur)="onBlur()"
      />
      <mat-autocomplete #auto="matAutocomplete" (optionSelected)="onOptionSelected($event)">
        @for (option of filteredOptions(); track option.code) {
          <mat-option [value]="option.code" style="min-height:44px">
            {{ option.label | localeLabel }}
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
export class DropdownMediumPrimitiveComponent implements ControlValueAccessor {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  readonly valueChange = output<ValueChange>();

  readonly innerValue = signal<string>('');
  readonly searchQuery = signal<string>('');
  readonly touched = signal(false);

  // TODO(cross-cutting): remove as-any cast once FieldSchema has enumOptions
  private readonly allOptions = computed<DropdownOption[]>(() => {
    const raw = (this.schema() as unknown as { enumOptions?: DropdownOption[] }).enumOptions;
    return raw ?? [];
  });

  readonly filteredOptions = computed<DropdownOption[]>(() => {
    const q = this.searchQuery().toLowerCase();
    if (!q) return this.allOptions();
    return this.allOptions().filter(o => {
      const label = o.label['en'] ?? '';
      return label.toLowerCase().includes(q);
    });
  });

  /** Display text: the label of the selected option, or the raw search query */
  readonly displayText = computed<string>(() => {
    const code = this.innerValue();
    if (!code) return this.searchQuery();
    const found = this.allOptions().find(o => o.code === code);
    return found ? (found.label['en'] ?? '') : code;
  });

  private _onChange: (v: unknown) => void = () => {};
  private _onTouched: () => void = () => {};

  writeValue(val: unknown): void {
    this.innerValue.set(val != null ? String(val) : '');
    this.searchQuery.set('');
  }

  registerOnChange(fn: (v: unknown) => void): void {
    this._onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this._onTouched = fn;
  }

  onSearchInput(event: Event): void {
    const q = (event.target as HTMLInputElement).value;
    this.searchQuery.set(q);
    // Clear selected value if user types something new
    if (q !== this.displayText()) {
      this.innerValue.set('');
    }
  }

  onOptionSelected(event: MatAutocompleteSelectedEvent): void {
    const code = event.option.value as string;
    this.innerValue.set(code);
    this.searchQuery.set('');
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

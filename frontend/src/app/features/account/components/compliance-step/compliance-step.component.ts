// features/account/components/compliance-step/compliance-step.component.ts
// Phase 3 rendering unit inside the onboarding wizard.
// Receives a list of FieldSpec objects (from GET /api/v1/seller-profile/required-fields)
// and dynamically renders a reactive form for one super-category's compliance fields.
// One instance per declared super-category.
//
// NOTE: Will be moved to shared/components/compliance-step/ by the cross-cutting session.

import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  inject,
} from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { TranslocoPipe } from '@jsverse/transloco';

// TODO(cross-cutting): align with @core/models when cross-cutting fixes field-schema.model.ts
// @core/models/field-schema.model.ts#FieldSchema models the catalog wizard field shape
// (canonicalName, primitive, PrimitiveKind, StepId, LocaleMap, etc.) — a completely different
// contract from the compliance required-fields FieldSpec shape below.
// The backend's RequiredFieldsResponse.extension_fields uses this FieldSpec per §8.E.
export interface FieldSpec {
  readonly field_name: string;        // e.g. "fssai_license_number"
  readonly display_name: string;      // e.g. "FSSAI License Number"
  readonly display_help: string;      // e.g. "Your FSSAI licence issued by the Food Safety authority"
  readonly field_type: 'text' | 'date' | 'select';
  readonly required: boolean;
  readonly options: string[] | null;  // only present when field_type === 'select'
}

/** Component-level constant for super-category ID → display name mapping. */
const CATEGORY_NAMES: Record<string, string> = {
  '26': 'Grocery',
  '13': 'Kids & Baby',
  '16': 'Electronics',
  '19': 'Beauty & Health',
  '80': 'Books & Stationery',
  '30': 'Home & Appliances',
};

@Component({
  selector: 'mee-compliance-step',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    TranslocoPipe,
  ],
  template: `
    <div class="space-y-4">
      <!-- Step header -->
      <div class="flex items-center gap-2 mb-2">
        <mat-icon class="text-primary">verified_user</mat-icon>
        <h3 class="text-mee-lg font-semibold text-on-surface">
          {{ 'onboarding.compliance.title' | transloco : { category: categoryName } }}
        </h3>
      </div>

      @if (form) {
        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="space-y-4" novalidate>
          @for (field of fields; track field.field_name) {
            <mat-form-field appearance="outline" class="w-full">
              <mat-label>{{ field.display_name }}</mat-label>

              @if (field.field_type === 'select' && field.options?.length) {
                <mat-select [formControlName]="field.field_name">
                  @for (opt of field.options!; track opt) {
                    <mat-option [value]="opt">{{ opt }}</mat-option>
                  }
                </mat-select>
              } @else if (field.field_type === 'date') {
                <input matInput type="date" [formControlName]="field.field_name" />
              } @else {
                <input matInput type="text" [formControlName]="field.field_name" />
              }

              <!-- Philosophy F5: every field must render display_help as mat-hint. No exceptions. -->
              <mat-hint>{{ field.display_help }}</mat-hint>

              @if (form.get(field.field_name)?.invalid && form.get(field.field_name)?.touched) {
                <mat-error>{{ 'onboarding.compliance.fieldRequired' | transloco }}</mat-error>
              }
            </mat-form-field>
          }

          <!-- Actions -->
          <div class="flex justify-between gap-2 pt-2">
            <button type="button" mat-stroked-button (click)="formBack.emit()">
              {{ 'onboarding.actions.back' | transloco }}
            </button>
            <button type="submit" mat-flat-button color="primary" [disabled]="saving">
              @if (saving) {
                <mat-spinner diameter="16" class="inline-block mr-2"></mat-spinner>
              }
              {{ 'onboarding.compliance.save' | transloco }}
            </button>
          </div>
        </form>
      }
    </div>
  `,
})
export class ComplianceStepComponent implements OnChanges {
  private readonly fb = inject(FormBuilder);

  @Input({ required: true }) superCategoryId!: string;
  @Input({ required: true }) fields!: FieldSpec[];
  /** Pre-filled completion map: field_name → true when already saved. */
  @Input() completed: Record<string, boolean> = {};
  @Input() saving = false;

  @Output() readonly formSubmit = new EventEmitter<Record<string, string | null>>();
  @Output() readonly formBack = new EventEmitter<void>();

  form!: FormGroup;

  get categoryName(): string {
    return CATEGORY_NAMES[this.superCategoryId] ?? this.superCategoryId;
  }

  ngOnChanges(): void {
    if (!this.fields?.length) return;
    const controls: Record<string, AbstractControl> = {};
    for (const field of this.fields) {
      const initial = this.completed[field.field_name] ? '' : null;
      controls[field.field_name] = new FormControl(
        initial,
        field.required ? [Validators.required] : [],
      );
    }
    this.form = this.fb.group(controls);
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.formSubmit.emit(this.form.value as Record<string, string | null>);
  }
}

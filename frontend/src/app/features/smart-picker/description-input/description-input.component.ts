// features/smart-picker/description-input/description-input.component.ts
// Reactive Form input for product description — emits on valid submit
// Per AC-2: min 10 chars, disabled while loading, i18n via Transloco

import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input,
  output,
} from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { TranslocoModule } from '@jsverse/transloco';

@Component({
  selector: 'mee-description-input',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    TranslocoModule,
  ],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()" class="flex flex-col gap-3">
      <mat-form-field appearance="outline" class="w-full">
        <mat-label>{{ 'smartPicker.description.placeholder' | transloco }}</mat-label>
        <textarea
          matInput
          formControlName="description"
          rows="3"
          [placeholder]="'smartPicker.description.placeholder' | transloco"
          class="min-h-[88px]"
        ></textarea>
        @if (descCtrl.invalid && descCtrl.touched) {
          <mat-error>
            {{ 'smartPicker.description.minLengthError' | transloco }}
          </mat-error>
        }
      </mat-form-field>

      <button
        mat-raised-button
        color="primary"
        type="submit"
        [disabled]="disabled() || form.invalid"
        class="min-h-[44px] w-full"
      >
        {{ 'smartPicker.description.submitLabel' | transloco }}
      </button>
    </form>
  `,
})
export class DescriptionInputComponent {
  /** True while parent state is loading — disables the form */
  readonly disabled = input(false);

  /** Emits the description string when form is valid and submitted */
  readonly descriptionSubmit = output<string>();

  private readonly fb = inject(FormBuilder);

  readonly form = this.fb.group({
    description: ['', [Validators.required, Validators.minLength(10)]],
  });

  get descCtrl() {
    return this.form.controls.description;
  }

  onSubmit(): void {
    if (this.form.invalid || this.disabled()) return;
    this.descriptionSubmit.emit(this.descCtrl.value ?? '');
  }
}

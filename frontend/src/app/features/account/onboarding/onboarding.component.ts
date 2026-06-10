import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';
import { AuthLayoutComponent } from '../../../layouts/auth-layout/auth-layout.component';
import {
  MeeButtonComponent,
  MeeInputComponent,
  MeeStepsComponent,
} from '../../../ui';
import type { MeeStep } from '../../../ui';

/** GST pattern: 15-char GSTIN format */
const GST_PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

/** Validator that only applies GST pattern when the field has a non-empty value. */
export function optionalGstValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = (control.value as string | null | undefined) ?? '';
    if (!value.trim()) return null;
    return GST_PATTERN.test(value) ? null : { gstPattern: true };
  };
}

@Component({
  selector: 'mee-onboarding',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    AuthLayoutComponent,
    MeeStepsComponent,
    MeeInputComponent,
    MeeButtonComponent,
  ],
  template: `
    <mee-auth-layout>
      <!-- Decorative progress indicator -->
      <mee-steps
        [steps]="steps"
        [active_index]="1"
      />

      <div class="mt-6 mb-4">
        <h1
          class="text-center font-bold"
          style="font-size: 22px; color: var(--mee-color-on-surface);"
        >
          Set up your business
        </h1>
        <p
          class="text-center mt-1"
          style="font-size: 14px; color: var(--mee-color-on-surface-muted);"
        >
          Tell us about your shop
        </p>
      </div>

      <form [formGroup]="form" (ngSubmit)="onSubmit()" novalidate class="flex flex-col gap-4">

        <mee-input
          [label]="'Business / Shop Name'"
          [required]="true"
          [error]="businessNameError()"
          formControlName="businessName"
        />

        <mee-input
          [label]="'City'"
          [required]="true"
          [error]="cityError()"
          formControlName="city"
        />

        <mee-input
          [label]="'GST Number (optional)'"
          [error]="gstError()"
          formControlName="gstNumber"
        />

        <mee-button
          [label]="'Save & Continue'"
          [loading]="loading()"
          [disabled]="form.invalid || loading()"
          [fullWidth]="true"
          [variant]="'primary'"
          (clicked)="onSubmit()"
        />

      </form>

      <p
        class="text-center mt-4"
        style="font-size: 12px; color: var(--mee-color-on-surface-muted);"
      >
        You can update this later.
      </p>
    </mee-auth-layout>
  `,
})
export class OnboardingComponent {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);

  readonly steps: MeeStep[] = [
    { label: 'Account' },
    { label: 'Business' },
    { label: 'Done' },
  ];

  readonly loading = signal<boolean>(false);
  readonly submitted = signal<boolean>(false);

  readonly form = this.fb.group({
    businessName: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    city: ['Tirupur', [Validators.required, Validators.maxLength(60)]],
    gstNumber: ['', [optionalGstValidator()]],
  });

  readonly businessNameError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('businessName');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['required']) return 'Business name is required.';
    if (ctrl.errors['minlength']) return 'Business name must be at least 2 characters.';
    if (ctrl.errors['maxlength']) return 'Business name must be 100 characters or fewer.';
    return undefined;
  });

  readonly cityError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('city');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['required']) return 'City is required.';
    if (ctrl.errors['maxlength']) return 'City must be 60 characters or fewer.';
    return undefined;
  });

  readonly gstError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('gstNumber');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['gstPattern']) return 'Enter a valid 15-character GSTIN (e.g. 29ABCDE1234F1Z5).';
    return undefined;
  });

  onSubmit(): void {
    this.submitted.set(true);
    if (this.form.invalid || this.loading()) return;
    this.loading.set(true);
    setTimeout(() => {
      this.loading.set(false);
      void this.router.navigate(['/dashboard']);
    }, 1500);
  }
}

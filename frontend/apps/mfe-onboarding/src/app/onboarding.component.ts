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
import { AuthLayoutComponent } from '@mesell/composites';
import {
  MeeButtonComponent,
  MeeInputComponent,
  MeeStepsComponent,
} from '@mesell/ui-kit';
import type { MeeStep } from '@mesell/ui-kit';

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
  styles: [`
    /* ── Steps wrap ─────────────────────────────────────────────────────────
       Prevent PrimeNG p-steps from overflowing the auth card at 360px.
       Step labels are short but PrimeNG renders a full-width flex row — clip cleanly. */
    .steps-wrap {
      overflow: hidden;
      width: 100%;
      margin-bottom: var(--mee-space-4);
    }

    /* Truncate individual step labels that are too wide for their cell. */
    ::ng-deep .steps-wrap .p-steps-item .p-menuitem-link .p-steps-title {
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 64px;
    }

    /* ── Section heading ────────────────────────────────────────────────────
       h1 + subtitle live in .section-heading block. */
    .section-heading {
      margin-top: var(--mee-space-6);
      margin-bottom: 0;
      text-align: center;
    }

    h1 {
      font-size: 22px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      text-align: center;
      margin: 0 0 var(--mee-space-1);
    }

    .section-subtitle {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      text-align: center;
      margin: 0 0 var(--mee-space-6);
    }

    /* ── Form fields ────────────────────────────────────────────────────────
       Vertical stack with consistent spacing between fields. */
    .form-fields {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
    }

    /* ── Hint text ──────────────────────────────────────────────────────────
       Fallback hint paragraph — used when mee-input hint slot is not available. */
    .hint-text {
      font-size: 12px;
      color: var(--mee-color-on-surface-muted);
      margin-top: var(--mee-space-1);
      margin-bottom: 0;
    }

    /* ── Skip footer ────────────────────────────────────────────────────────
       "I'll set this up later" link below the submit button. */
    .skip-text {
      text-align: center;
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
      margin-top: var(--mee-space-4);
      margin-bottom: 0;
    }

    .skip-link {
      color: var(--mee-color-primary);
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      transition: color var(--mee-transition-fast);
      /* Touch target: inline-flex with min-height ensures >= 44px tap area on mobile */
      min-height: 44px;
      display: inline-flex;
      align-items: center;
    }

    .skip-link:hover {
      text-decoration: underline;
    }
  `],
  template: `
    <mee-auth-layout>
      <!-- Progress indicator.
           Wrapped in .steps-wrap to constrain PrimeNG step label overflow at 360px. -->
      <div class="steps-wrap">
        <mee-steps
          [steps]="steps"
          [active_index]="1"
        />
      </div>

      <!-- Section heading: title + subtitle -->
      <div class="section-heading">
        <h1>Set up your business</h1>
        <p class="section-subtitle">Tell us about your shop</p>
      </div>

      <form [formGroup]="form" (ngSubmit)="onSubmit()" novalidate class="form-fields">

        <mee-input
          [label]="'Business / Shop Name'"
          [required]="true"
          [error]="businessNameError()"
          [testId]="'onboarding-business-name'"
          formControlName="businessName"
        />

        <mee-input
          [label]="'City'"
          [required]="true"
          [error]="cityError()"
          formControlName="city"
        />

        <mee-input
          [label]="'GST Number'"
          [hint]="'You can add this later'"
          [error]="gstError()"
          formControlName="gstNumber"
        />

        <mee-button
          class="block"
          [label]="'Save & Continue'"
          [loading]="loading()"
          [disabled]="form.invalid || loading()"
          [fullWidth]="true"
          [variant]="'primary'"
          [testId]="'onboarding-submit'"
          (clicked)="onSubmit()"
        />

      </form>

      <!-- Skip footer -->
      <p class="skip-text">
        <a
          class="skip-link"
          (click)="skipSetup()"
          role="button"
          tabindex="0"
          (keydown.enter)="skipSetup()"
        >I'll set this up later →</a>
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

  skipSetup(): void {
    void this.router.navigate(['/dashboard']);
  }
}

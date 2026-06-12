import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';
import { AuthLayoutComponent, MeeAlertBannerComponent, MeeOfflineBannerComponent } from '@mesell/composites';
import {
  MeeButtonComponent,
  MeeInputComponent,
  MeeStepsComponent,
} from '@mesell/ui-kit';
import type { MeeStep } from '@mesell/ui-kit';
import { NetworkService } from '@mesell/core';
import { SellerProfileService, ProfileValidationError } from './services/seller-profile.service';

/** Validator for 6-digit Indian PIN code (backend pattern ^\d{6}$). */
function pincodeValidator(control: { value: string | null | undefined }): { pincodeInvalid: true } | null {
  const value = control.value ?? '';
  if (!value) return null; // optional field — empty is allowed
  return /^\d{6}$/.test(value) ? null : { pincodeInvalid: true };
}

@Component({
  selector: 'mee-onboarding',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [SellerProfileService],
  imports: [
    ReactiveFormsModule,
    AuthLayoutComponent,
    MeeStepsComponent,
    MeeInputComponent,
    MeeButtonComponent,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
  ],
  template: `
    <mee-offline-banner />
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
          Legal Metrology details for Meesho compliance
        </p>
      </div>

      <!-- Error banner -->
      @if (errorMessage()) {
        <mee-alert-banner
          variant="error"
          [message]="errorMessage()!"
        />
      }

      <form [formGroup]="form" (ngSubmit)="onSubmit()" novalidate class="flex flex-col gap-4">

        <!-- Manufacturer section -->
        <p class="text-sm font-semibold mt-2" style="color: var(--mee-color-on-surface);">
          Manufacturer Details
        </p>

        <mee-input
          [label]="'Manufacturer Name'"
          [required]="true"
          [error]="fieldError('manufacturer_name') || manufacturerNameError()"
          formControlName="manufacturer_name"
        />

        <mee-input
          [label]="'Manufacturer Address'"
          [required]="true"
          [error]="fieldError('manufacturer_address') || manufacturerAddressError()"
          formControlName="manufacturer_address"
        />

        <mee-input
          [label]="'Manufacturer Pincode'"
          [required]="true"
          [error]="fieldError('manufacturer_pincode') || manufacturerPincodeError()"
          formControlName="manufacturer_pincode"
        />

        <!-- Packer section -->
        <p class="text-sm font-semibold mt-2" style="color: var(--mee-color-on-surface);">
          Packer Details
        </p>

        <mee-input
          [label]="'Packer Name'"
          [required]="true"
          [error]="fieldError('packer_name') || packerNameError()"
          formControlName="packer_name"
        />

        <mee-input
          [label]="'Packer Address'"
          [required]="true"
          [error]="fieldError('packer_address') || packerAddressError()"
          formControlName="packer_address"
        />

        <mee-input
          [label]="'Packer Pincode'"
          [required]="true"
          [error]="fieldError('packer_pincode') || packerPincodeError()"
          formControlName="packer_pincode"
        />

        <!-- Country of Origin -->
        <mee-input
          [label]="'Country of Origin'"
          [required]="true"
          [error]="fieldError('country_of_origin') || countryError()"
          formControlName="country_of_origin"
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
        You can update this later from your profile.
      </p>
    </mee-auth-layout>
  `,
})
export class OnboardingComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly profileService = inject(SellerProfileService);
  protected readonly network = inject(NetworkService);

  readonly steps: MeeStep[] = [
    { label: 'Account' },
    { label: 'Business' },
    { label: 'Done' },
  ];

  readonly loading = signal<boolean>(false);
  readonly submitted = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);
  /** Per-field errors from 422 validation_message_id / errors[]. */
  readonly fieldErrors = signal<Record<string, string>>({});

  readonly form = this.fb.group({
    manufacturer_name:    ['', [Validators.required, Validators.maxLength(200)]],
    manufacturer_address: ['', [Validators.required, Validators.maxLength(500)]],
    manufacturer_pincode: ['', [Validators.required, pincodeValidator]],
    packer_name:          ['', [Validators.required, Validators.maxLength(200)]],
    packer_address:       ['', [Validators.required, Validators.maxLength(500)]],
    packer_pincode:       ['', [Validators.required, pincodeValidator]],
    country_of_origin:    ['India', [Validators.required, Validators.maxLength(100)]],
  });

  // ── Computed field-level errors (form validators) ──────────────────────────

  readonly manufacturerNameError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('manufacturer_name');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['required']) return 'Manufacturer name is required.';
    if (ctrl.errors['maxlength']) return 'Too long (max 200 characters).';
    return undefined;
  });

  readonly manufacturerAddressError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('manufacturer_address');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['required']) return 'Manufacturer address is required.';
    if (ctrl.errors['maxlength']) return 'Too long (max 500 characters).';
    return undefined;
  });

  readonly manufacturerPincodeError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('manufacturer_pincode');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['required']) return 'Manufacturer pincode is required.';
    if (ctrl.errors['pincodeInvalid']) return 'Enter a valid 6-digit pincode.';
    return undefined;
  });

  readonly packerNameError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('packer_name');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['required']) return 'Packer name is required.';
    if (ctrl.errors['maxlength']) return 'Too long (max 200 characters).';
    return undefined;
  });

  readonly packerAddressError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('packer_address');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['required']) return 'Packer address is required.';
    if (ctrl.errors['maxlength']) return 'Too long (max 500 characters).';
    return undefined;
  });

  readonly packerPincodeError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('packer_pincode');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['required']) return 'Packer pincode is required.';
    if (ctrl.errors['pincodeInvalid']) return 'Enter a valid 6-digit pincode.';
    return undefined;
  });

  readonly countryError = computed<string | undefined>(() => {
    if (!this.submitted()) return undefined;
    const ctrl = this.form.get('country_of_origin');
    if (!ctrl?.errors) return undefined;
    if (ctrl.errors['required']) return 'Country of origin is required.';
    return undefined;
  });

  ngOnInit(): void {
    // country_of_origin defaults to 'India' via the form initialiser above.
    // Optionally load existing partial profile so a returning user sees pre-filled values.
    this.profileService.getProfile().subscribe({
      next: (profile) => {
        this.form.patchValue({
          manufacturer_name:    profile.manufacturer_name ?? '',
          manufacturer_address: profile.manufacturer_address ?? '',
          manufacturer_pincode: profile.manufacturer_pincode ?? '',
          packer_name:          profile.packer_name ?? '',
          packer_address:       profile.packer_address ?? '',
          packer_pincode:       profile.packer_pincode ?? '',
          country_of_origin:    profile.country_of_origin || 'India',
        });
      },
      error: () => {
        // Non-critical — form still renders with defaults; getProfile catchError handles the banner
      },
    });
  }

  /** Return a per-field 422 error string if the backend returned one. */
  fieldError(field: string): string | undefined {
    return this.fieldErrors()[field] ?? undefined;
  }

  onSubmit(): void {
    this.submitted.set(true);
    if (this.form.invalid || this.loading()) return;

    this.loading.set(true);
    this.errorMessage.set(null);
    this.fieldErrors.set({});

    const val = this.form.value;
    this.profileService.patchProfile({
      manufacturer_name:    val.manufacturer_name    || null,
      manufacturer_address: val.manufacturer_address || null,
      manufacturer_pincode: val.manufacturer_pincode || null,
      packer_name:          val.packer_name          || null,
      packer_address:       val.packer_address       || null,
      packer_pincode:       val.packer_pincode       || null,
      country_of_origin:    val.country_of_origin    || 'India',
    }).subscribe({
      next: () => {
        this.loading.set(false);
        void this.router.navigate(['/dashboard']);
      },
      error: (err: unknown) => {
        this.loading.set(false);
        if (err instanceof ProfileValidationError) {
          // Map 422 envelope to per-field errors + banner.
          // Backend errors[] shape: { field: string, constraint: string, msg: string }
          const errors: Record<string, string> = {};
          const rawErrors = (err.envelope.errors ?? []) as Array<{ field?: string; msg?: string }>;
          for (const fe of rawErrors) {
            if (fe.field) {
              errors[fe.field] = fe.msg ?? err.envelope.validation_message_id ?? 'Invalid value.';
            }
          }
          this.fieldErrors.set(errors);
          this.errorMessage.set(
            err.envelope.validation_message_id ??
            'Please correct the highlighted fields and try again.',
          );
        } else {
          this.errorMessage.set('Something went wrong. Please try again.');
        }
      },
    });
  }
}

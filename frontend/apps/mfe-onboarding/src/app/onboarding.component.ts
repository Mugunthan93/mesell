import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
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
import { AuthService } from '@mesell/core';
import {
  AuthLayoutComponent,
  MeeAlertBannerComponent,
  MeeOfflineBannerComponent,
  EmptyStateComponent,
} from '@mesell/composites';
import {
  MeeButtonComponent,
  MeeInputComponent,
  MeeSkeletonComponent,
  MeeStepsComponent,
} from '@mesell/ui-kit';
import type { MeeStep } from '@mesell/ui-kit';
import { SellerProfileService, ProfileValidationError, ProfileNetworkError } from './services/seller-profile.service';
import type { PatchProfileRequest, SellerProfile } from './seller-profile.model';
import type { ApiErrorEnvelope } from '@mesell/core';

/**
 * Optional pincode validator.
 * Empty → valid; non-empty must match ^\d{6}$ else error key `pincodeInvalid`.
 */
export function pincodeValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = (control.value as string | null | undefined) ?? '';
    if (!value.trim()) return null;
    return /^\d{6}$/.test(value) ? null : { pincodeInvalid: true };
  };
}

@Component({
  selector: 'mee-onboarding',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [SellerProfileService],
  imports: [
    ReactiveFormsModule,
    AuthLayoutComponent,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
    EmptyStateComponent,
    MeeStepsComponent,
    MeeInputComponent,
    MeeButtonComponent,
    MeeSkeletonComponent,
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

      @if (profileLoading()) {
        <mee-skeleton variant="text" [lines]="5" />
      } @else {
        @if (errorMessage()) {
          <mee-alert-banner variant="error" [message]="errorMessage()!" />
        }

        <form [formGroup]="form" (ngSubmit)="onSubmit()" novalidate class="form-fields" data-testid="onboarding-wizard">

          <mee-input
            [label]="'Manufacturer Name'"
            [required]="true"
            formControlName="manufacturer_name"
            [testId]="'onboarding-manufacturer-name'"
          />

          <mee-input
            [label]="'Manufacturer Address'"
            [required]="true"
            formControlName="manufacturer_address"
            [testId]="'onboarding-manufacturer-address'"
          />

          <mee-input
            [label]="'Manufacturer Pincode'"
            [required]="true"
            [hint]="'6-digit PIN code'"
            formControlName="manufacturer_pincode"
            [testId]="'onboarding-manufacturer-pincode'"
            [error]="(form.controls.manufacturer_pincode.touched || submitted()) && form.controls.manufacturer_pincode.hasError('required') ? 'Manufacturer pincode is required.' : (form.controls.manufacturer_pincode.touched && form.controls.manufacturer_pincode.hasError('pincodeInvalid') ? 'Enter a valid 6-digit pincode.' : undefined)"
          />

          <mee-input
            [label]="'Packer Name'"
            [required]="true"
            formControlName="packer_name"
            [testId]="'onboarding-packer-name'"
          />

          <mee-input
            [label]="'Packer Address'"
            [required]="true"
            formControlName="packer_address"
            [testId]="'onboarding-packer-address'"
          />

          <mee-input
            [label]="'Packer Pincode'"
            [required]="true"
            [hint]="'6-digit PIN code'"
            formControlName="packer_pincode"
            [testId]="'onboarding-packer-pincode'"
            [error]="(form.controls.packer_pincode.touched || submitted()) && form.controls.packer_pincode.hasError('required') ? 'Packer pincode is required.' : (form.controls.packer_pincode.touched && form.controls.packer_pincode.hasError('pincodeInvalid') ? 'Enter a valid 6-digit pincode.' : undefined)"
          />

          <mee-input
            [label]="'Country of Origin'"
            [required]="true"
            formControlName="country_of_origin"
            [testId]="'onboarding-country-of-origin'"
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
      }

      <!-- Skip footer -->
      <p class="skip-text">
        <a
          class="skip-link"
          data-testid="onboarding-skip"
          (click)="skipSetup()"
          role="button"
          tabindex="0"
          (keydown.enter)="skipSetup()"
        >I'll set this up later →</a>
      </p>
    </mee-auth-layout>
  `,
})
export class OnboardingComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);
  private readonly sellerProfile = inject(SellerProfileService);

  readonly steps: MeeStep[] = [
    { label: 'Account' },
    { label: 'Business' },
    { label: 'Done' },
  ];

  readonly loading = signal<boolean>(false);
  readonly submitted = signal<boolean>(false);
  readonly profileLoading = signal<boolean>(true);

  private readonly _errorMessage = signal<string | null>(null);
  readonly errorMessage = computed<string | null>(() => this._errorMessage());

  private readonly _fieldErrors = signal<Record<string, string>>({});

  readonly form = this.fb.group({
    manufacturer_name:    ['', [Validators.required, Validators.maxLength(140)]],
    manufacturer_address: ['', [Validators.required, Validators.maxLength(280)]],
    manufacturer_pincode: ['', [Validators.required, pincodeValidator()]],
    packer_name:          ['', [Validators.required, Validators.maxLength(140)]],
    packer_address:       ['', [Validators.required, Validators.maxLength(280)]],
    packer_pincode:       ['', [Validators.required, pincodeValidator()]],
    country_of_origin:    ['India', [Validators.required]],
  });

  ngOnInit(): void {
    this.sellerProfile.getProfile().subscribe({
      next: (profile: SellerProfile) => {
        this.form.patchValue({
          manufacturer_name:    profile.manufacturer_name    ?? '',
          manufacturer_address: profile.manufacturer_address ?? '',
          manufacturer_pincode: profile.manufacturer_pincode ?? '',
          packer_name:          profile.packer_name          ?? '',
          packer_address:       profile.packer_address       ?? '',
          packer_pincode:       profile.packer_pincode       ?? '',
          country_of_origin:    profile.country_of_origin    ?? 'India',
        });
        this.profileLoading.set(false);
      },
      error: () => {
        this.profileLoading.set(false);
      },
    });
  }

  onSubmit(): void {
    this.submitted.set(true);
    if (this.form.invalid || this.loading()) return;

    this.loading.set(true);
    this._errorMessage.set(null);
    this._fieldErrors.set({});

    const raw = this.form.value;
    const payload: PatchProfileRequest = {
      manufacturer_name:    raw.manufacturer_name    ?? null,
      manufacturer_address: raw.manufacturer_address ?? null,
      manufacturer_pincode: raw.manufacturer_pincode?.trim() || null,
      packer_name:          raw.packer_name          ?? null,
      packer_address:       raw.packer_address       ?? null,
      packer_pincode:       raw.packer_pincode?.trim() || null,
      country_of_origin:    raw.country_of_origin    ?? null,
    };

    this.sellerProfile.patchProfile(payload).subscribe({
      next: () => {
        this.auth.refreshUser().subscribe({
          complete: () => {
            this.loading.set(false);
            void this.router.navigate(['/dashboard']);
          },
        });
      },
      error: (err: unknown) => {
        this.loading.set(false);
        if (err instanceof ProfileValidationError) {
          this._mapValidationError(err.envelope);
        } else if (err instanceof ProfileNetworkError) {
          this._errorMessage.set(err.message);
        } else {
          this._errorMessage.set('A network error occurred. Please try again.');
        }
      },
    });
  }

  /**
   * Returns the per-field error message for the given control name.
   * Gate 7 asserts: `fieldError('manufacturer_pincode') === 'Enter a valid 6-digit pincode.'`
   */
  fieldError(controlName: string): string | null {
    return this._fieldErrors()[controlName] ?? null;
  }

  skipSetup(): void {
    void this.router.navigate(['/dashboard']);
  }

  private _mapValidationError(envelope: Partial<ApiErrorEnvelope>): void {
    const errors = (envelope.errors ?? []) as Array<{
      field?: string;
      constraint?: string;
      msg?: string;
    }>;
    const mapped: Record<string, string> = {};
    for (const e of errors) {
      if (e.field) {
        mapped[e.field] = e.msg ?? 'Invalid value.';
      }
    }
    this._fieldErrors.set(mapped);
    this._errorMessage.set(
      envelope.detail ?? 'Validation failed — check the highlighted fields.',
    );
  }
}

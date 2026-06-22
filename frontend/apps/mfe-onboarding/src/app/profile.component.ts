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
import {
  MeeAlertBannerComponent,
  MeeOfflineBannerComponent,
  EmptyStateComponent,
} from '@mesell/composites';
import {
  MeeCardComponent,
  MeeBadgeComponent,
  MeeInputComponent,
  MeeButtonComponent,
  MeeIconComponent,
  MeeSkeletonComponent,
} from '@mesell/ui-kit';
import type { MeeBadgeSeverity } from '@mesell/ui-kit';
import { AuthService } from '@mesell/core';
import type { ApiErrorEnvelope } from '@mesell/core';
import {
  SellerProfileService,
  ProfileValidationError,
  ProfileNetworkError,
} from './services/seller-profile.service';
import type { PatchProfileRequest, SellerProfile } from './seller-profile.model';

/**
 * Optional pincode validator — mirrors onboarding.component.ts pincodeValidator().
 * Empty string → valid; non-empty must match ^\d{6}$ else error key `pincodeInvalid`.
 */
function pincodeValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = (control.value as string | null | undefined) ?? '';
    if (!value.trim()) return null;
    return /^\d{6}$/.test(value) ? null : { pincodeInvalid: true };
  };
}

@Component({
  selector: 'app-profile',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [SellerProfileService],
  imports: [
    ReactiveFormsModule,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
    EmptyStateComponent,
    MeeCardComponent,
    MeeBadgeComponent,
    MeeInputComponent,
    MeeButtonComponent,
    MeeIconComponent,
    MeeSkeletonComponent,
  ],
  styles: [`
    :host {
      display: block;
      padding: var(--mee-space-4);
      padding-bottom: calc(var(--mee-space-8) + env(safe-area-inset-bottom, 0px));
    }

    .profile-header {
      padding: var(--mee-space-2) 0 var(--mee-space-5);
    }

    .profile-title {
      font-size: 24px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0 0 var(--mee-space-1);
    }

    .profile-subtitle {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }

    .profile-content {
      max-width: 560px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-6);
    }

    .identity-card-body {
      display: flex;
      align-items: center;
      gap: var(--mee-space-4);
      padding: var(--mee-space-2) 0;
    }

    .avatar-circle {
      width: 48px;
      height: 48px;
      border-radius: var(--mee-radius-full);
      background: var(--mee-color-primary-light);
      color: var(--mee-color-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      font-weight: 700;
      flex-shrink: 0;
      user-select: none;
    }

    .identity-info {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-1);
      min-width: 0;
    }

    .identity-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .identity-phone-row {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
      flex-wrap: wrap;
    }

    .identity-phone {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
    }

    .edit-form-row {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
    }

    .form-section-label {
      font-size: 13px;
      font-weight: 600;
      color: var(--mee-color-on-surface-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin: 0 0 var(--mee-space-2);
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
    }

    .plan-card-body {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-3);
    }

    .plan-label {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin: 0;
    }

    .plan-name {
      font-size: 20px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0;
    }

    .plan-features {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
    }

    .plan-feature-item {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
      font-size: 14px;
      color: var(--mee-color-on-surface);
    }

    .plan-feature-item i {
      color: var(--mee-color-success);
      font-size: 14px;
    }

    .plan-manage-link {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      text-align: right;
      font-size: 14px;
      color: var(--mee-color-primary);
      font-weight: 500;
      text-decoration: none;
      cursor: pointer;
      transition: opacity var(--mee-transition-fast);
      min-height: 44px;
    }

    .plan-manage-link:hover {
      opacity: 0.8;
    }

    .logout-btn {
      width: 100%;
      min-height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--mee-space-2);
      background: transparent;
      border: 1.5px solid var(--mee-color-error);
      border-radius: var(--mee-radius-md);
      color: var(--mee-color-error);
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      transition: background var(--mee-transition-fast), color var(--mee-transition-fast);
      padding: var(--mee-space-3) var(--mee-space-4);
    }

    .logout-btn:hover {
      background: rgba(220, 38, 38, 0.06);
    }
  `],
  template: `
    <!-- Page heading -->
    <div class="profile-header">
      <h1 class="profile-title">Profile</h1>
      <p class="profile-subtitle">Manage your account</p>
    </div>

    <!-- Centered content column -->
    <div class="profile-content">

      <!-- Section 1: Identity card (read-only — sourced from AuthService) -->
      <mee-card>
        <div class="identity-card-body">
          <!-- Avatar initial circle -->
          <div class="avatar-circle" aria-hidden="true">
            {{ avatarInitial() }}
          </div>

          <!-- Name + phone row -->
          <div class="identity-info">
            <span class="identity-name">
              {{ auth.currentUser()?.name || 'Seller' }}
            </span>
            <div class="identity-phone-row">
              <span class="identity-phone">
                {{ formattedPhone() }}
              </span>
              <mee-badge
                [value]="planLabel()"
                [severity]="planSeverity()"
              />
            </div>
          </div>
        </div>
      </mee-card>

      <!-- Section 2: Legal-Metrology edit form -->
      <form [formGroup]="form" (ngSubmit)="onSubmit()" novalidate class="edit-form-row">

        <!-- Global error banner (network or generic 422) -->
        @if (errorMessage()) {
          <mee-alert-banner variant="error" [message]="errorMessage()!" />
        }

        <!-- Manufacturer fields -->
        <p class="form-section-label">Manufacturer</p>

        <mee-input
          label="Manufacturer name"
          placeholder="e.g. Acme Textiles Pvt. Ltd."
          formControlName="manufacturer_name"
          [error]="fieldError('manufacturer_name') || undefined"
        />

        <mee-input
          label="Manufacturer address"
          placeholder="Street, city, state"
          formControlName="manufacturer_address"
          [error]="fieldError('manufacturer_address') || undefined"
        />

        <mee-input
          label="Manufacturer PIN code"
          placeholder="6-digit PIN"
          [required]="true"
          formControlName="manufacturer_pincode"
          [error]="fieldError('manufacturer_pincode') || (form.controls.manufacturer_pincode.touched && form.controls.manufacturer_pincode.hasError('required') ? 'Manufacturer pincode is required.' : (form.controls.manufacturer_pincode.touched && form.controls.manufacturer_pincode.hasError('pincodeInvalid') ? 'Enter a valid 6-digit pincode.' : undefined))"
        />

        <!-- Packer fields -->
        <p class="form-section-label">Packer</p>

        <mee-input
          label="Packer name"
          placeholder="e.g. Acme Packaging Ltd."
          formControlName="packer_name"
          [error]="fieldError('packer_name') || undefined"
        />

        <mee-input
          label="Packer address"
          placeholder="Street, city, state"
          formControlName="packer_address"
          [error]="fieldError('packer_address') || undefined"
        />

        <mee-input
          label="Packer PIN code"
          placeholder="6-digit PIN"
          [required]="true"
          formControlName="packer_pincode"
          [error]="fieldError('packer_pincode') || (form.controls.packer_pincode.touched && form.controls.packer_pincode.hasError('required') ? 'Packer pincode is required.' : (form.controls.packer_pincode.touched && form.controls.packer_pincode.hasError('pincodeInvalid') ? 'Enter a valid 6-digit pincode.' : undefined))"
        />

        <!-- Country of origin -->
        <mee-input
          label="Country of origin"
          placeholder="e.g. India"
          formControlName="country_of_origin"
          [error]="fieldError('country_of_origin') || undefined"
        />

        <!-- Phone read-only — displayed via placeholder; no CVA binding needed -->
        <mee-input
          label="Phone"
          [disabled]="true"
          [placeholder]="displayPhone()"
        />

        <!-- Save button — right-aligned, not full-width -->
        <div class="form-actions">
          <mee-button
            [label]="saved() ? 'Saved!' : 'Save changes'"
            variant="secondary"
            [loading]="saving()"
            [disabled]="form.invalid || saving()"
            [fullWidth]="false"
            (clicked)="onSubmit()"
          />
        </div>
      </form>

      <!-- Section 3: Plan card -->
      <mee-card>
        <div class="plan-card-body">
          <p class="plan-label">Current plan</p>
          <p class="plan-name">{{ planLabel() }}</p>

          <ul class="plan-features" aria-label="Plan features">
            <li class="plan-feature-item">
              <mee-icon name="check" />
              50 products / month
            </li>
            <li class="plan-feature-item">
              <mee-icon name="check" />
              AI autofill
            </li>
            <li class="plan-feature-item">
              <mee-icon name="check" />
              XLSX export
            </li>
          </ul>

          <a class="plan-manage-link" role="button" tabindex="0">
            Manage subscription
          </a>
        </div>
      </mee-card>

      <!-- Section 4: Logout button -->
      <button
        type="button"
        class="logout-btn"
        (click)="onLogout()"
      >
        <mee-icon name="logout" />
        Log out
      </button>

    </div>
  `,
})
export class ProfileComponent implements OnInit {
  protected readonly auth            = inject(AuthService);
  private  readonly router           = inject(Router);
  private  readonly fb               = inject(FormBuilder);
  private  readonly sellerProfile    = inject(SellerProfileService);

  readonly form = this.fb.group({
    manufacturer_name:    [''],
    manufacturer_address: [''],
    manufacturer_pincode: ['', [Validators.required, pincodeValidator()]],
    packer_name:          [''],
    packer_address:       [''],
    packer_pincode:       ['', [Validators.required, pincodeValidator()]],
    country_of_origin:    ['India'],
  });

  // Local reactive state
  readonly saving       = signal(false);
  readonly saved        = signal(false);
  readonly errorMessage = signal<string | null>(null);

  private readonly _fieldErrors = signal<Record<string, string>>({});

  // Derived display values — VERBATIM from the original (identity card, not editable)
  readonly displayPhone = computed<string>(() => {
    const p = this.auth.currentUser()?.phone ?? '';
    return p.startsWith('+91') ? p.slice(3) : p;
  });

  readonly formattedPhone = computed<string>(() => {
    const digits = this.displayPhone();
    if (digits.length === 10) {
      return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
    }
    return digits ? `+91 ${digits}` : '';
  });

  readonly planSeverity = computed<MeeBadgeSeverity>(() => 'neutral');

  readonly planLabel = computed<string>(() => 'Free plan');

  readonly avatarInitial = computed<string>(() => {
    const name = this.auth.currentUser()?.name ?? '';
    return name.charAt(0).toUpperCase() || 'S';
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
      },
      // Service maps 404 → FRESH_SELLER_PROFILE (no error banner needed for 404)
    });
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving()) return;

    this.form.markAllAsTouched();
    if (this.form.invalid) return;

    this.saving.set(true);
    this.errorMessage.set(null);

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
        this.saving.set(false);
        this.saved.set(true);
        // The ONLY remaining setTimeout — resets the "Saved!" label after 3s
        setTimeout(() => {
          if (this.saved()) this.saved.set(false);
        }, 3000);
      },
      error: (err: unknown) => {
        this.saving.set(false);
        // Do NOT clear the form — keep field values so the seller can correct them
        if (err instanceof ProfileValidationError) {
          this._mapValidationError(err.envelope);
        } else if (err instanceof ProfileNetworkError) {
          this.errorMessage.set(err.message);
        } else {
          this.errorMessage.set('A network error occurred. Please try again.');
        }
      },
    });
    // NOTE: No AuthService.refreshUser() call — editing optional Legal-Metrology fields
    // cannot regress onboarding_complete for an already-onboarded seller, and adding
    // a /auth/me GET would break spec httpMock.verify(). Contrast: onboarding.component.ts
    // DOES call refreshUser() because first-run flips the onboarding_complete flag.
    // No nav-visible flag concern detected for this PATCH endpoint.
  }

  /**
   * Returns the per-field validation error message for the given form control name.
   * Populated by _mapValidationError() on 422 responses from patchProfile().
   */
  fieldError(controlName: string): string | null {
    return this._fieldErrors()[controlName] ?? null;
  }

  onLogout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
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
    this.errorMessage.set(
      envelope.detail ?? 'Validation failed — check the highlighted fields.',
    );
  }
}

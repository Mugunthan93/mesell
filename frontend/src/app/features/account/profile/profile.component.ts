// features/account/profile/profile.component.ts
// Page component for /profile — edit existing seller profile.
// Loads existing values via GET /api/v1/seller-profile, pre-fills the form,
// and saves via PATCH /api/v1/seller-profile on submit → navigates to /dashboard.
//
// ComplianceStepComponent is stubbed out in this dispatch.
// TODO(profile-session dispatch-2): replace compliance-step-stub div with
//   <mee-compliance-step [mode]="'edit'" [profile]="profile()" (saved)="onComplianceSaved($event)">
//   </mee-compliance-step>
//   after @shared/components/compliance-step is available (onboarding session hand-off).

import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslocoPipe } from '@jsverse/transloco';
import { catchError, EMPTY } from 'rxjs';

import { ProfileApiService, SellerProfileCorrect } from './profile-api.service';
import { ErrorService } from '@core/services/error.service';

/** Validates that a pincode is exactly 6 digits when a value is present. */
function optionalPincodeValidator(control: AbstractControl): ValidationErrors | null {
  const value = control.value as string | null | undefined;
  if (!value || value.trim() === '') return null;
  return /^\d{6}$/.test(value) ? null : { pattern: true };
}

@Component({
  selector: 'mee-profile-edit',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslocoPipe,
  ],
  template: `
    <div class="mee-profile-edit max-w-2xl mx-auto p-4">
      @if (loading()) {
        <mat-spinner diameter="32" aria-label="Loading profile…"></mat-spinner>
      } @else {
        <h1 class="text-xl font-semibold mb-6">{{ 'profile.title' | transloco }}</h1>
        <form [formGroup]="form" (ngSubmit)="onSave()">

          <!-- Manufacturer fields -->
          <mat-form-field class="w-full mb-4">
            <mat-label>{{ 'profile.manufacturer_name' | transloco }}</mat-label>
            <input
              matInput
              formControlName="manufacturer_name"
              autocomplete="organization"
              style="min-height:44px"
            />
            @if (form.get('manufacturer_name')?.hasError('required') && form.get('manufacturer_name')?.touched) {
              <mat-error>{{ 'validation.required' | transloco }}</mat-error>
            }
          </mat-form-field>

          <mat-form-field class="w-full mb-4">
            <mat-label>{{ 'profile.manufacturer_address' | transloco }}</mat-label>
            <textarea
              matInput
              formControlName="manufacturer_address"
              rows="2"
              style="min-height:44px"
            ></textarea>
            @if (form.get('manufacturer_address')?.hasError('required') && form.get('manufacturer_address')?.touched) {
              <mat-error>{{ 'validation.required' | transloco }}</mat-error>
            }
          </mat-form-field>

          <mat-form-field class="w-full mb-4">
            <mat-label>{{ 'profile.manufacturer_pincode' | transloco }}</mat-label>
            <input
              matInput
              formControlName="manufacturer_pincode"
              inputmode="numeric"
              maxlength="6"
              style="min-height:44px"
            />
            @if (form.get('manufacturer_pincode')?.hasError('required') && form.get('manufacturer_pincode')?.touched) {
              <mat-error>{{ 'validation.required' | transloco }}</mat-error>
            }
            @if (form.get('manufacturer_pincode')?.hasError('pattern') && form.get('manufacturer_pincode')?.touched) {
              <mat-error>{{ 'validation.pincode' | transloco }}</mat-error>
            }
          </mat-form-field>

          <!-- Packer fields -->
          <mat-form-field class="w-full mb-4">
            <mat-label>{{ 'profile.packer_name' | transloco }}</mat-label>
            <input
              matInput
              formControlName="packer_name"
              style="min-height:44px"
            />
            @if (form.get('packer_name')?.hasError('required') && form.get('packer_name')?.touched) {
              <mat-error>{{ 'validation.required' | transloco }}</mat-error>
            }
          </mat-form-field>

          <mat-form-field class="w-full mb-4">
            <mat-label>{{ 'profile.packer_address' | transloco }}</mat-label>
            <textarea
              matInput
              formControlName="packer_address"
              rows="2"
              style="min-height:44px"
            ></textarea>
            @if (form.get('packer_address')?.hasError('required') && form.get('packer_address')?.touched) {
              <mat-error>{{ 'validation.required' | transloco }}</mat-error>
            }
          </mat-form-field>

          <mat-form-field class="w-full mb-4">
            <mat-label>{{ 'profile.packer_pincode' | transloco }}</mat-label>
            <input
              matInput
              formControlName="packer_pincode"
              inputmode="numeric"
              maxlength="6"
              style="min-height:44px"
            />
            @if (form.get('packer_pincode')?.hasError('required') && form.get('packer_pincode')?.touched) {
              <mat-error>{{ 'validation.required' | transloco }}</mat-error>
            }
            @if (form.get('packer_pincode')?.hasError('pattern') && form.get('packer_pincode')?.touched) {
              <mat-error>{{ 'validation.pincode' | transloco }}</mat-error>
            }
          </mat-form-field>

          <!-- Importer fields (optional) -->
          <mat-form-field class="w-full mb-4">
            <mat-label>{{ 'profile.importer_name' | transloco }}</mat-label>
            <input
              matInput
              formControlName="importer_name"
              style="min-height:44px"
            />
          </mat-form-field>

          <mat-form-field class="w-full mb-4">
            <mat-label>{{ 'profile.importer_address' | transloco }}</mat-label>
            <textarea
              matInput
              formControlName="importer_address"
              rows="2"
              style="min-height:44px"
            ></textarea>
          </mat-form-field>

          <mat-form-field class="w-full mb-4">
            <mat-label>{{ 'profile.importer_pincode' | transloco }}</mat-label>
            <input
              matInput
              formControlName="importer_pincode"
              inputmode="numeric"
              maxlength="6"
              style="min-height:44px"
            />
            @if (form.get('importer_pincode')?.hasError('pattern') && form.get('importer_pincode')?.touched) {
              <mat-error>{{ 'validation.pincode' | transloco }}</mat-error>
            }
          </mat-form-field>

          <!-- Country of origin -->
          <mat-form-field class="w-full mb-6">
            <mat-label>{{ 'profile.country_of_origin' | transloco }}</mat-label>
            <input
              matInput
              formControlName="country_of_origin"
              style="min-height:44px"
            />
            @if (form.get('country_of_origin')?.hasError('required') && form.get('country_of_origin')?.touched) {
              <mat-error>{{ 'validation.required' | transloco }}</mat-error>
            }
          </mat-form-field>

          <!-- ComplianceStepComponent placeholder — replace with real component when available -->
          <!-- TODO(profile-session dispatch-2): replace stub with
               <mee-compliance-step [mode]="'edit'" [profile]="profile()" (saved)="onComplianceSaved($event)">
               </mee-compliance-step>
               after @shared/components/compliance-step is available (onboarding session hand-off) -->
          <div
            class="compliance-step-stub p-4 border border-dashed rounded text-sm text-gray-400 mb-6"
            role="region"
            aria-label="Super-category compliance (pending)"
          >
            Super-category &amp; compliance fields — available after ComplianceStepComponent hand-off from onboarding session.
          </div>

          <div class="flex gap-3 mt-6">
            <button
              mat-raised-button
              color="primary"
              type="submit"
              [disabled]="saving() || form.invalid"
            >
              @if (saving()) {
                <mat-spinner diameter="18" class="inline"></mat-spinner>
              }
              {{ 'profile.save' | transloco }}
            </button>
            <button mat-button type="button" routerLink="/dashboard">
              {{ 'profile.cancel' | transloco }}
            </button>
          </div>

        </form>
      }
    </div>
  `,
})
export class ProfileEditComponent implements OnInit {
  private readonly profileApi = inject(ProfileApiService);
  private readonly router = inject(Router);
  private readonly errorService = inject(ErrorService);
  private readonly fb = inject(FormBuilder);

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly profile = signal<SellerProfileCorrect | null>(null);

  readonly form = this.fb.group({
    manufacturer_name:    ['', [Validators.required]],
    manufacturer_address: ['', [Validators.required]],
    manufacturer_pincode: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
    packer_name:          ['', [Validators.required]],
    packer_address:       ['', [Validators.required]],
    packer_pincode:       ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
    importer_name:        [null as string | null, []],
    importer_address:     [null as string | null, []],
    importer_pincode:     [null as string | null, [optionalPincodeValidator]],
    country_of_origin:    ['India', [Validators.required]],
  });

  ngOnInit(): void {
    this.profileApi.getProfile().pipe(
      catchError((err: unknown) => {
        // 404 = first-time seller with no profile yet — show empty form.
        // The PATCH endpoint acts as an upsert on the backend.
        const status = (err as { status?: number })?.status;
        if (status === 404) {
          this.loading.set(false);
          return EMPTY;
        }
        // All other errors surface via snackbar
        this.errorService.showError(
          err instanceof Error ? err : new Error('Failed to load profile'),
        );
        this.loading.set(false);
        return EMPTY;
      }),
    ).subscribe(data => {
      this.profile.set(data);
      this.form.patchValue({
        manufacturer_name:    data.manufacturer_name ?? '',
        manufacturer_address: data.manufacturer_address ?? '',
        manufacturer_pincode: data.manufacturer_pincode ?? '',
        packer_name:          data.packer_name ?? '',
        packer_address:       data.packer_address ?? '',
        packer_pincode:       data.packer_pincode ?? '',
        importer_name:        data.importer_name ?? null,
        importer_address:     data.importer_address ?? null,
        importer_pincode:     data.importer_pincode ?? null,
        country_of_origin:    data.country_of_origin,
      });
      this.loading.set(false);
    });
  }

  onSave(): void {
    if (this.form.invalid) return;
    this.saving.set(true);

    // Only send defined, non-null base-profile fields.
    // active_super_categories + compliance_extensions are handled by
    // ComplianceStepComponent in edit mode (stub — no-op in this dispatch).
    const raw = this.form.value;
    const patch = Object.fromEntries(
      Object.entries(raw).filter(([, v]) => v !== undefined),
    ) as Parameters<ProfileApiService['patchBaseProfile']>[0];

    this.profileApi.patchBaseProfile(patch).subscribe({
      next: () => {
        this.saving.set(false);
        void this.router.navigateByUrl('/dashboard');
      },
      error: (err: unknown) => {
        this.errorService.showError(
          err instanceof Error ? err : new Error('Failed to save profile'),
        );
        this.saving.set(false);
      },
    });
  }
}

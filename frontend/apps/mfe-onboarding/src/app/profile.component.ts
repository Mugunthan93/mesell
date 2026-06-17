import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
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
import {
  MeeCardComponent,
  MeeBadgeComponent,
  MeeInputComponent,
  MeeButtonComponent,
  MeeSkeletonComponent,
} from '@mesell/ui-kit';
import type { MeeBadgeSeverity } from '@mesell/ui-kit';
import { AuthService, NetworkService } from '@mesell/core';
import {
  MeeAlertBannerComponent,
  MeeOfflineBannerComponent,
  EmptyStateComponent,
} from '@mesell/composites';
import { SellerProfileService, ProfileValidationError } from './services/seller-profile.service';

/** Validator for 6-digit Indian PIN code (backend pattern ^\d{6}$). */
function pincodeValidator(control: { value: string | null | undefined }): { pincodeInvalid: true } | null {
  const value = control.value ?? '';
  if (!value) return null; // optional field — empty is allowed
  return /^\d{6}$/.test(value) ? null : { pincodeInvalid: true };
}

@Component({
  selector: 'app-profile',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [SellerProfileService],
  imports: [
    ReactiveFormsModule,
    MeeCardComponent,
    MeeBadgeComponent,
    MeeInputComponent,
    MeeButtonComponent,
    MeeSkeletonComponent,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
    EmptyStateComponent,
  ],
  template: `
    <!--
      Offline banner: sticky-top, z-50, so it floats above page content
      without layout shift (max-height:0 internally when online).
    -->
    <div class="mee-offline-wrapper">
      <mee-offline-banner />
    </div>

    <!-- Page heading -->
    <div class="p-4 pb-2 md:p-8 md:pb-4">
      <h1 class="text-2xl font-semibold" style="color: var(--mee-color-on-surface)">Profile</h1>
      <p class="text-sm mt-1" style="color: var(--mee-color-on-surface-muted)">Manage your account</p>
    </div>

    <!--
      Centered content column.
      max-w-[560px]: caps width on tablets/desktop.
      px-4: 16px side padding on all screens (enough room at 360px).
      space-y-6: 24px gap between content sections.
    -->
    <div class="w-full max-w-[560px] mx-auto px-4 pb-8 md:px-8 space-y-6">

      <!-- Identity card -->
      <mee-card>
        <div class="flex items-center gap-4 py-2">
          <!--
            Avatar circle — explicit 48x48 px (> 44px WCAG 2.5.8 min tap target).
            aria-hidden because it's decorative (name is spoken via adjacent span).
          -->
          <div
            class="flex-shrink-0 flex items-center justify-center rounded-full text-lg font-bold select-none"
            style="
              width: 48px;
              height: 48px;
              background: var(--mee-color-primary-light);
              color: var(--mee-color-primary);
            "
            aria-hidden="true"
          >
            {{ avatarInitial() }}
          </div>

          <!-- Name + phone row -->
          <div class="flex flex-col gap-1 min-w-0">
            <span class="text-base font-semibold truncate" style="color: var(--mee-color-on-surface)">
              {{ auth.currentUser()?.name || 'Seller' }}
            </span>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-sm" style="color: var(--mee-color-on-surface-muted)">
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

      <!--
        Loading state: skeleton placeholders replacing the raw animate-spin spinner
        (spec §3.4 item 1). aria-live="polite" announces loading to screen readers.
      -->
      @if (profileLoading()) {
        <div aria-live="polite" aria-label="Loading your profile" role="status" class="space-y-3">
          <mee-skeleton variant="text" [lines]="3" />
          <mee-skeleton variant="text" [lines]="3" />
        </div>
      } @else {

        <!-- Load error banner — focused programmatically for a11y -->
        @if (loadError()) {
          <div
            #errorBannerRef
            tabindex="-1"
            aria-live="assertive"
            style="outline: none;"
          >
            <mee-alert-banner
              variant="error"
              [message]="loadError()!"
            />
          </div>
        }

        <!-- First-time seller: empty-state prompt (all LM fields blank after load) -->
        @if (isFirstTimeSeller()) {
          <mee-empty-state
            icon="person_add"
            message="Complete your Legal Metrology details to start selling on Meesho."
            cta_label="Fill in details"
            (cta_click)="scrollToForm()"
          />
        }

        <!--
          Submit error + success banners — aria-live="assertive" so AT announces immediately.
          Wrapper is programmatically focused so keyboard users receive context.
        -->
        @if (errorMessage()) {
          <div
            #submitErrorRef
            tabindex="-1"
            aria-live="assertive"
            style="outline: none;"
          >
            <mee-alert-banner
              variant="error"
              [message]="errorMessage()!"
            />
          </div>
        }

        @if (saved()) {
          <div aria-live="polite">
            <mee-alert-banner
              variant="success"
              message="Profile saved successfully."
            />
          </div>
        }

        <!--
          Edit form.
          360px layout: flex-column gap --mee-space-3 (12px) so 7 fields stack without crowding.
          Section headings add --mee-space-2 (8px) top margin for visual grouping.
          All mee-input + mee-button components respect min-height 44px internally.
        -->
        <form
          [formGroup]="form"
          (ngSubmit)="onSubmit()"
          novalidate
          aria-label="Business profile form"
          #profileForm
        >
          <div class="flex flex-col" style="gap: var(--mee-space-3);">

            <!-- Section: Manufacturer Details -->
            <p
              class="text-sm font-semibold"
              id="section-manufacturer"
              style="color: var(--mee-color-on-surface); margin-top: var(--mee-space-2);"
            >
              Manufacturer Details
            </p>

            <mee-input
              [label]="'Manufacturer Name'"
              [error]="fieldError('manufacturer_name') || manufacturerNameError()"
              formControlName="manufacturer_name"
            />

            <mee-input
              [label]="'Manufacturer Address'"
              [error]="fieldError('manufacturer_address') || manufacturerAddressError()"
              formControlName="manufacturer_address"
            />

            <mee-input
              [label]="'Manufacturer Pincode'"
              inputmode="numeric"
              maxlength="6"
              [error]="fieldError('manufacturer_pincode') || manufacturerPincodeError()"
              formControlName="manufacturer_pincode"
            />

            <!-- Section: Packer Details -->
            <p
              class="text-sm font-semibold"
              id="section-packer"
              style="color: var(--mee-color-on-surface); margin-top: var(--mee-space-2);"
            >
              Packer Details
            </p>

            <mee-input
              [label]="'Packer Name'"
              [error]="fieldError('packer_name') || packerNameError()"
              formControlName="packer_name"
            />

            <mee-input
              [label]="'Packer Address'"
              [error]="fieldError('packer_address') || packerAddressError()"
              formControlName="packer_address"
            />

            <mee-input
              [label]="'Packer Pincode'"
              inputmode="numeric"
              maxlength="6"
              [error]="fieldError('packer_pincode') || packerPincodeError()"
              formControlName="packer_pincode"
            />

            <!-- Country of Origin -->
            <mee-input
              [label]="'Country of Origin'"
              [error]="fieldError('country_of_origin') || countryError()"
              formControlName="country_of_origin"
            />

            <!-- Phone read-only -->
            <mee-input
              [label]="'Phone'"
              [disabled]="true"
              [placeholder]="displayPhone()"
            />

            <!-- Save button — min 44px height guaranteed by mee-button variant="primary" -->
            <mee-button
              [label]="saved() ? 'Saved!' : 'Save changes'"
              variant="primary"
              [loading]="saving()"
              [disabled]="saving()"
              [fullWidth]="true"
              (clicked)="onSubmit()"
              style="margin-top: var(--mee-space-2);"
            />
          </div>
        </form>

        <!-- Divider -->
        <hr style="border-color: var(--mee-color-outline); margin-top: var(--mee-space-4);" />

        <!-- Log out — min 44px enforced by mee-button -->
        <mee-button
          label="Log out"
          variant="danger"
          [fullWidth]="true"
          (clicked)="onLogout()"
        />

      }
    </div>
  `,
  styles: [`
    :host { display: block; }

    /*
     * Offline banner wrapper: sticky to viewport top, z-index 50.
     * The banner itself has max-height:0 when online (no layout shift).
     * margin-bottom: 0 when hidden; the internal padding handles spacing when visible.
     */
    .mee-offline-wrapper {
      position: sticky;
      top: 0;
      z-index: 50;
    }

    /* Suppress visible focus ring on programmatic-focus wrappers (error banners). */
    [tabindex="-1"]:focus {
      outline: none;
    }
  `],
})
export class ProfileComponent implements OnInit, AfterViewInit {
  protected readonly auth    = inject(AuthService);
  private  readonly router   = inject(Router);
  private  readonly fb       = inject(FormBuilder);
  private  readonly profileService = inject(SellerProfileService);
  protected readonly network = inject(NetworkService);

  @ViewChild('errorBannerRef') errorBannerRef?: ElementRef<HTMLDivElement>;
  @ViewChild('submitErrorRef') submitErrorRef?: ElementRef<HTMLDivElement>;

  readonly form = this.fb.group({
    manufacturer_name:    ['', [Validators.maxLength(200)]],
    manufacturer_address: ['', [Validators.maxLength(500)]],
    manufacturer_pincode: ['', [pincodeValidator]],
    packer_name:          ['', [Validators.maxLength(200)]],
    packer_address:       ['', [Validators.maxLength(500)]],
    packer_pincode:       ['', [pincodeValidator]],
    country_of_origin:    ['India', [Validators.required, Validators.maxLength(100)]],
  });

  // Local reactive state
  readonly profileLoading      = signal(true);
  readonly saving              = signal(false);
  readonly saved               = signal(false);
  readonly loadError           = signal<string | null>(null);
  readonly errorMessage        = signal<string | null>(null);
  /** True when all LM base fields are blank after load — first-time seller UX. */
  readonly isFirstTimeSeller   = signal(false);
  /** Per-field 422 errors from the backend. */
  readonly fieldErrors         = signal<Record<string, string>>({});

  // ── Derived display values ─────────────────────────────────────────────────

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

  readonly planLabel = computed<string>(() => {
    const plan = this.auth.currentUser()?.plan;
    if (!plan) return 'Free plan';
    return `${plan.charAt(0).toUpperCase()}${plan.slice(1)} plan`;
  });

  readonly avatarInitial = computed<string>(() => {
    const name = this.auth.currentUser()?.name ?? '';
    return name.charAt(0).toUpperCase() || 'S';
  });

  // ── Computed field-level errors (form validators) ──────────────────────────

  readonly manufacturerNameError = computed<string | undefined>(() => {
    const ctrl = this.form.get('manufacturer_name');
    if (!ctrl || ctrl.valid || ctrl.pristine) return undefined;
    if (ctrl.errors?.['maxlength']) return 'Too long (max 200 characters).';
    return undefined;
  });

  readonly manufacturerAddressError = computed<string | undefined>(() => {
    const ctrl = this.form.get('manufacturer_address');
    if (!ctrl || ctrl.valid || ctrl.pristine) return undefined;
    if (ctrl.errors?.['maxlength']) return 'Too long (max 500 characters).';
    return undefined;
  });

  readonly manufacturerPincodeError = computed<string | undefined>(() => {
    const ctrl = this.form.get('manufacturer_pincode');
    if (!ctrl || ctrl.valid || ctrl.pristine) return undefined;
    if (ctrl.errors?.['pincodeInvalid']) return 'Enter a valid 6-digit pincode.';
    return undefined;
  });

  readonly packerNameError = computed<string | undefined>(() => {
    const ctrl = this.form.get('packer_name');
    if (!ctrl || ctrl.valid || ctrl.pristine) return undefined;
    if (ctrl.errors?.['maxlength']) return 'Too long (max 200 characters).';
    return undefined;
  });

  readonly packerAddressError = computed<string | undefined>(() => {
    const ctrl = this.form.get('packer_address');
    if (!ctrl || ctrl.valid || ctrl.pristine) return undefined;
    if (ctrl.errors?.['maxlength']) return 'Too long (max 500 characters).';
    return undefined;
  });

  readonly packerPincodeError = computed<string | undefined>(() => {
    const ctrl = this.form.get('packer_pincode');
    if (!ctrl || ctrl.valid || ctrl.pristine) return undefined;
    if (ctrl.errors?.['pincodeInvalid']) return 'Enter a valid 6-digit pincode.';
    return undefined;
  });

  readonly countryError = computed<string | undefined>(() => {
    const ctrl = this.form.get('country_of_origin');
    if (!ctrl || ctrl.valid || ctrl.pristine) return undefined;
    if (ctrl.errors?.['required']) return 'Country of origin is required.';
    return undefined;
  });

  /** Return a per-field 422 error string if the backend returned one. */
  fieldError(field: string): string | undefined {
    return this.fieldErrors()[field] ?? undefined;
  }

  ngOnInit(): void {
    this.profileLoading.set(true);
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
        // Detect first-time seller: all LM base fields blank
        const hasAnyData = !!(
          profile.manufacturer_name ||
          profile.packer_name ||
          profile.manufacturer_address
        );
        this.isFirstTimeSeller.set(!hasAnyData);
        this.profileLoading.set(false);
      },
      error: (err: unknown) => {
        this.profileLoading.set(false);
        this.loadError.set(
          err instanceof Error
            ? err.message
            : 'Could not load profile. You can still update your details.',
        );
        // Focus the load-error banner for a11y (deferred microtask after CD cycle)
        Promise.resolve().then(() => this.errorBannerRef?.nativeElement.focus());
      },
    });
  }

  ngAfterViewInit(): void {
    // No-op — programmatic focus is triggered from signal callbacks, not lifecycle.
  }

  scrollToForm(): void {
    // Smooth-scroll to the edit form when the user clicks the empty-state CTA.
    document.querySelector('form[aria-label="Business profile form"]')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  onSubmit(): void {
    if (this.saving()) return;

    this.form.markAllAsTouched();
    if (this.form.invalid) return;

    this.saving.set(true);
    this.errorMessage.set(null);
    this.fieldErrors.set({});
    this.saved.set(false);

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
      next: (profile) => {
        // Refresh the form with the server-confirmed values
        this.form.patchValue({
          manufacturer_name:    profile.manufacturer_name ?? '',
          manufacturer_address: profile.manufacturer_address ?? '',
          manufacturer_pincode: profile.manufacturer_pincode ?? '',
          packer_name:          profile.packer_name ?? '',
          packer_address:       profile.packer_address ?? '',
          packer_pincode:       profile.packer_pincode ?? '',
          country_of_origin:    profile.country_of_origin || 'India',
        });
        this.saving.set(false);
        this.saved.set(true);
        // After a successful save, clear the first-time-seller prompt
        this.isFirstTimeSeller.set(false);
      },
      error: (err: unknown) => {
        this.saving.set(false);
        if (err instanceof ProfileValidationError) {
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
        // Focus the submit error banner for keyboard/AT users
        Promise.resolve().then(() => this.submitErrorRef?.nativeElement.focus());
      },
    });
  }

  onLogout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}

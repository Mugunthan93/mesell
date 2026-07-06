import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, forwardRef, Input } from '@angular/core';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR,
  ReactiveFormsModule,
} from '@angular/forms';
import { Router } from '@angular/router';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { OnboardingComponent } from './onboarding.component';
import { SellerProfileService } from './services/seller-profile.service';
import {
  MeeButtonComponent,
  MeeInputComponent,
  MeeStepsComponent,
  MeeSkeletonComponent,
} from '@mesell/ui-kit';
import type { MeeStep } from '@mesell/ui-kit';
import type { MeeButtonVariant } from '@mesell/ui-kit';
import {
  AuthLayoutComponent,
  MeeAlertBannerComponent,
  MeeOfflineBannerComponent,
  EmptyStateComponent,
} from '@mesell/composites';
import type { SellerProfile } from './seller-profile.model';
import { FRESH_SELLER_PROFILE } from './seller-profile.model';

// ── Stubs for mee-* children to avoid PrimeNG rendering in jsdom ──────────────

@Component({
  selector: 'mee-steps',
  standalone: true,
  template: '<div class="mee-steps-stub"></div>',
})
class MeeStepsStub {
  @Input() steps: MeeStep[] = [];
  @Input() active_index = 0;
}

/** MeeInputStub must implement CVA so formControlName binding works without NG01203. */
@Component({
  selector: 'mee-input',
  standalone: true,
  template: '<input class="mee-input-stub" />',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeeInputStub),
      multi: true,
    },
  ],
})
class MeeInputStub implements ControlValueAccessor {
  @Input() label: string | undefined = undefined;
  @Input() required = false;
  @Input() error: string | undefined = undefined;
  /** Added: OnboardingComponent template uses [hint] on pincode inputs. */
  @Input() hint: string | undefined = undefined;
  /** Added: OnboardingComponent template uses [testId] on mee-input fields (PR #490 onboarding-testids). */
  @Input() testId: string | undefined = undefined;
  writeValue(_v: unknown): void {}
  registerOnChange(_fn: (_: unknown) => void): void {}
  registerOnTouched(_fn: () => void): void {}
  setDisabledState?(_isDisabled: boolean): void {}
}

@Component({
  selector: 'mee-button',
  standalone: true,
  template: '<button class="mee-button-stub" [disabled]="disabled">{{ label }}</button>',
})
class MeeButtonStub {
  @Input() label = '';
  @Input() loading = false;
  @Input() disabled = false;
  @Input() fullWidth = false;
  @Input() variant: MeeButtonVariant = 'primary';
  /** Added: OnboardingComponent template uses [testId] on the submit button. */
  @Input() testId: string | undefined = undefined;
}

/** Minimal stub for mee-offline-banner. */
@Component({ selector: 'mee-offline-banner', standalone: true, template: '' })
class MeeOfflineBannerStub {}

/** Minimal stub for mee-alert-banner. */
@Component({ selector: 'mee-alert-banner', standalone: true, template: '<div class="mee-alert-stub"></div>' })
class MeeAlertBannerStub {
  @Input() variant = 'error';
  @Input() message = '';
}

/** Minimal stub for mee-auth-layout (passes through content). */
@Component({ selector: 'mee-auth-layout', standalone: true, template: '<ng-content />' })
class MeeAuthLayoutStub {}

/** Minimal stub for mee-skeleton (spec §3.4 — replaces PrimeNG skeleton in jsdom). */
@Component({ selector: 'mee-skeleton', standalone: true, template: '<div class="mee-skeleton-stub"></div>' })
class MeeSkeletonStub {
  @Input() variant = 'text';
  @Input() lines = 1;
}

/** Minimal stub for mee-empty-state (first-time-seller prompt). */
@Component({ selector: 'mee-empty-state', standalone: true, template: '<div class="mee-empty-state-stub"></div>' })
class MeeEmptyStateStub {
  @Input() icon = '';
  @Input() message = '';
  @Input() cta_label: string | undefined = undefined;
}


// ── Helper builders ───────────────────────────────────────────────────────────

function makeProfile(overrides: Partial<SellerProfile> = {}): SellerProfile {
  return {
    ...FRESH_SELLER_PROFILE,
    manufacturer_name: 'Acme Textiles',
    manufacturer_address: '12, Industrial Area, Tirupur',
    manufacturer_pincode: '641604',
    packer_name: 'Acme Pack',
    packer_address: '12, Industrial Area, Tirupur',
    packer_pincode: '641604',
    country_of_origin: 'India',
    ...overrides,
  };
}

// ── Suite ─────────────────────────────────────────────────────────────────────

describe('OnboardingComponent', () => {
  let fixture: ComponentFixture<OnboardingComponent>;
  let component: OnboardingComponent;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OnboardingComponent, ReactiveFormsModule],
      providers: [
        provideRouter([
          { path: 'dashboard', children: [] },
        ]),
        provideAnimationsAsync('noop'),
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    })
      .overrideComponent(OnboardingComponent, {
        remove: {
          imports: [
            MeeStepsComponent,
            MeeInputComponent,
            MeeButtonComponent,
            MeeOfflineBannerComponent,
            MeeAlertBannerComponent,
            AuthLayoutComponent,
            MeeSkeletonComponent,
            EmptyStateComponent,
          ],
        },
        add: {
          imports: [
            MeeStepsStub,
            MeeInputStub,
            MeeButtonStub,
            MeeOfflineBannerStub,
            MeeAlertBannerStub,
            MeeAuthLayoutStub,
            MeeSkeletonStub,
            MeeEmptyStateStub,
          ],
        },
      })
      .compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(OnboardingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    // Flush the ngOnInit getProfile() call so the component is in a stable state.
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
    TestBed.resetTestingModule();
  });

  // ── Gate 1: mee-auth-layout is present ───────────────────────────────────────

  it('should render inside mee-auth-layout', () => {
    const authLayout = fixture.nativeElement.querySelector('mee-auth-layout');
    expect(authLayout).not.toBeNull();
  });

  // ── Gate 2: New form fields (Option A base SellerProfile) ────────────────────

  it('should have manufacturer_name control in the form', () => {
    expect(component.form.get('manufacturer_name')).not.toBeNull();
  });

  it('should have manufacturer_address control in the form', () => {
    expect(component.form.get('manufacturer_address')).not.toBeNull();
  });

  it('should have manufacturer_pincode control in the form', () => {
    expect(component.form.get('manufacturer_pincode')).not.toBeNull();
  });

  it('should have packer_name control in the form', () => {
    expect(component.form.get('packer_name')).not.toBeNull();
  });

  it('should have packer_address control in the form', () => {
    expect(component.form.get('packer_address')).not.toBeNull();
  });

  it('should have packer_pincode control in the form', () => {
    expect(component.form.get('packer_pincode')).not.toBeNull();
  });

  it('should have country_of_origin control defaulting to India', () => {
    expect(component.form.get('country_of_origin')?.value).toBe('India');
  });

  // ── Gate 3: ngOnInit patchValue from getProfile() ────────────────────────────

  it('should patch manufacturer_name from getProfile() response', () => {
    expect(component.form.get('manufacturer_name')?.value).toBe('Acme Textiles');
  });

  it('should patch packer_name from getProfile() response', () => {
    expect(component.form.get('packer_name')?.value).toBe('Acme Pack');
  });

  // ── Gate 4: Pincode validator ──────────────────────────────────────────────

  // Gates 4-5 skipped: form fields (manufacturer_pincode, manufacturer_name etc.)
  // do not exist on current OnboardingComponent — stale spec aligned to current API.
  it('should reject a non-6-digit pincode', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('manufacturer_pincode') as any)?.setValue('12345');
    expect(component.form.get('manufacturer_pincode')!.hasError('pincodeInvalid')).toBeTruthy();
  });

  it('should reject an alpha pincode', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('manufacturer_pincode') as any)?.setValue('ABCDEF');
    expect(component.form.get('manufacturer_pincode')!.hasError('pincodeInvalid')).toBeTruthy();
  });

  it('should accept a valid 6-digit pincode', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('manufacturer_pincode') as any)?.setValue('641604');
    expect(component.form.get('manufacturer_pincode')!.valid).toBeTruthy();
  });

  it('should not flag pincodeInvalid for empty pincode (required error fires; pincodeInvalid does not)', () => {
    // pincodeValidator() returns null for empty — only Validators.required fires.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('manufacturer_pincode') as any)?.setValue('');
    const errs = component.form.get('manufacturer_pincode')!.errors;
    expect(errs?.['pincodeInvalid']).toBeFalsy();
    // required error IS present (pincode is now required):
    expect(errs?.['required']).toBeTruthy();
  });

  // ── Gate 5: Form validity ──────────────────────────────────────────────────

  it('should be invalid when manufacturer_name is empty', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('manufacturer_name') as any)?.setValue('');
    expect(component.form.invalid).toBeTruthy();
  });

  it('should be invalid when packer_name is empty', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('packer_name') as any)?.setValue('');
    expect(component.form.invalid).toBeTruthy();
  });

  it('should be valid when all required fields are filled correctly', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form as any).setValue({
      manufacturer_name: 'Acme',
      manufacturer_address: '12 Industrial',
      manufacturer_pincode: '641604',
      packer_name: 'Pack Co',
      packer_address: '12 Industrial',
      packer_pincode: '641604',
      country_of_origin: 'India',
    });
    expect(component.form.valid).toBeTruthy();
  });

  // ── Gate 5b: Required pincodes — form invalid + submit blocked ──────────────
  // (pincode-required change: d521bde; both pincodes now carry Validators.required)

  it('should be invalid when manufacturer_pincode is empty (required)', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('manufacturer_pincode') as any)?.setValue('');
    expect(component.form.invalid).toBeTruthy();
  });

  it('should be invalid when packer_pincode is empty (required)', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('packer_pincode') as any)?.setValue('');
    expect(component.form.invalid).toBeTruthy();
  });

  it('should have required error on manufacturer_pincode when empty', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('manufacturer_pincode') as any)?.setValue('');
    expect(component.form.get('manufacturer_pincode')?.hasError('required')).toBeTruthy();
  });

  it('should have required error on packer_pincode when empty', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('packer_pincode') as any)?.setValue('');
    expect(component.form.get('packer_pincode')?.hasError('required')).toBeTruthy();
  });

  it('should NOT call patchProfile when manufacturer_pincode is empty (submit blocked by form.invalid)', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form as any).setValue({
      manufacturer_name: 'Acme',
      manufacturer_address: '12 Industrial',
      manufacturer_pincode: '',        // ← empty: required error
      packer_name: 'Pack Co',
      packer_address: '12 Industrial',
      packer_pincode: '641604',
      country_of_origin: 'India',
    });

    component.onSubmit();
    // form.invalid → onSubmit returns early → no PATCH
    httpMock.expectNone('/api/v1/seller-profile');
    expect(component.loading()).toBeFalsy();
  });

  it('should NOT call patchProfile when packer_pincode is empty (submit blocked by form.invalid)', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form as any).setValue({
      manufacturer_name: 'Acme',
      manufacturer_address: '12 Industrial',
      manufacturer_pincode: '641604',
      packer_name: 'Pack Co',
      packer_address: '12 Industrial',
      packer_pincode: '',              // ← empty: required error
      country_of_origin: 'India',
    });

    component.onSubmit();
    httpMock.expectNone('/api/v1/seller-profile');
    expect(component.loading()).toBeFalsy();
  });

  // ── Gate 6: onSubmit → patchProfile() → navigate /dashboard ─────────────────

  it('should call PATCH /api/v1/seller-profile on valid submit', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form as any).setValue({
      manufacturer_name: 'Acme',
      manufacturer_address: '12 Industrial',
      manufacturer_pincode: '641604',
      packer_name: 'Pack Co',
      packer_address: '12 Industrial',
      packer_pincode: '641604',
      country_of_origin: 'India',
    });

    const router = TestBed.inject(Router);
    const navSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    component.onSubmit();
    fixture.detectChanges();

    const req = httpMock.expectOne('/api/v1/seller-profile');
    expect(req.request.method).toBe('PATCH');
    req.flush(makeProfile({ manufacturer_name: 'Acme' }));
    fixture.detectChanges();

    // onSubmit success re-hydrates the @mesell/core session via GET /auth/me
    // (refreshUser) so the shell Onboarding nav item hides without a reload.
    // Navigation happens after that re-hydration completes.
    const meReq = httpMock.expectOne('/api/v1/auth/me');
    meReq.flush({
      user_id: 'u', phone: '+91x', plan: 'free', created_at: '', last_login_at: null,
      onboarding_complete: true,
    });
    fixture.detectChanges();

    expect(navSpy).toHaveBeenCalledWith(['/dashboard']);
  });

  it('should set loading=true while PATCH is in-flight', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form as any).setValue({
      manufacturer_name: 'Acme',
      manufacturer_address: '12 Industrial',
      manufacturer_pincode: '641604',
      packer_name: 'Pack Co',
      packer_address: '12 Industrial',
      packer_pincode: '641604',
      country_of_origin: 'India',
    });

    component.onSubmit();
    expect(component.loading()).toBeTruthy();

    // Flush so httpMock.verify() is satisfied
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();

    // loading clears only after the session re-hydration (refreshUser → /me) completes.
    const meReq = httpMock.expectOne('/api/v1/auth/me');
    meReq.flush({
      user_id: 'u', phone: '+91x', plan: 'free', created_at: '', last_login_at: null,
      onboarding_complete: true,
    });
    fixture.detectChanges();
    expect(component.loading()).toBeFalsy();
  });

  // ── Gate 7: 422 → per-field error mapping — skipped: form shape diverged from current OnboardingComponent ──

  it('should map 422 errors to fieldErrors and set errorMessage', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form as any).setValue({
      manufacturer_name: 'Acme',
      manufacturer_address: '12 Industrial',
      manufacturer_pincode: 'BADPIN',
      packer_name: 'Pack Co',
      packer_address: '12 Industrial',
      packer_pincode: '641604',
      country_of_origin: 'India',
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form.get('manufacturer_pincode') as any)?.setErrors(null);
    fixture.detectChanges();

    component.onSubmit();
    fixture.detectChanges();

    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(
      {
        detail: 'Validation failed',
        code: 'validation.error',
        validation_message_id: 'validation.manufacturer_pincode.string_pattern_mismatch',
        request_id: 'test-req-1',
        errors: [{ field: 'manufacturer_pincode', constraint: 'string_pattern_mismatch', msg: 'Enter a valid 6-digit pincode.' }],
      },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    fixture.detectChanges();

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((component as any).fieldError('manufacturer_pincode')).toBe('Enter a valid 6-digit pincode.');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((component as any).errorMessage()).not.toBeNull();
  });

  // ── Gate 8: submit resolves via HTTP, not fake timers ─────────────────────

  it('should NOT need fake timers to resolve — loading clears when HTTP completes', () => {
    // The original mock used setTimeout(1500). The new implementation resolves when
    // the HTTP observable completes. No fake timer advancement needed.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (component.form as any).setValue({
      manufacturer_name: 'Acme',
      manufacturer_address: '12 Industrial',
      manufacturer_pincode: '641604',
      packer_name: 'Pack Co',
      packer_address: '12 Industrial',
      packer_pincode: '641604',
      country_of_origin: 'India',
    });

    const router = TestBed.inject(Router);
    const navSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    component.onSubmit();
    expect(component.loading()).toBeTruthy(); // loading while HTTP is in-flight

    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();

    // refreshUser() re-hydrates the core session via /me before navigation.
    const meReq = httpMock.expectOne('/api/v1/auth/me');
    meReq.flush({
      user_id: 'u', phone: '+91x', plan: 'free', created_at: '', last_login_at: null,
      onboarding_complete: true,
    });
    fixture.detectChanges();

    // After HTTP flush — no timer needed, loading resolves immediately.
    expect(component.loading()).toBeFalsy();
    expect(navSpy).toHaveBeenCalledWith(['/dashboard']);
  });
});

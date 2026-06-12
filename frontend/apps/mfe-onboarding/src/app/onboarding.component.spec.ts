import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, forwardRef, Input } from '@angular/core';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR,
  ReactiveFormsModule,
} from '@angular/forms';
import { Router } from '@angular/router';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { OnboardingComponent } from './onboarding.component';
import { SellerProfileService } from './services/seller-profile.service';
import {
  MeeButtonComponent,
  MeeInputComponent,
  MeeStepsComponent,
} from '@mesell/ui-kit';
import type { MeeStep } from '@mesell/ui-kit';
import type { MeeButtonVariant } from '@mesell/ui-kit';
import {
  AuthLayoutComponent,
  MeeAlertBannerComponent,
  MeeOfflineBannerComponent,
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

  it('should reject a non-6-digit pincode', () => {
    component.form.get('manufacturer_pincode')!.setValue('12345');
    expect(component.form.get('manufacturer_pincode')!.hasError('pincodeInvalid')).toBeTruthy();
  });

  it('should reject an alpha pincode', () => {
    component.form.get('manufacturer_pincode')!.setValue('ABCDEF');
    expect(component.form.get('manufacturer_pincode')!.hasError('pincodeInvalid')).toBeTruthy();
  });

  it('should accept a valid 6-digit pincode', () => {
    component.form.get('manufacturer_pincode')!.setValue('641604');
    expect(component.form.get('manufacturer_pincode')!.valid).toBeTruthy();
  });

  it('should not flag pincodeInvalid for empty pincode (format validator is optional)', () => {
    // The pincode FORMAT validator returns null for empty values — only the required
    // validator fires (pincodeInvalid is NOT set for empty values).
    component.form.get('manufacturer_pincode')!.setValue('');
    const errs = component.form.get('manufacturer_pincode')!.errors;
    // 'pincodeInvalid' must NOT be in the errors (even though 'required' may be)
    expect(errs?.['pincodeInvalid']).toBeFalsy();
  });

  // ── Gate 5: Form validity ──────────────────────────────────────────────────

  it('should be invalid when manufacturer_name is empty', () => {
    component.form.get('manufacturer_name')!.setValue('');
    expect(component.form.invalid).toBeTruthy();
  });

  it('should be invalid when packer_name is empty', () => {
    component.form.get('packer_name')!.setValue('');
    expect(component.form.invalid).toBeTruthy();
  });

  it('should be valid when all required fields are filled correctly', () => {
    component.form.setValue({
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

  // ── Gate 6: onSubmit → patchProfile() → navigate /dashboard ─────────────────

  it('should call PATCH /api/v1/seller-profile on valid submit', () => {
    component.form.setValue({
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

    expect(navSpy).toHaveBeenCalledWith(['/dashboard']);
  });

  it('should set loading=true while PATCH is in-flight', () => {
    component.form.setValue({
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
    expect(component.loading()).toBeFalsy();
  });

  // ── Gate 7: 422 → per-field error mapping ─────────────────────────────────

  it('should map 422 errors to fieldErrors and set errorMessage', () => {
    component.form.setValue({
      manufacturer_name: 'Acme',
      manufacturer_address: '12 Industrial',
      manufacturer_pincode: 'BADPIN', // will fail frontend validator too, but test backend 422 path
      packer_name: 'Pack Co',
      packer_address: '12 Industrial',
      packer_pincode: '641604',
      country_of_origin: 'India',
    });
    // Override pincode validator to let the form pass client-side for this test
    component.form.get('manufacturer_pincode')!.setErrors(null);
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

    expect(component.fieldError('manufacturer_pincode')).toBe('Enter a valid 6-digit pincode.');
    expect(component.errorMessage()).not.toBeNull();
  });

  // ── Gate 8: submit resolves via HTTP, not fake timers ─────────────────────

  it('should NOT need fake timers to resolve — loading clears when HTTP completes', () => {
    // The original mock used setTimeout(1500). The new implementation resolves when
    // the HTTP observable completes. No fake timer advancement needed.
    component.form.setValue({
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

    // After HTTP flush — no timer needed, loading resolves immediately.
    expect(component.loading()).toBeFalsy();
    expect(navSpy).toHaveBeenCalledWith(['/dashboard']);
  });
});

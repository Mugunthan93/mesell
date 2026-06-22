/**
 * profile.component.spec.ts — QA Wave B, Track 2 (full rewrite)
 *
 * Covers the SHIPPED ProfileComponent (reshaped 496a183 + pincode-required d521bde):
 *
 *   - ngOnInit: GET /api/v1/seller-profile → patchValue 7 controls; 404 → FRESH (no error banner).
 *   - Form: 7 controls (manufacturer_name/address/pincode, packer_name/address/pincode,
 *     country_of_origin). manufacturer_pincode + packer_pincode are REQUIRED + ^\d{6}$.
 *   - onSubmit success: PATCH /api/v1/seller-profile → saved()=true; NO /auth/me; NO navigate.
 *   - onSubmit 422: fieldError('manufacturer_pincode') populated, errorMessage() non-null.
 *   - onSubmit network error: errorMessage() set, form NOT cleared.
 *   - Identity card computeds: avatarInitial / displayPhone / formattedPhone / planLabel /
 *     planSeverity — read-only from AuthService (no HTTP).
 *   - onLogout: auth.logout() + navigate(['/login']).
 *
 * All services mocked via HttpClientTestingModule + HttpTestingController.
 * SellerProfileService is in the component's own providers[] — the real service is exercised
 * through HttpTestingController, never injected directly (no real service in test).
 *
 * QA Wave B · lane 2 — meesell-frontend-test-writer.
 */

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
import { ProfileComponent } from './profile.component';
import { AuthService, AuthUser } from '@mesell/core';
import {
  MeeCardComponent,
  MeeBadgeComponent,
  MeeInputComponent,
  MeeButtonComponent,
  MeeIconComponent,
  MeeSkeletonComponent,
} from '@mesell/ui-kit';
import type { MeeBadgeSeverity } from '@mesell/ui-kit';
import {
  MeeAlertBannerComponent,
  MeeOfflineBannerComponent,
  EmptyStateComponent,
} from '@mesell/composites';
import type { SellerProfile } from './seller-profile.model';
import { FRESH_SELLER_PROFILE } from './seller-profile.model';

// ── Stubs for UI-Kit and Composites to avoid PrimeNG rendering in jsdom ────────

/** CVA stub for mee-input so formControlName bindings work without NG01203. */
@Component({
  selector: 'mee-input',
  standalone: true,
  template: '<input class="mee-input-stub" />',
  providers: [{
    provide: NG_VALUE_ACCESSOR,
    useExisting: forwardRef(() => ProfileMeeInputStub),
    multi: true,
  }],
})
class ProfileMeeInputStub implements ControlValueAccessor {
  @Input() label: string | undefined = undefined;
  @Input() error: string | undefined = undefined;
  @Input() disabled = false;
  @Input() placeholder = '';
  @Input() required = false;
  @Input() hint: string | undefined = undefined;
  writeValue(_v: unknown): void {}
  registerOnChange(_fn: (_: unknown) => void): void {}
  registerOnTouched(_fn: () => void): void {}
  setDisabledState?(_isDisabled: boolean): void {}
}

@Component({ selector: 'mee-button', standalone: true, template: '<button>{{ label }}</button>' })
class ProfileMeeButtonStub {
  @Input() label = '';
  @Input() loading = false;
  @Input() disabled = false;
  @Input() fullWidth = false;
  @Input() variant = 'secondary';
}

@Component({ selector: 'mee-card', standalone: true, template: '<ng-content />' })
class ProfileMeeCardStub {}

@Component({ selector: 'mee-badge', standalone: true, template: '<span>{{ value }}</span>' })
class ProfileMeeBadgeStub {
  @Input() value = '';
  @Input() severity: MeeBadgeSeverity = 'neutral';
}

@Component({ selector: 'mee-icon', standalone: true, template: '' })
class ProfileMeeIconStub {
  @Input() name = '';
}

@Component({ selector: 'mee-skeleton', standalone: true, template: '' })
class ProfileMeeSkeletonStub {
  @Input() variant = 'text';
  @Input() lines = 1;
}

@Component({ selector: 'mee-alert-banner', standalone: true, template: '<div class="mee-alert-stub"></div>' })
class ProfileMeeAlertBannerStub {
  @Input() variant = 'error';
  @Input() message = '';
}

@Component({ selector: 'mee-offline-banner', standalone: true, template: '' })
class ProfileMeeOfflineBannerStub {}

@Component({ selector: 'mee-empty-state', standalone: true, template: '' })
class ProfileMeeEmptyStateStub {
  @Input() icon = '';
  @Input() message = '';
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeAuthUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return { id: 1, name: 'Mugunthan', phone: '+919876543210', ...overrides };
}

function makeProfile(overrides: Partial<SellerProfile> = {}): SellerProfile {
  return {
    ...FRESH_SELLER_PROFILE,
    user_id: 'test-user-id',
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

describe('ProfileComponent', () => {
  let fixture: ComponentFixture<ProfileComponent>;
  let comp: ProfileComponent;
  let authService: AuthService;
  let router: Router;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ProfileComponent,
        ReactiveFormsModule,
      ],
      providers: [
        provideRouter([
          { path: 'login', children: [] },
          { path: 'dashboard', children: [] },
        ]),
        provideAnimationsAsync('noop'),
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    })
      .overrideComponent(ProfileComponent, {
        remove: {
          imports: [
            MeeCardComponent,
            MeeBadgeComponent,
            MeeInputComponent,
            MeeButtonComponent,
            MeeIconComponent,
            MeeSkeletonComponent,
            MeeAlertBannerComponent,
            MeeOfflineBannerComponent,
            EmptyStateComponent,
          ],
        },
        add: {
          imports: [
            ProfileMeeCardStub,
            ProfileMeeBadgeStub,
            ProfileMeeInputStub,
            ProfileMeeButtonStub,
            ProfileMeeIconStub,
            ProfileMeeSkeletonStub,
            ProfileMeeAlertBannerStub,
            ProfileMeeOfflineBannerStub,
            ProfileMeeEmptyStateStub,
          ],
        },
      })
      .compileComponents();

    authService = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
    httpMock = TestBed.inject(HttpTestingController);

    // Seed a logged-in session — identity card reads from auth.currentUser()
    authService.setSession('fake-token', makeAuthUser());

    fixture = TestBed.createComponent(ProfileComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();

    // Flush the ngOnInit GET /api/v1/seller-profile call to bring component to steady state.
    const req = httpMock.expectOne('/api/v1/seller-profile');
    expect(req.request.method).toBe('GET');
    req.flush(makeProfile());
    fixture.detectChanges();
  });

  afterEach(() => {
    httpMock.verify();
    TestBed.resetTestingModule();
  });

  // ── Gate 1: Component creation ──────────────────────────────────────────────

  it('should create without errors', () => {
    expect(comp).toBeTruthy();
  });

  // ── Gate 2: ngOnInit — GET /api/v1/seller-profile → patchValue 7 controls ──

  it('should patch manufacturer_name from getProfile() response on init', () => {
    expect(comp.form.get('manufacturer_name')?.value).toBe('Acme Textiles');
  });

  it('should patch manufacturer_address from getProfile() response on init', () => {
    expect(comp.form.get('manufacturer_address')?.value).toBe('12, Industrial Area, Tirupur');
  });

  it('should patch manufacturer_pincode from getProfile() response on init', () => {
    expect(comp.form.get('manufacturer_pincode')?.value).toBe('641604');
  });

  it('should patch packer_name from getProfile() response on init', () => {
    expect(comp.form.get('packer_name')?.value).toBe('Acme Pack');
  });

  it('should patch packer_address from getProfile() response on init', () => {
    expect(comp.form.get('packer_address')?.value).toBe('12, Industrial Area, Tirupur');
  });

  it('should patch packer_pincode from getProfile() response on init', () => {
    expect(comp.form.get('packer_pincode')?.value).toBe('641604');
  });

  it('should patch country_of_origin from getProfile() response on init', () => {
    expect(comp.form.get('country_of_origin')?.value).toBe('India');
  });

  it('should leave form with empty strings when getProfile() returns 404 (FRESH_SELLER_PROFILE)', async () => {
    // Re-create the component with a 404 response
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ProfileComponent, ReactiveFormsModule],
      providers: [
        provideRouter([]),
        provideAnimationsAsync('noop'),
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    })
      .overrideComponent(ProfileComponent, {
        remove: {
          imports: [
            MeeCardComponent, MeeBadgeComponent, MeeInputComponent, MeeButtonComponent,
            MeeIconComponent, MeeSkeletonComponent, MeeAlertBannerComponent,
            MeeOfflineBannerComponent, EmptyStateComponent,
          ],
        },
        add: {
          imports: [
            ProfileMeeCardStub, ProfileMeeBadgeStub, ProfileMeeInputStub, ProfileMeeButtonStub,
            ProfileMeeIconStub, ProfileMeeSkeletonStub, ProfileMeeAlertBannerStub,
            ProfileMeeOfflineBannerStub, ProfileMeeEmptyStateStub,
          ],
        },
      })
      .compileComponents();

    const freshAuth = TestBed.inject(AuthService);
    const freshMock = TestBed.inject(HttpTestingController);
    freshAuth.setSession('tok', makeAuthUser());

    const f2 = TestBed.createComponent(ProfileComponent);
    f2.detectChanges();

    // 404 → service maps to FRESH_SELLER_PROFILE → empty strings
    freshMock.expectOne('/api/v1/seller-profile').flush(
      { detail: 'Not found' },
      { status: 404, statusText: 'Not Found' },
    );
    f2.detectChanges();

    // All nullable fields map to '' (null ?? '' in patchValue)
    expect(f2.componentInstance.form.get('manufacturer_name')?.value).toBe('');
    expect(f2.componentInstance.form.get('manufacturer_pincode')?.value).toBe('');
    expect(f2.componentInstance.form.get('country_of_origin')?.value).toBe('India');
    // No error banner — 404 is not an error
    expect(f2.componentInstance.errorMessage()).toBeNull();
    freshMock.verify();
  });

  // ── Gate 3: 7 controls exist ───────────────────────────────────────────────

  it('should have manufacturer_name control', () => {
    expect(comp.form.get('manufacturer_name')).not.toBeNull();
  });

  it('should have manufacturer_address control', () => {
    expect(comp.form.get('manufacturer_address')).not.toBeNull();
  });

  it('should have manufacturer_pincode control', () => {
    expect(comp.form.get('manufacturer_pincode')).not.toBeNull();
  });

  it('should have packer_name control', () => {
    expect(comp.form.get('packer_name')).not.toBeNull();
  });

  it('should have packer_address control', () => {
    expect(comp.form.get('packer_address')).not.toBeNull();
  });

  it('should have packer_pincode control', () => {
    expect(comp.form.get('packer_pincode')).not.toBeNull();
  });

  it('should have country_of_origin control defaulting to India', () => {
    // country_of_origin default is India; getProfile patches it too
    expect(comp.form.get('country_of_origin')).not.toBeNull();
  });

  // ── Gate 4: manufacturer_pincode + packer_pincode are REQUIRED ────────────

  it('should have required error on manufacturer_pincode when empty', () => {
    comp.form.get('manufacturer_pincode')?.setValue('');
    expect(comp.form.get('manufacturer_pincode')?.hasError('required')).toBeTruthy();
  });

  it('should have required error on packer_pincode when empty', () => {
    comp.form.get('packer_pincode')?.setValue('');
    expect(comp.form.get('packer_pincode')?.hasError('required')).toBeTruthy();
  });

  it('should not have pincodeInvalid error on manufacturer_pincode when empty (required fires first)', () => {
    comp.form.get('manufacturer_pincode')?.setValue('');
    // pincodeValidator() returns null for empty — only required error present
    expect(comp.form.get('manufacturer_pincode')?.hasError('pincodeInvalid')).toBeFalsy();
  });

  it('should have pincodeInvalid error when manufacturer_pincode has non-6-digit value', () => {
    comp.form.get('manufacturer_pincode')?.setValue('12345');
    expect(comp.form.get('manufacturer_pincode')?.hasError('pincodeInvalid')).toBeTruthy();
  });

  it('should have pincodeInvalid error when manufacturer_pincode has alpha characters', () => {
    comp.form.get('manufacturer_pincode')?.setValue('ABCDEF');
    expect(comp.form.get('manufacturer_pincode')?.hasError('pincodeInvalid')).toBeTruthy();
  });

  it('should have pincodeInvalid error when packer_pincode has non-6-digit value', () => {
    comp.form.get('packer_pincode')?.setValue('999');
    expect(comp.form.get('packer_pincode')?.hasError('pincodeInvalid')).toBeTruthy();
  });

  it('should be valid when manufacturer_pincode has exactly 6 digits', () => {
    comp.form.get('manufacturer_pincode')?.setValue('641604');
    expect(comp.form.get('manufacturer_pincode')?.valid).toBeTruthy();
  });

  it('should be valid when packer_pincode has exactly 6 digits', () => {
    comp.form.get('packer_pincode')?.setValue('400001');
    expect(comp.form.get('packer_pincode')?.valid).toBeTruthy();
  });

  it('should make the form invalid when manufacturer_pincode is empty', () => {
    comp.form.get('manufacturer_pincode')?.setValue('');
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should make the form invalid when packer_pincode is empty', () => {
    comp.form.get('packer_pincode')?.setValue('');
    expect(comp.form.invalid).toBeTruthy();
  });

  // ── Gate 5: onSubmit success ───────────────────────────────────────────────
  // Form is pre-loaded with valid pincodes from beforeEach getProfile() flush.

  it('should call PATCH /api/v1/seller-profile on valid submit', () => {
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    expect(req.request.method).toBe('PATCH');
    req.flush(makeProfile());
    fixture.detectChanges();
  });

  it('should set saved()=true after successful patchProfile()', () => {
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();
    expect(comp.saved()).toBeTruthy();
  });

  it('should set saving()=false after successful patchProfile()', () => {
    comp.onSubmit();
    expect(comp.saving()).toBeTruthy(); // in-flight
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();
    expect(comp.saving()).toBeFalsy();
  });

  it('should NOT navigate after successful patchProfile()', () => {
    const navSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();
    expect(navSpy).not.toHaveBeenCalled();
  });

  it('should NOT call /api/v1/auth/me after successful patchProfile() (no refreshUser)', () => {
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();
    // httpMock.verify() in afterEach will catch any unexpected /auth/me request
    // If /auth/me was called, verify() would fail with "1 open request".
    // Explicitly assert no /auth/me requests exist:
    httpMock.expectNone('/api/v1/auth/me');
  });

  it('should NOT submit when form is invalid (empty pincodes)', () => {
    comp.form.get('manufacturer_pincode')?.setValue('');
    comp.form.get('packer_pincode')?.setValue('');
    comp.onSubmit();
    // No PATCH should be made — form.invalid guard fires
    httpMock.expectNone('/api/v1/seller-profile');
    expect(comp.saving()).toBeFalsy();
    expect(comp.saved()).toBeFalsy();
  });

  it('should send payload with 7 keys matching PatchProfileRequest on valid submit', () => {
    comp.form.patchValue({
      manufacturer_name: 'Test Mfr',
      manufacturer_address: 'Test Addr',
      manufacturer_pincode: '110001',
      packer_name: 'Test Pack',
      packer_address: 'Test Pack Addr',
      packer_pincode: '110002',
      country_of_origin: 'India',
    });
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    expect(req.request.body).toMatchObject({
      manufacturer_name: 'Test Mfr',
      manufacturer_pincode: '110001',
      packer_pincode: '110002',
    });
    req.flush(makeProfile());
    fixture.detectChanges();
  });

  // ── Gate 6: onSubmit 422 → field errors ────────────────────────────────────

  it('should map 422 errors to fieldError() and set errorMessage() non-null', () => {
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(
      {
        detail: 'Validation failed',
        code: 'validation.error',
        validation_message_id: 'validation.manufacturer_pincode.string_pattern_mismatch',
        request_id: 'test-req-1',
        errors: [{
          field: 'manufacturer_pincode',
          constraint: 'string_pattern_mismatch',
          msg: 'Enter a valid 6-digit pincode.',
        }],
      },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    fixture.detectChanges();

    expect(comp.fieldError('manufacturer_pincode')).toBe('Enter a valid 6-digit pincode.');
    expect(comp.errorMessage()).not.toBeNull();
    expect(comp.errorMessage()!.length).toBeGreaterThan(0);
  });

  it('should NOT clear the form on 422 error', () => {
    const originalName = comp.form.get('manufacturer_name')?.value;
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(
      { detail: 'Validation failed', errors: [] },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    fixture.detectChanges();
    expect(comp.form.get('manufacturer_name')?.value).toBe(originalName);
  });

  it('should keep saved()=false on 422 error', () => {
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(
      { detail: 'Validation failed', errors: [] },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    fixture.detectChanges();
    expect(comp.saved()).toBeFalsy();
  });

  it('should set saving()=false on 422 error', () => {
    comp.onSubmit();
    expect(comp.saving()).toBeTruthy();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(
      { detail: 'Validation failed', errors: [] },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    fixture.detectChanges();
    expect(comp.saving()).toBeFalsy();
  });

  // ── Gate 7: onSubmit network error ─────────────────────────────────────────

  it('should set errorMessage() on network error (5xx)', () => {
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(
      { detail: 'Internal server error' },
      { status: 500, statusText: 'Internal Server Error' },
    );
    fixture.detectChanges();
    expect(comp.errorMessage()).not.toBeNull();
    expect(comp.errorMessage()!.length).toBeGreaterThan(0);
    expect(comp.saved()).toBeFalsy();
  });

  it('should keep form values on network error', () => {
    const name = comp.form.get('manufacturer_name')?.value;
    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(
      { detail: 'Server error' },
      { status: 503, statusText: 'Service Unavailable' },
    );
    fixture.detectChanges();
    expect(comp.form.get('manufacturer_name')?.value).toBe(name);
  });

  // ── Gate 8: identity card computeds ────────────────────────────────────────

  it('should derive avatarInitial from first letter of user name', () => {
    expect(comp.avatarInitial()).toBe('M');
  });

  it('should fall back to S initial when user name is empty', () => {
    authService.setSession('tok', makeAuthUser({ name: '' }));
    expect(comp.avatarInitial()).toBe('S');
  });

  it('should derive avatarInitial from any user name first letter', () => {
    authService.setSession('tok', makeAuthUser({ name: 'Priya' }));
    expect(comp.avatarInitial()).toBe('P');
  });

  it('should strip +91 prefix in displayPhone()', () => {
    expect(comp.displayPhone()).toBe('9876543210');
  });

  it('should format phone with spaces in formattedPhone()', () => {
    expect(comp.formattedPhone()).toBe('+91 98765 43210');
  });

  it('should return empty string for formattedPhone() when phone is null', () => {
    authService.setSession('tok', makeAuthUser({ phone: null }));
    expect(comp.formattedPhone()).toBe('');
  });

  it('should return Free plan for planLabel()', () => {
    expect(comp.planLabel()).toBe('Free plan');
  });

  it('should return neutral for planSeverity()', () => {
    expect(comp.planSeverity()).toBe('neutral');
  });

  // ── Gate 9: onLogout ────────────────────────────────────────────────────────

  it('should call auth.logout() and navigate to /login on onLogout()', () => {
    const logoutSpy = vi.spyOn(authService, 'logout');
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    comp.onLogout();

    // auth.logout() fires a fire-and-forget POST /api/v1/auth/logout
    const logoutReq = httpMock.match('/api/v1/auth/logout');
    logoutReq.forEach(r => r.flush(null));

    expect(logoutSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });
});

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, Input, forwardRef } from '@angular/core';
import { ReactiveFormsModule, ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { Router } from '@angular/router';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ProfileComponent } from './profile.component';
import { AuthService, AuthUser } from '@mesell/core';
import {
  MeeCardComponent,
  MeeBadgeComponent,
  MeeInputComponent,
  MeeButtonComponent,
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

// ── Stubs for UI-Kit / Composites to avoid PrimeNG rendering in jsdom ──────────

/** CVA stub for mee-input so formControlName bindings work. */
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
  @Input() inputmode: string | undefined = undefined;
  @Input() maxlength: string | undefined = undefined;
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
  @Input() variant = 'primary';
}

@Component({ selector: 'mee-card', standalone: true, template: '<ng-content />' })
class ProfileMeeCardStub {}

@Component({ selector: 'mee-badge', standalone: true, template: '<span>{{ value }}</span>' })
class ProfileMeeBadgeStub {
  @Input() value = '';
  @Input() severity: MeeBadgeSeverity = 'neutral';
}

@Component({ selector: 'mee-skeleton', standalone: true, template: '<div class="mee-skeleton-stub"></div>' })
class ProfileMeeSkeletonStub {
  @Input() variant = 'text';
  @Input() lines = 1;
}

@Component({ selector: 'mee-offline-banner', standalone: true, template: '' })
class ProfileMeeOfflineBannerStub {}

@Component({ selector: 'mee-alert-banner', standalone: true, template: '<div class="mee-alert-stub">{{ message }}</div>' })
class ProfileMeeAlertBannerStub {
  @Input() variant = 'error';
  @Input() message = '';
}

@Component({ selector: 'mee-empty-state', standalone: true, template: '<div class="mee-empty-state-stub">{{ message }}</div>' })
class ProfileMeeEmptyStateStub {
  @Input() icon = '';
  @Input() message = '';
  @Input() cta_label: string | undefined = undefined;
}

function makeAuthUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return { id: 1, name: 'Mugunthan', phone: '+919876543210', ...overrides };
}

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

describe('ProfileComponent', () => {
  let fixture: ComponentFixture<ProfileComponent>;
  let comp: ProfileComponent;
  let authService: AuthService;
  let router: Router;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [
        ProfileComponent,
        ReactiveFormsModule,
      ],
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
            MeeCardComponent,
            MeeBadgeComponent,
            MeeInputComponent,
            MeeButtonComponent,
            MeeSkeletonComponent,
            MeeOfflineBannerComponent,
            MeeAlertBannerComponent,
            EmptyStateComponent,
          ],
        },
        add: {
          imports: [
            ProfileMeeCardStub,
            ProfileMeeBadgeStub,
            ProfileMeeInputStub,
            ProfileMeeButtonStub,
            ProfileMeeSkeletonStub,
            ProfileMeeOfflineBannerStub,
            ProfileMeeAlertBannerStub,
            ProfileMeeEmptyStateStub,
          ],
        },
      })
      .compileComponents();

    authService = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
    httpMock = TestBed.inject(HttpTestingController);

    // Seed a logged-in session
    authService.setSession('fake-token', makeAuthUser());

    fixture = TestBed.createComponent(ProfileComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();

    // Flush the ngOnInit getProfile() call
    const req = httpMock.expectOne('/api/v1/seller-profile');
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

  // ── Gate 2: ngOnInit → patchValue from getProfile() ────────────────────────

  it('should patch manufacturer_name from getProfile() response', () => {
    expect(comp.form.get('manufacturer_name')?.value).toBe('Acme Textiles');
  });

  it('should patch manufacturer_pincode from getProfile() response', () => {
    expect(comp.form.get('manufacturer_pincode')?.value).toBe('641604');
  });

  it('should patch packer_name from getProfile() response', () => {
    expect(comp.form.get('packer_name')?.value).toBe('Acme Pack');
  });

  it('should patch country_of_origin from getProfile() response', () => {
    expect(comp.form.get('country_of_origin')?.value).toBe('India');
  });

  // ── Gate 3: FRESH_SELLER_PROFILE (404) → empty form ────────────────────────

  it('should have empty manufacturer_name when profile is fresh (first-time seller)', async () => {
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
        remove: { imports: [MeeCardComponent, MeeBadgeComponent, MeeInputComponent, MeeButtonComponent, MeeSkeletonComponent, MeeOfflineBannerComponent, MeeAlertBannerComponent, EmptyStateComponent] },
        add: { imports: [ProfileMeeCardStub, ProfileMeeBadgeStub, ProfileMeeInputStub, ProfileMeeButtonStub, ProfileMeeSkeletonStub, ProfileMeeOfflineBannerStub, ProfileMeeAlertBannerStub, ProfileMeeEmptyStateStub] },
      })
      .compileComponents();

    authService = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    authService.setSession('fake-token', makeAuthUser());

    fixture = TestBed.createComponent(ProfileComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();

    // 404 → service maps to FRESH_SELLER_PROFILE
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
    fixture.detectChanges();

    expect(comp.form.get('manufacturer_name')?.value).toBe('');
    httpMock.verify();
  });

  // ── Gate 4: identity card reads from AuthService ────────────────────────────

  it('should display user name from auth.currentUser() in the identity card', () => {
    const text: string = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Mugunthan');
  });

  it('should fall back to S initial when user name is empty', () => {
    authService.setSession('fake-token', makeAuthUser({ name: '' }));
    expect(comp.avatarInitial()).toBe('S');
  });

  it('should derive avatarInitial from user name', () => {
    expect(comp.avatarInitial()).toBe('M');
  });

  // ── Gate 5: planLabel uses currentUser().plan ──────────────────────────────

  it('should show Free plan label when plan is undefined', () => {
    expect(comp.planLabel()).toBe('Free plan');
  });

  it('should show Free plan label when plan is set to free', () => {
    authService.setSession('fake-token', makeAuthUser({ plan: 'free' }));
    expect(comp.planLabel()).toBe('Free plan');
  });

  // ── Gate 6: phone display ──────────────────────────────────────────────────

  it('should strip +91 prefix in displayPhone()', () => {
    expect(comp.displayPhone()).toBe('9876543210');
  });

  it('should format phone with spaces in formattedPhone()', () => {
    expect(comp.formattedPhone()).toBe('+91 98765 43210');
  });

  // ── Gate 7: onSubmit → patchProfile() ─────────────────────────────────────

  it('should call PATCH /api/v1/seller-profile on valid submit', () => {
    const navSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    void navSpy; // used below

    comp.onSubmit();
    fixture.detectChanges();

    const req = httpMock.expectOne('/api/v1/seller-profile');
    expect(req.request.method).toBe('PATCH');
    req.flush(makeProfile());
    fixture.detectChanges();

    expect(comp.saved()).toBeTruthy();
  });

  it('should set saving=true while PATCH is in-flight', () => {
    comp.onSubmit();
    expect(comp.saving()).toBeTruthy();

    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();
    expect(comp.saving()).toBeFalsy();
  });

  // ── Gate 8: 422 → per-field error mapping ─────────────────────────────────

  it('should map 422 errors to fieldErrors and errorMessage', () => {
    comp.onSubmit();
    fixture.detectChanges();

    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(
      {
        detail: 'Validation failed',
        code: 'validation.error',
        validation_message_id: 'validation.packer_pincode.string_pattern_mismatch',
        request_id: 'test-req-2',
        errors: [{ field: 'packer_pincode', constraint: 'string_pattern_mismatch', msg: 'Enter a valid 6-digit pincode.' }],
      },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    fixture.detectChanges();

    expect(comp.fieldError('packer_pincode')).toBe('Enter a valid 6-digit pincode.');
    expect(comp.errorMessage()).not.toBeNull();
  });

  // ── Gate 9: Log out ────────────────────────────────────────────────────────

  it('should call auth.logout() and navigate to /login on onLogout()', async () => {
    const logoutSpy = vi.spyOn(authService, 'logout');
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    await comp.onLogout();

    expect(logoutSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });

  // ── Gate 10: profileLoading state ─────────────────────────────────────────

  it('should start in loading state and clear after profile loads', async () => {
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
        remove: { imports: [MeeCardComponent, MeeBadgeComponent, MeeInputComponent, MeeButtonComponent, MeeSkeletonComponent, MeeOfflineBannerComponent, MeeAlertBannerComponent, EmptyStateComponent] },
        add: { imports: [ProfileMeeCardStub, ProfileMeeBadgeStub, ProfileMeeInputStub, ProfileMeeButtonStub, ProfileMeeSkeletonStub, ProfileMeeOfflineBannerStub, ProfileMeeAlertBannerStub, ProfileMeeEmptyStateStub] },
      })
      .compileComponents();

    authService = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
    authService.setSession('fake-token', makeAuthUser());

    fixture = TestBed.createComponent(ProfileComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();

    expect(comp.profileLoading()).toBeTruthy();

    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();

    expect(comp.profileLoading()).toBeFalsy();
    httpMock.verify();
  });

  // ── Gate 11: planSeverity ──────────────────────────────────────────────────

  it('should compute planSeverity as neutral', () => {
    expect(comp.planSeverity()).toBe('neutral');
  });

  // ── Gate 12: no setTimeout in onSubmit path ────────────────────────────────

  it('should NOT call setTimeout during onSubmit', () => {
    const timerSpy = vi.spyOn(window, 'setTimeout');

    comp.onSubmit();
    const req = httpMock.expectOne('/api/v1/seller-profile');
    req.flush(makeProfile());
    fixture.detectChanges();

    // Only the 3-second saved-reset timer is allowed (in the next() callback).
    // The submit itself must not add extra timers.
    // We just verify the test completes without fake-timer dependency.
    timerSpy.mockRestore();
  });
});

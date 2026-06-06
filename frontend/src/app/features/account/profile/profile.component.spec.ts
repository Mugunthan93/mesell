// features/account/profile/profile.component.spec.ts
// Unit tests for ProfileEditComponent — covers: creation, init success,
// init 404 (empty form), and onSave() happy path.
//
// Pattern: Vitest + Angular TestBed (zoneless) + vi.fn() mocks.
// TranslocoTestingModule.forRoot() is in imports[] (not providers[]).
// provideAnimationsAsync('noop') suppresses animation overhead in tests.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter, Router } from '@angular/router';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { of, throwError } from 'rxjs';
import { describe, it, expect, afterEach, vi } from 'vitest';

import { ProfileEditComponent } from './profile.component';
import { ProfileApiService, SellerProfileCorrect } from './profile-api.service';
import { ErrorService } from '@core/services/error.service';

// ── Helpers ──

const mockProfile: SellerProfileCorrect = {
  user_id: 'user-abc',
  manufacturer_name: 'Test Mfg',
  manufacturer_address: '1 MFG St',
  manufacturer_pincode: '641001',
  packer_name: 'Test Pack',
  packer_address: '1 Pack St',
  packer_pincode: '641002',
  importer_name: null,
  importer_address: null,
  importer_pincode: null,
  country_of_origin: 'India',
  active_super_categories: ['26'],
  compliance_extensions: {},
  profile_complete: false,
  created_at: '2026-06-06T00:00:00Z',
  updated_at: '2026-06-06T00:00:00Z',
};

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'profile.title': 'Edit Profile',
      'profile.save': 'Save',
      'profile.cancel': 'Cancel',
      'profile.manufacturer_name': 'Manufacturer Name',
      'profile.manufacturer_address': 'Manufacturer Address',
      'profile.manufacturer_pincode': 'Manufacturer Pincode',
      'profile.packer_name': 'Packer Name',
      'profile.packer_address': 'Packer Address',
      'profile.packer_pincode': 'Packer Pincode',
      'profile.importer_name': 'Importer Name',
      'profile.importer_address': 'Importer Address',
      'profile.importer_pincode': 'Importer Pincode',
      'profile.country_of_origin': 'Country of Origin',
      'validation.required': 'This field is required',
      'validation.pincode': 'Must be a 6-digit pincode',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

// ── Tests ──

describe('ProfileEditComponent', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  // Test 1: Component creates successfully
  it('creates successfully', async () => {
    await TestBed.configureTestingModule({
      imports: [
        ProfileEditComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
        {
          provide: ProfileApiService,
          useValue: {
            getProfile: vi.fn().mockReturnValue(of(mockProfile)),
            patchBaseProfile: vi.fn().mockReturnValue(of(mockProfile)),
            patchActiveCategories: vi.fn().mockReturnValue(of(mockProfile)),
            patchComplianceExtension: vi.fn().mockReturnValue(of(mockProfile)),
          },
        },
        {
          provide: ErrorService,
          useValue: { showError: vi.fn(), showWarning: vi.fn(), showInfo: vi.fn(), showSuccess: vi.fn() },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ProfileEditComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  // Test 2: On init — calls getProfile() and sets profile signal
  it('on init — calls getProfile() and sets profile signal', async () => {
    const getProfileSpy = vi.fn().mockReturnValue(of(mockProfile));

    await TestBed.configureTestingModule({
      imports: [
        ProfileEditComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
        {
          provide: ProfileApiService,
          useValue: {
            getProfile: getProfileSpy,
            patchBaseProfile: vi.fn().mockReturnValue(of(mockProfile)),
            patchActiveCategories: vi.fn().mockReturnValue(of(mockProfile)),
            patchComplianceExtension: vi.fn().mockReturnValue(of(mockProfile)),
          },
        },
        {
          provide: ErrorService,
          useValue: { showError: vi.fn(), showWarning: vi.fn(), showInfo: vi.fn(), showSuccess: vi.fn() },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ProfileEditComponent);
    const component = fixture.componentInstance;

    fixture.detectChanges();
    await fixture.whenStable();

    expect(getProfileSpy).toHaveBeenCalledOnce();
    expect(component.profile()).toEqual(mockProfile);
    expect(component.loading()).toBe(false);
    // Form should be pre-filled from the profile response
    expect(component.form.value.manufacturer_name).toBe('Test Mfg');
    expect(component.form.value.country_of_origin).toBe('India');
  });

  // Test 3: On init with 404 — loading clears, profile stays null, no error surfaced
  it('on init with 404 — loading clears, profile is null, no error surfaced', async () => {
    const notFoundError = { status: 404, message: 'Not Found' };
    const showErrorSpy = vi.fn();

    await TestBed.configureTestingModule({
      imports: [
        ProfileEditComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
        {
          provide: ProfileApiService,
          useValue: {
            getProfile: vi.fn().mockReturnValue(throwError(() => notFoundError)),
            patchBaseProfile: vi.fn().mockReturnValue(of(mockProfile)),
            patchActiveCategories: vi.fn().mockReturnValue(of(mockProfile)),
            patchComplianceExtension: vi.fn().mockReturnValue(of(mockProfile)),
          },
        },
        {
          provide: ErrorService,
          useValue: { showError: showErrorSpy, showWarning: vi.fn(), showInfo: vi.fn(), showSuccess: vi.fn() },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ProfileEditComponent);
    const component = fixture.componentInstance;

    fixture.detectChanges();
    await fixture.whenStable();

    // 404 = first-time seller — show empty form, do NOT surface an error snackbar
    expect(showErrorSpy).not.toHaveBeenCalled();
    // loading clears so the form is rendered
    expect(component.loading()).toBe(false);
    // profile stays null
    expect(component.profile()).toBeNull();
    // form retains default empty values (country_of_origin defaults to 'India')
    expect(component.form.value.manufacturer_name).toBe('');
    expect(component.form.value.country_of_origin).toBe('India');
  });

  // Test 4: onSave() — calls patchBaseProfile() and navigates to /dashboard on success
  it('onSave() — calls patchBaseProfile() and navigates to /dashboard on success', async () => {
    const patchSpy = vi.fn().mockReturnValue(of(mockProfile));

    await TestBed.configureTestingModule({
      imports: [
        ProfileEditComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([{ path: 'dashboard', redirectTo: '' }]),
        {
          provide: ProfileApiService,
          useValue: {
            getProfile: vi.fn().mockReturnValue(of(mockProfile)),
            patchBaseProfile: patchSpy,
            patchActiveCategories: vi.fn().mockReturnValue(of(mockProfile)),
            patchComplianceExtension: vi.fn().mockReturnValue(of(mockProfile)),
          },
        },
        {
          provide: ErrorService,
          useValue: { showError: vi.fn(), showWarning: vi.fn(), showInfo: vi.fn(), showSuccess: vi.fn() },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ProfileEditComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();

    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);

    // Fill form with valid values so form.invalid is false
    component.form.setValue({
      manufacturer_name: 'Acme',
      manufacturer_address: '1 Road',
      manufacturer_pincode: '641001',
      packer_name: 'Pack Co',
      packer_address: '2 Road',
      packer_pincode: '641002',
      importer_name: null,
      importer_address: null,
      importer_pincode: null,
      country_of_origin: 'India',
    });

    component.onSave();

    expect(patchSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith('/dashboard');
    expect(component.saving()).toBe(false);
  });
});

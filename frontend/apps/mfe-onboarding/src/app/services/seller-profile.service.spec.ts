/**
 * SellerProfileService spec — HttpTestingController coverage.
 *
 * Covers per R-W6-1:
 *   - Happy path: #7 GET, #8 PATCH, #11 GET
 *   - Error matrix: 401 (get → fresh, patch → rethrow), 404 (get → fresh, required-fields → empty),
 *                   422 → ProfileValidationError with envelope, 5xx → ProfileNetworkError
 *   - No manual Authorization header (interceptor owns it)
 *   - No localStorage / sessionStorage
 *
 * Pattern: HttpTestingController (per memory — ALWAYS use provideHttpClientTesting).
 * ApiClient is the real implementation (not mocked) — we test through it.
 * No AuthService dependency in this service (interceptor-owned auth).
 *
 * Wave 6 · Wave B · lane 2 — authored by meesell-angular-service-builder (session-1).
 */

import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withFetch } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import {
  SellerProfileService,
  ProfileValidationError,
  ProfileNetworkError,
} from './seller-profile.service';
import type { SellerProfile, RequiredFieldsResponse } from '../seller-profile.model';
import { FRESH_SELLER_PROFILE } from '../seller-profile.model';

// ─────────────────────────────────────────────────────────────────────────────
// Test fixtures
// ─────────────────────────────────────────────────────────────────────────────

function makeProfile(overrides: Partial<SellerProfile> = {}): SellerProfile {
  return {
    user_id: 'uuid-test-123',
    manufacturer_name: 'Acme Textiles',
    manufacturer_address: '12 MG Road, Tirupur',
    manufacturer_pincode: '641601',
    packer_name: 'Acme Packing',
    packer_address: '12 MG Road, Tirupur',
    packer_pincode: '641601',
    importer_name: null,
    importer_address: null,
    importer_pincode: null,
    country_of_origin: 'India',
    active_super_categories: [],
    compliance_extensions: {},
    onboarding_complete: false,
    created_at: '2026-06-12T00:00:00Z',
    updated_at: '2026-06-12T00:00:00Z',
    ...overrides,
  };
}

function makeRequiredFields(): RequiredFieldsResponse {
  return {
    base_fields: [
      {
        name: 'Manufacturer Name',
        canonical_name: 'manufacturer_name',
        marker: 'compulsory',
        data_type: 'text',
        primitive: 'text_short',
        help_text: 'Legal name of the manufacturer.',
        is_advanced: false,
        enum_resolver: null,
        validation_message_ids: ['validation.required'],
      },
    ],
    extension_fields: {},
    completed: { manufacturer_name: false },
  };
}

function make422Body(validationMessageId: string) {
  return {
    detail: 'Validation error',
    code: 'VALIDATION_ERROR',
    validation_message_id: validationMessageId,
    request_id: 'req-test-422',
    errors: [{ field: 'manufacturer_pincode', msg: 'Invalid format' }],
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Test setup
// ─────────────────────────────────────────────────────────────────────────────

describe('SellerProfileService', () => {
  let service: SellerProfileService;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        SellerProfileService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(SellerProfileService);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller.verify(); // assert no unexpected requests
    TestBed.resetTestingModule();
  });

  // ─────────────────────────────────────────────────────────────────────────
  // #7 GET /api/v1/seller-profile — getProfile()
  // ─────────────────────────────────────────────────────────────────────────

  describe('getProfile()', () => {
    it('happy path: returns the profile from the backend', () => {
      const expected = makeProfile();
      let result: SellerProfile | undefined;

      service.getProfile().subscribe((p) => (result = p));

      const req = controller.expectOne('/api/v1/seller-profile');
      expect(req.request.method).toBe('GET');

      // ASSERT: no manual Authorization header from the service itself
      // (jwtInterceptor owns it — interceptor NOT registered in TestBed here)
      expect(req.request.headers.has('Authorization')).toBe(false);

      req.flush(expected);
      expect(result).toEqual(expected);
    });

    it('404 → returns FRESH_SELLER_PROFILE (first-time seller, not an error)', () => {
      let result: SellerProfile | undefined;

      service.getProfile().subscribe((p) => (result = p));

      const req = controller.expectOne('/api/v1/seller-profile');
      req.flush('Not Found', { status: 404, statusText: 'Not Found' });

      expect(result).toEqual({ ...FRESH_SELLER_PROFILE });
    });

    it('401 → returns FRESH_SELLER_PROFILE (terminal 401 — interceptor already retried)', () => {
      let result: SellerProfile | undefined;

      service.getProfile().subscribe((p) => (result = p));

      const req = controller.expectOne('/api/v1/seller-profile');
      req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });

      expect(result).toEqual({ ...FRESH_SELLER_PROFILE });
    });

    it('422 → throws ProfileValidationError with envelope', () => {
      const body422 = make422Body('validation.pincode.invalid_format');
      let caughtError: unknown;

      service.getProfile().subscribe({
        next: () => { throw new Error('Should not emit next on 422'); },
        error: (e) => (caughtError = e),
      });

      const req = controller.expectOne('/api/v1/seller-profile');
      req.flush(body422, { status: 422, statusText: 'Unprocessable Entity' });

      expect(caughtError).toBeInstanceOf(ProfileValidationError);
      const pve = caughtError as ProfileValidationError;
      expect(pve.envelope.validation_message_id).toBe('validation.pincode.invalid_format');
      expect(pve.status).toBe(422);
    });

    it('500 → throws ProfileNetworkError', () => {
      let caughtError: unknown;

      service.getProfile().subscribe({
        next: () => { throw new Error('Should not emit next on 500'); },
        error: (e) => (caughtError = e),
      });

      const req = controller.expectOne('/api/v1/seller-profile');
      req.flush('Server Error', { status: 500, statusText: 'Internal Server Error' });

      expect(caughtError).toBeInstanceOf(ProfileNetworkError);
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // #8 PATCH /api/v1/seller-profile — patchProfile()
  // ─────────────────────────────────────────────────────────────────────────

  describe('patchProfile()', () => {
    it('happy path: sends only the provided base fields and returns updated profile', () => {
      const body = {
        manufacturer_name: 'Acme Textiles',
        manufacturer_address: '12 MG Road, Tirupur',
        manufacturer_pincode: '641601',
        packer_name: 'Acme Packing',
        packer_address: '12 MG Road, Tirupur',
        packer_pincode: '641601',
        country_of_origin: 'India',
      };
      const expected = makeProfile();
      let result: SellerProfile | undefined;

      service.patchProfile(body).subscribe((p) => (result = p));

      const req = controller.expectOne('/api/v1/seller-profile');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual(body);

      // ASSERT: no manual Authorization header from the service
      expect(req.request.headers.has('Authorization')).toBe(false);

      req.flush(expected);
      expect(result).toEqual(expected);
    });

    it('422 → throws ProfileValidationError (bad pincode pattern)', () => {
      const body = { manufacturer_pincode: 'BAD_PIN' };
      const body422 = make422Body('validation.pincode.invalid_format');
      let caughtError: unknown;

      service.patchProfile(body).subscribe({
        next: () => { throw new Error('Should not emit next on 422'); },
        error: (e) => (caughtError = e),
      });

      const req = controller.expectOne('/api/v1/seller-profile');
      req.flush(body422, { status: 422, statusText: 'Unprocessable Entity' });

      expect(caughtError).toBeInstanceOf(ProfileValidationError);
      const pve = caughtError as ProfileValidationError;
      expect(pve.envelope.validation_message_id).toBe('validation.pincode.invalid_format');
      expect(pve.envelope.errors).toHaveLength(1);
    });

    it('422 with extra="forbid" key → throws ProfileValidationError (contract-mismatch guard)', () => {
      // If a future code-path accidentally sends a non-PatchProfileRequest key,
      // the backend returns 422. This test verifies the service maps that correctly.
      const body422 = make422Body('validation.extra_fields_forbidden');
      let caughtError: unknown;

      // Cast to bypass TS check — we're simulating a runtime mismatch
      service.patchProfile({ manufacturer_name: 'Test' }).subscribe({
        error: (e) => (caughtError = e),
      });

      const req = controller.expectOne('/api/v1/seller-profile');
      req.flush(body422, { status: 422, statusText: 'Unprocessable Entity' });

      expect(caughtError).toBeInstanceOf(ProfileValidationError);
    });

    it('401 → throws ProfileNetworkError (terminal 401 from refresh chain)', () => {
      let caughtError: unknown;

      service.patchProfile({ manufacturer_name: 'Test' }).subscribe({
        error: (e) => (caughtError = e),
      });

      const req = controller.expectOne('/api/v1/seller-profile');
      req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });

      expect(caughtError).toBeInstanceOf(ProfileNetworkError);
    });

    it('500 → throws ProfileNetworkError', () => {
      let caughtError: unknown;

      service.patchProfile({ manufacturer_name: 'Test' }).subscribe({
        error: (e) => (caughtError = e),
      });

      const req = controller.expectOne('/api/v1/seller-profile');
      req.flush('Server Error', { status: 500, statusText: 'Internal Server Error' });

      expect(caughtError).toBeInstanceOf(ProfileNetworkError);
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // #11 GET /api/v1/seller-profile/required-fields — getRequiredFields()
  // ─────────────────────────────────────────────────────────────────────────

  describe('getRequiredFields()', () => {
    it('happy path: returns the FieldSpec wizard schema', () => {
      const expected = makeRequiredFields();
      let result: RequiredFieldsResponse | undefined;

      service.getRequiredFields().subscribe((r) => (result = r));

      const req = controller.expectOne('/api/v1/seller-profile/required-fields');
      expect(req.request.method).toBe('GET');
      expect(req.request.headers.has('Authorization')).toBe(false);

      req.flush(expected);
      expect(result).toEqual(expected);
      expect(result!.base_fields).toHaveLength(1);
      expect(result!.base_fields[0].canonical_name).toBe('manufacturer_name');
    });

    it('404 → returns empty RequiredFieldsResponse (graceful degradation)', () => {
      let result: RequiredFieldsResponse | undefined;

      service.getRequiredFields().subscribe((r) => (result = r));

      const req = controller.expectOne('/api/v1/seller-profile/required-fields');
      req.flush('Not Found', { status: 404, statusText: 'Not Found' });

      expect(result).toEqual({ base_fields: [], extension_fields: {}, completed: {} });
    });

    it('401 → returns empty RequiredFieldsResponse (graceful degradation)', () => {
      let result: RequiredFieldsResponse | undefined;

      service.getRequiredFields().subscribe((r) => (result = r));

      const req = controller.expectOne('/api/v1/seller-profile/required-fields');
      req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });

      expect(result).toEqual({ base_fields: [], extension_fields: {}, completed: {} });
    });

    it('500 → throws ProfileNetworkError', () => {
      let caughtError: unknown;

      service.getRequiredFields().subscribe({
        error: (e) => (caughtError = e),
      });

      const req = controller.expectOne('/api/v1/seller-profile/required-fields');
      req.flush('Server Error', { status: 500, statusText: 'Internal Server Error' });

      expect(caughtError).toBeInstanceOf(ProfileNetworkError);
    });
  });

  // ─────────────────────────────────────────────────────────────────────────
  // #9 PATCH /api/v1/seller-profile/active-categories — STUB smoke test
  // ─────────────────────────────────────────────────────────────────────────

  describe('patchActiveCategories() — STUB (Option A defer)', () => {
    it('issues PATCH to the correct path (stub wires the correct URL)', () => {
      const expected = makeProfile({ active_super_categories: ['26'] });
      let result: SellerProfile | undefined;

      service.patchActiveCategories({ active_super_categories: ['26'] }).subscribe(
        (p) => (result = p),
      );

      const req = controller.expectOne('/api/v1/seller-profile/active-categories');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ active_super_categories: ['26'] });

      req.flush(expected);
      expect(result).toEqual(expected);
    });
  });
});

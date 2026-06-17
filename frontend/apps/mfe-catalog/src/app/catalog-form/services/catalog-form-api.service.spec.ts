/**
 * catalog-form-api.service.spec.ts — Wave 6 Wave C
 *
 * Contract-conformance tests for CatalogFormApiService.
 * Uses HttpTestingController via provideHttpClientTesting to intercept requests
 * and assert URL, method, headers, body, and error-matrix fallbacks.
 *
 * Spec §5.4 requirements:
 *   getSchema: URL, 200 success, 401 rethrow, 404→[], 5xx→[]
 *   getDraft:  URL, 200 success, 404→null, 5xx→null, 401 rethrow
 *   autosave:  URL, method=PATCH, X-Autosave header, body shape, 401/422/5xx rethrow
 *   autofill:  URL, method=POST, body {description}, 401/402/404/5xx rethrow
 *   getFieldEnum: URL, success, any error→[]
 *
 * ApiClient is route-scoped (@Injectable() — no providedIn).
 * ApiClient itself is providedIn:'root' and wraps HttpClient.
 * TestBed provides ApiClient via the DI tree and HttpClient via provideHttpClientTesting.
 *
 * Auth: jwtInterceptor is NOT in TestBed (Wave A frozen surface).
 *   Assert no Authorization header from this service (interceptor-free test environment).
 */

import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

import { ApiClient } from '@mesell/core';
import { CatalogFormApiService } from './catalog-form-api.service';
import type {
  SchemaResponseDTO,
  ProductDraftResponse,
  ProductResponse,
  AutofillResponse,
  FieldEnumResponseDTO,
  SchemaFieldDTO,
} from './catalog-form-api.service';

// ── Fixtures ───────────────────────────────────────────────────────────────────

const CATEGORY_ID  = 'cat-uuid-001';
const PRODUCT_ID   = 'prod-uuid-001';
const FIELD_NAME   = 'brand';

/** Minimal SchemaFieldDTO for fixtures. */
function makeFieldDTO(overrides: Partial<SchemaFieldDTO> & { canonical_name: string }): SchemaFieldDTO {
  return {
    name:          overrides.canonical_name.replace(/_/g, ' '),
    data_type:     'text',
    primitive:     'text_short',
    is_advanced:   false,
    marker:        'optional',
    ...overrides,
  };
}

const SCHEMA_DTO: SchemaResponseDTO = {
  fields: [
    makeFieldDTO({ canonical_name: 'product_title', marker: 'compulsory', primitive: 'text_short' }),
    makeFieldDTO({ canonical_name: 'color', marker: 'optional', primitive: 'dropdown_small', enum_resolver: 'static', enum_values: ['Blue', 'Red'] }),
    makeFieldDTO({ canonical_name: 'hero_image', marker: 'compulsory', primitive: 'image_upload' }),
  ],
  compulsory_count: 2,
  optional_count: 1,
  total_count: 3,
  wizard_step_count: 1,
  main_sheet_label: 'Main Sheet',
  compliance_shape: 'standard',
};

const PRODUCT_RESPONSE: ProductResponse = {
  id: PRODUCT_ID,
  catalog_id: 'cat-001',
  category_id: CATEGORY_ID,
  name: 'Blue Kurti',
  status: 'draft',
  fields: { product_title: 'Blue Kurti' },
  ai_suggestions: {},
  created_at: '2026-06-12T00:00:00Z',
  updated_at: '2026-06-12T01:00:00Z',
};

const DRAFT_RESPONSE: ProductDraftResponse = {
  fields: { product_title: 'Saved Kurti' },
  last_updated: '2026-06-12T00:30:00Z',
  autosave_count: 3,
};

const AUTOFILL_RESPONSE: AutofillResponse = {
  suggestions: {
    product_title: { value: 'AI Blue Kurti', confidence: 0.95, source: 'ai' },
    color:         { value: 'Blue',          confidence: 0.90, source: 'ai' },
  },
  applied: { product_title: false, color: false },
  fallback_offered: false,
};

const FIELD_ENUM_RESPONSE: FieldEnumResponseDTO = {
  enum_entries: [
    { canonical: 'cotton', meesho: 'Cotton', labels: ['Cotton'] },
    { canonical: 'polyester', meesho: 'Polyester', labels: ['Polyester'] },
  ],
  total: 2,
  truncated: false,
};

// ── Test harness ───────────────────────────────────────────────────────────────

describe('CatalogFormApiService', () => {
  let svc: CatalogFormApiService;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        ApiClient,
        CatalogFormApiService,
      ],
    });
    svc        = TestBed.inject(CatalogFormApiService);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller.verify();
  });

  // ── getSchema ──────────────────────────────────────────────────────────────

  describe('getSchema()', () => {
    it('GET /api/v1/categories/{id}/schema — URL and method', () => {
      svc.getSchema(CATEGORY_ID).subscribe();
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/schema`);
      expect(req.request.method).toBe('GET');
      req.flush(SCHEMA_DTO);
    });

    it('does NOT send Authorization header (jwtInterceptor owns it)', () => {
      svc.getSchema(CATEGORY_ID).subscribe();
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/schema`);
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush(SCHEMA_DTO);
    });

    it('200 success → adapts flat fields to FieldGroup[] (3 groups)', () => {
      let result: unknown;
      svc.getSchema(CATEGORY_ID).subscribe(groups => (result = groups));
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/schema`);
      req.flush(SCHEMA_DTO);
      // Should have 3 groups
      expect(Array.isArray(result)).toBe(true);
      expect((result as unknown[]).length).toBe(3);
    });

    it('200 → image_upload field excluded from adapted groups', () => {
      let groups: unknown[] = [];
      svc.getSchema(CATEGORY_ID).subscribe(g => (groups = g));
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/schema`);
      req.flush(SCHEMA_DTO);
      const allFields = (groups as Array<{ fields: Array<{ canonical_name: string }> }>)
        .flatMap(g => g.fields);
      expect(allFields.find(f => f.canonical_name === 'hero_image')).toBeUndefined();
    });

    it('404 → of([]) (schema not found OR feature flag OFF)', () => {
      let result: unknown = 'NOT SET';
      svc.getSchema(CATEGORY_ID).subscribe(g => (result = g));
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/schema`);
      req.flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
      expect(result).toEqual([]);
    });

    it('500 → of([])', () => {
      let result: unknown = 'NOT SET';
      svc.getSchema(CATEGORY_ID).subscribe(g => (result = g));
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/schema`);
      req.flush({ detail: 'Server error' }, { status: 500, statusText: 'Server Error' });
      expect(result).toEqual([]);
    });

    it('401 → rethrow (errorCalled=true)', () => {
      let errorCalled = false;
      svc.getSchema(CATEGORY_ID).subscribe({
        next: () => undefined,
        error: () => (errorCalled = true),
      });
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/schema`);
      req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
      expect(errorCalled).toBe(true);
    });
  });

  // ── getDraft ───────────────────────────────────────────────────────────────

  describe('getDraft()', () => {
    it('GET /api/v1/products/{id}/draft — URL and method', () => {
      svc.getDraft(PRODUCT_ID).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/draft`);
      expect(req.request.method).toBe('GET');
      req.flush(DRAFT_RESPONSE);
    });

    it('200 success → emits ProductDraftResponse', () => {
      let result: unknown;
      svc.getDraft(PRODUCT_ID).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/draft`);
      req.flush(DRAFT_RESPONSE);
      expect(result).toEqual(DRAFT_RESPONSE);
    });

    it('404 → of(null) — feature flag OFF or product not found', () => {
      let result: unknown = 'NOT SET';
      svc.getDraft(PRODUCT_ID).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/draft`);
      req.flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
      expect(result).toBeNull();
    });

    it('500 → of(null) — non-fatal for draft recovery', () => {
      let result: unknown = 'NOT SET';
      svc.getDraft(PRODUCT_ID).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/draft`);
      req.flush({ detail: 'Server error' }, { status: 500, statusText: 'Server Error' });
      expect(result).toBeNull();
    });

    it('401 → rethrow (component handles terminal auth failure)', () => {
      let errorCalled = false;
      svc.getDraft(PRODUCT_ID).subscribe({
        next: () => undefined,
        error: () => (errorCalled = true),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/draft`);
      req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
      expect(errorCalled).toBe(true);
    });
  });

  // ── autosave ───────────────────────────────────────────────────────────────

  describe('autosave()', () => {
    const FIELDS = { product_title: 'Blue Kurti', color: 'Blue' };

    it('PATCH /api/v1/products/{id} — URL and method', () => {
      svc.autosave(PRODUCT_ID, FIELDS).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      expect(req.request.method).toBe('PATCH');
      req.flush(PRODUCT_RESPONSE);
    });

    it('sends X-Autosave: true header', () => {
      svc.autosave(PRODUCT_ID, FIELDS).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      expect(req.request.headers.get('X-Autosave')).toBe('true');
      req.flush(PRODUCT_RESPONSE);
    });

    it('request body contains {fields} (PatchProductRequest shape)', () => {
      svc.autosave(PRODUCT_ID, FIELDS).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      expect(req.request.body).toEqual({ fields: FIELDS });
      req.flush(PRODUCT_RESPONSE);
    });

    it('does NOT send Authorization header (jwtInterceptor owns it)', () => {
      svc.autosave(PRODUCT_ID, FIELDS).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush(PRODUCT_RESPONSE);
    });

    it('200 success → emits ProductResponse', () => {
      let result: unknown;
      svc.autosave(PRODUCT_ID, FIELDS).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      req.flush(PRODUCT_RESPONSE);
      expect(result).toEqual(PRODUCT_RESPONSE);
    });

    it('401 → rethrow (component sets saveStatus=error)', () => {
      let errorCalled = false;
      svc.autosave(PRODUCT_ID, FIELDS).subscribe({
        next: () => undefined,
        error: () => (errorCalled = true),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
      expect(errorCalled).toBe(true);
    });

    it('422 → rethrow (component surfaces field-level errors; user input preserved)', () => {
      let errorCalled = false;
      svc.autosave(PRODUCT_ID, FIELDS).subscribe({
        next: () => undefined,
        error: () => (errorCalled = true),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      req.flush({ detail: 'Validation failed', errors: { color: 'Invalid value' } }, { status: 422, statusText: 'Unprocessable Entity' });
      expect(errorCalled).toBe(true);
    });

    it('500 → rethrow (component shows autosave failure)', () => {
      let errorCalled = false;
      svc.autosave(PRODUCT_ID, FIELDS).subscribe({
        next: () => undefined,
        error: () => (errorCalled = true),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      req.flush({ detail: 'Server error' }, { status: 500, statusText: 'Server Error' });
      expect(errorCalled).toBe(true);
    });
  });

  // ── autofill ───────────────────────────────────────────────────────────────

  describe('autofill()', () => {
    const DESCRIPTION = 'A beautiful blue cotton kurti with mirror work.';

    it('POST /api/v1/products/{id}/autofill — URL and method', () => {
      svc.autofill(PRODUCT_ID, DESCRIPTION).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/autofill`);
      expect(req.request.method).toBe('POST');
      req.flush(AUTOFILL_RESPONSE);
    });

    it('request body contains {description} (AutofillRequest shape)', () => {
      svc.autofill(PRODUCT_ID, DESCRIPTION).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/autofill`);
      expect(req.request.body).toEqual({ description: DESCRIPTION });
      req.flush(AUTOFILL_RESPONSE);
    });

    it('200 success → emits AutofillResponse with suggestions map', () => {
      let result: AutofillResponse | undefined;
      svc.autofill(PRODUCT_ID, DESCRIPTION).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/autofill`);
      req.flush(AUTOFILL_RESPONSE);
      expect(result?.suggestions['product_title'].value).toBe('AI Blue Kurti');
      expect(result?.suggestions['product_title'].confidence).toBe(0.95);
      expect(result?.suggestions['product_title'].source).toBe('ai');
      expect(result?.fallback_offered).toBe(false);
    });

    it('401 → rethrow', () => {
      let errorStatus = 0;
      svc.autofill(PRODUCT_ID, DESCRIPTION).subscribe({
        next: () => undefined,
        error: (e: { status: number }) => (errorStatus = e.status),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/autofill`);
      req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
      expect(errorStatus).toBe(401);
    });

    it('402 → rethrow status=402 (plan guard — component shows quota toast)', () => {
      let errorStatus = 0;
      svc.autofill(PRODUCT_ID, DESCRIPTION).subscribe({
        next: () => undefined,
        error: (e: { status: number }) => (errorStatus = e.status),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/autofill`);
      req.flush({ detail: 'Quota exceeded' }, { status: 402, statusText: 'Payment Required' });
      expect(errorStatus).toBe(402);
    });

    it('404 → rethrow status=404 (FEATURE_AI_AUTOFILL_ENABLED=false — component disables button)', () => {
      let errorStatus = 0;
      svc.autofill(PRODUCT_ID, DESCRIPTION).subscribe({
        next: () => undefined,
        error: (e: { status: number }) => (errorStatus = e.status),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/autofill`);
      req.flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
      expect(errorStatus).toBe(404);
    });

    it('500 → rethrow (component shows retry toast)', () => {
      let errorCalled = false;
      svc.autofill(PRODUCT_ID, DESCRIPTION).subscribe({
        next: () => undefined,
        error: () => (errorCalled = true),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/autofill`);
      req.flush({ detail: 'Server error' }, { status: 500, statusText: 'Server Error' });
      expect(errorCalled).toBe(true);
    });
  });

  // ── getFieldEnum ───────────────────────────────────────────────────────────

  describe('getFieldEnum()', () => {
    it('GET /api/v1/categories/{id}/field-enum/{name} — URL and method', () => {
      svc.getFieldEnum(CATEGORY_ID, FIELD_NAME).subscribe();
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/field-enum/${FIELD_NAME}`);
      expect(req.request.method).toBe('GET');
      req.flush(FIELD_ENUM_RESPONSE);
    });

    it('200 success → emits EnumEntryDTO[]', () => {
      let result: unknown;
      svc.getFieldEnum(CATEGORY_ID, FIELD_NAME).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/field-enum/${FIELD_NAME}`);
      req.flush(FIELD_ENUM_RESPONSE);
      expect(Array.isArray(result)).toBe(true);
      expect((result as unknown[]).length).toBe(2);
    });

    it('200 → extracts enum_entries from response envelope', () => {
      let result: Array<{ canonical: string }> = [];
      svc.getFieldEnum(CATEGORY_ID, FIELD_NAME).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/field-enum/${FIELD_NAME}`);
      req.flush(FIELD_ENUM_RESPONSE);
      expect(result[0].canonical).toBe('cotton');
      expect(result[1].canonical).toBe('polyester');
    });

    it('404 → of([]) (graceful — field-enum not available)', () => {
      let result: unknown = 'NOT SET';
      svc.getFieldEnum(CATEGORY_ID, FIELD_NAME).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/field-enum/${FIELD_NAME}`);
      req.flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
      expect(result).toEqual([]);
    });

    it('500 → of([]) (graceful — dropdown shows empty)', () => {
      let result: unknown = 'NOT SET';
      svc.getFieldEnum(CATEGORY_ID, FIELD_NAME).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/field-enum/${FIELD_NAME}`);
      req.flush({ detail: 'Server error' }, { status: 500, statusText: 'Server Error' });
      expect(result).toEqual([]);
    });

    it('401 → of([]) (graceful — all errors are caught)', () => {
      let result: unknown = 'NOT SET';
      svc.getFieldEnum(CATEGORY_ID, FIELD_NAME).subscribe(r => (result = r));
      const req = controller.expectOne(`/api/v1/categories/${CATEGORY_ID}/field-enum/${FIELD_NAME}`);
      req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
      expect(result).toEqual([]);
    });
  });
});

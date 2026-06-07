// features/catalog-form/catalog-form-api.service.spec.ts
// 4 required tests per dispatch spec:
//   1. getProduct — calls correct URL
//   2. saveProduct — calls correct URL with NO X-Autosave header
//   3. autosaveProduct — calls correct URL WITH X-Autosave: true header
//   4. requestAutofill — calls correct URL with retryOn503

import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import {
  CatalogFormApiService,
  ProductDetail,
  AutofillResponse,
} from './catalog-form-api.service';

const MOCK_PRODUCT: ProductDetail = {
  id: 'prod-001',
  leafCategoryId: 'cat-leaf-1',
  leafCategoryName: 'Kurti',
  superCategoryId: 'cat-super-1',
  status: 'draft',
  fields: { color: 'blue', size: 'M' },
  aiSuggestions: {},
  createdAt: '2026-06-06T00:00:00Z',
  updatedAt: '2026-06-06T00:00:00Z',
};

const MOCK_AUTOFILL: AutofillResponse = {
  suggestions: { color: { suggested_value: 'red', confidence: 0.9 } },
  fieldsFilled: 1,
  fallbackOffered: false,
};

describe('CatalogFormApiService', () => {
  let service: CatalogFormApiService;
  let apiClient: { get: ReturnType<typeof vi.fn>; patch: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    apiClient = {
      get: vi.fn(() => of(MOCK_PRODUCT)),
      patch: vi.fn(() => of(MOCK_PRODUCT)),
      post: vi.fn(() => of(MOCK_AUTOFILL)),
    };

    TestBed.configureTestingModule({
      providers: [
        CatalogFormApiService,
        { provide: ApiClient, useValue: apiClient },
      ],
    });

    service = TestBed.inject(CatalogFormApiService);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('getProduct — calls GET /products/:id with no extra headers', () => {
    let result: ProductDetail | undefined;
    service.getProduct('prod-001').subscribe(p => (result = p));

    expect(apiClient.get).toHaveBeenCalledOnce();
    expect(apiClient.get).toHaveBeenCalledWith('/products/prod-001');
    expect(result).toEqual(MOCK_PRODUCT);
  });

  it('saveProduct — calls PATCH /products/:id with NO X-Autosave header', () => {
    const fields = { color: 'green' };
    let result: ProductDetail | undefined;
    service.saveProduct('prod-001', fields).subscribe(p => (result = p));

    expect(apiClient.patch).toHaveBeenCalledOnce();
    const [path, body, options] = apiClient.patch.mock.calls[0] as [string, unknown, unknown];
    expect(path).toBe('/products/prod-001');
    expect(body).toEqual({ fields });
    // saveProduct must NOT send X-Autosave header
    expect(options).toBeUndefined();
    expect(result).toEqual(MOCK_PRODUCT);
  });

  it('autosaveProduct — calls PATCH /products/:id WITH X-Autosave: true header', () => {
    const fields = { color: 'yellow' };
    let result: ProductDetail | undefined;
    service.autosaveProduct('prod-001', fields).subscribe(p => (result = p));

    expect(apiClient.patch).toHaveBeenCalledOnce();
    const [path, body, options] = apiClient.patch.mock.calls[0] as [
      string,
      unknown,
      { headers: Record<string, string> },
    ];
    expect(path).toBe('/products/prod-001');
    expect(body).toEqual({ fields });
    // CRITICAL: X-Autosave: true header must be present (string, not boolean)
    expect(options?.headers?.['X-Autosave']).toBe('true');
    expect(result).toEqual(MOCK_PRODUCT);
  });

  it('requestAutofill — calls POST /products/:id/autofill with retryOn503: true', () => {
    let result: AutofillResponse | undefined;
    service.requestAutofill('prod-001').subscribe(r => (result = r));

    expect(apiClient.post).toHaveBeenCalledOnce();
    const [path, body, options] = apiClient.post.mock.calls[0] as [
      string,
      unknown,
      { retryOn503: boolean },
    ];
    expect(path).toBe('/products/prod-001/autofill');
    expect(body).toEqual({});
    expect(options?.retryOn503).toBe(true);
    expect(result).toEqual(MOCK_AUTOFILL);
  });
});

// features/catalog-form/draft-recovery.service.spec.ts
// 3 required tests:
//   1. 200 response — returns ProductDraft
//   2. 204 response (null body) — returns null without error
//   3. 404 propagates as error

import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import { ApiError } from '@core/api/api-error';
import { DraftRecoveryService, ProductDraft } from './draft-recovery.service';

const MOCK_DRAFT: ProductDraft = {
  fields: { color: 'blue', fabric: 'cotton' },
  lastUpdated: '2026-06-06T10:30:00Z',
  autosaveCount: 7,
};

describe('DraftRecoveryService', () => {
  let service: DraftRecoveryService;
  let apiClient: { get: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    apiClient = {
      get: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        DraftRecoveryService,
        { provide: ApiClient, useValue: apiClient },
      ],
    });

    service = TestBed.inject(DraftRecoveryService);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('200 response — returns ProductDraft when a draft exists', () => {
    apiClient.get.mockReturnValue(of(MOCK_DRAFT));

    let result: ProductDraft | null | undefined;
    service.getDraft('prod-001').subscribe(d => (result = d));

    expect(apiClient.get).toHaveBeenCalledWith('/products/prod-001/draft');
    expect(result).toEqual(MOCK_DRAFT);
  });

  it('204 response (null body) — returns null without throwing', () => {
    // Angular HttpClient emits null body for a 204 response
    apiClient.get.mockReturnValue(of(null));

    let result: ProductDraft | null | undefined;
    let errorThrown = false;
    service.getDraft('prod-001').subscribe({
      next: d => (result = d),
      error: () => (errorThrown = true),
    });

    expect(errorThrown).toBe(false);
    expect(result).toBeNull();
  });

  it('404 response — propagates ApiError as error (product not found)', () => {
    const notFoundError = new ApiError({
      kind: 'http',
      status: 404,
      code: 'catalog.product_not_found',
      displayMessage: 'Product not found.',
    });
    apiClient.get.mockReturnValue(throwError(() => notFoundError));

    let caughtError: unknown;
    service.getDraft('prod-404').subscribe({
      error: (err: unknown) => (caughtError = err),
    });

    expect(caughtError).toBeInstanceOf(ApiError);
    expect((caughtError as ApiError).status).toBe(404);
  });
});

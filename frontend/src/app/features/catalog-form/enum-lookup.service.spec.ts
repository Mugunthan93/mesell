// features/catalog-form/enum-lookup.service.spec.ts
// 2 required tests:
//   1. Correct URL with categoryId + fieldName
//   2. query params (q, limit) included in request options

import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import { EnumLookupService, EnumValue } from './enum-lookup.service';

const MOCK_RESPONSE = {
  field_name: 'fabric_type',
  values: [
    { code: 'CTN', label: 'Cotton' },
    { code: 'SLK', label: 'Silk' },
  ],
};

const EXPECTED_VALUES: EnumValue[] = [
  { code: 'CTN', label: 'Cotton' },
  { code: 'SLK', label: 'Silk' },
];

describe('EnumLookupService', () => {
  let service: EnumLookupService;
  let apiClient: { get: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    apiClient = {
      get: vi.fn(() => of(MOCK_RESPONSE)),
    };

    TestBed.configureTestingModule({
      providers: [
        EnumLookupService,
        { provide: ApiClient, useValue: apiClient },
      ],
    });

    service = TestBed.inject(EnumLookupService);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('constructs URL with correct categoryId and fieldName path segments', () => {
    let result: EnumValue[] | undefined;
    service.lookupEnum('cat-leaf-1', 'fabric_type', 'cotton').subscribe(v => (result = v));

    expect(apiClient.get).toHaveBeenCalledOnce();
    const [path] = apiClient.get.mock.calls[0] as [string, unknown];
    expect(path).toBe('/categories/cat-leaf-1/enum/fabric_type');
    expect(result).toEqual(EXPECTED_VALUES);
  });

  it('includes q and limit query params; limit defaults to 20', () => {
    service.lookupEnum('cat-leaf-1', 'fabric_type', 'cot').subscribe();

    const [, options] = apiClient.get.mock.calls[0] as [
      string,
      { params: Record<string, string | number> },
    ];
    expect(options?.params?.['q']).toBe('cot');
    expect(options?.params?.['limit']).toBe(20);
  });

  it('respects a custom limit when provided', () => {
    service.lookupEnum('cat-leaf-1', 'fabric_type', 'silk', 5).subscribe();

    const [, options] = apiClient.get.mock.calls[0] as [
      string,
      { params: Record<string, string | number> },
    ];
    expect(options?.params?.['limit']).toBe(5);
  });
});

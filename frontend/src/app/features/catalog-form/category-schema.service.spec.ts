// features/catalog-form/category-schema.service.spec.ts
// 2 required tests:
//   1. Correct URL constructed with categoryId
//   2. locale param included in the request options

import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import { CategorySchemaService, CategorySchemaFull } from './category-schema.service';

const MOCK_SCHEMA: CategorySchemaFull = {
  categoryId: 'cat-leaf-1',
  categoryName: 'Kurti',
  fields: [
    {
      canonicalName: 'color',
      dataType: 'text',
      primitive: 'text_short',
      marker: 'compulsory',
      isAdvanced: false,
      isHidden: false,
      stepId: 'basics',
      maxLength: 50,
      minLength: null,
      regex: null,
      minValue: null,
      maxValue: null,
      unitSuffix: null,
      displayLabel: { en: 'Color' },
      displayHelp: null,
      displayPlaceholder: null,
      displayUnitLabel: null,
      validationMessage: null,
      helpUrl: null,
    },
  ],
};

describe('CategorySchemaService', () => {
  let service: CategorySchemaService;
  let apiClient: { get: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    apiClient = {
      get: vi.fn(() => of(MOCK_SCHEMA)),
    };

    TestBed.configureTestingModule({
      providers: [
        CategorySchemaService,
        { provide: ApiClient, useValue: apiClient },
      ],
    });

    service = TestBed.inject(CategorySchemaService);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('constructs the correct URL using categoryId', () => {
    let result: CategorySchemaFull | undefined;
    service.getSchema('cat-leaf-1').subscribe(s => (result = s));

    expect(apiClient.get).toHaveBeenCalledOnce();
    const [path] = apiClient.get.mock.calls[0] as [string, unknown];
    expect(path).toBe('/categories/cat-leaf-1/schema');
    expect(result).toEqual(MOCK_SCHEMA);
  });

  it('includes locale param in request options (defaults to "en")', () => {
    service.getSchema('cat-leaf-1').subscribe();
    const [, options] = apiClient.get.mock.calls[0] as [string, { params: Record<string, string> }];
    expect(options?.params?.['locale']).toBe('en');
  });

  it('passes custom locale when provided', () => {
    service.getSchema('cat-leaf-1', 'ta').subscribe();
    const [, options] = apiClient.get.mock.calls[0] as [string, { params: Record<string, string> }];
    expect(options?.params?.['locale']).toBe('ta');
  });
});

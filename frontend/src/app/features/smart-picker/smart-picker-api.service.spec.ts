// features/smart-picker/smart-picker-api.service.spec.ts
// Tests all 4 API methods for correct path + HTTP verb per AC-10
// Pattern: Vitest + Angular TestBed (zoneless) + HttpTestingController

import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

import { SmartPickerApiService } from './smart-picker-api.service';
import { ApiClient } from '@core/api/api-client.service';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';

const BASE_URL = 'https://test.api';

describe('SmartPickerApiService', () => {
  let service: SmartPickerApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideExperimentalZonelessChangeDetection(),
        { provide: API_BASE_URL, useValue: BASE_URL },
        ApiClient,
        SmartPickerApiService,
      ],
    });
    service = TestBed.inject(SmartPickerApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('suggest() POSTs to /categories/suggest with description in body', () => {
    const mockResponse = {
      suggestions: [
        {
          super_category: 'Clothing',
          leaf_category: 'Kurti',
          leaf_category_id: 'uuid-1',
          confidence: 0.92,
          sample_attributes: [{ canonical_name: 'color', display_label: 'Color' }],
        },
      ],
      fallback_offered: false,
    };

    let result: unknown;
    service.suggest('Women kurta floral').subscribe((r) => (result = r));

    const req = httpMock.expectOne(`${BASE_URL}/categories/suggest`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ description: 'Women kurta floral' });

    req.flush(mockResponse);
    expect(result).toEqual(mockResponse);
  });

  it('getSuperCategories() GETs /categories', () => {
    const mockResponse = {
      categories: [{ id: 'sc-1', name: 'Clothing', leaf_count: 120 }],
    };

    let result: unknown;
    service.getSuperCategories().subscribe((r) => (result = r));

    const req = httpMock.expectOne(`${BASE_URL}/categories`);
    expect(req.request.method).toBe('GET');

    req.flush(mockResponse);
    expect(result).toEqual(mockResponse);
  });

  it('searchLeaves() GETs /categories/:id/leaves with search + limit params', () => {
    const mockResponse = {
      leaves: [{ id: 'leaf-1', name: 'Kurti', full_path: 'Clothing > Women > Kurti' }],
    };

    let result: unknown;
    service.searchLeaves('sc-1', 'kurti').subscribe((r) => (result = r));

    const req = httpMock.expectOne(
      (r) => r.url === `${BASE_URL}/categories/sc-1/leaves`,
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('search')).toBe('kurti');
    expect(req.request.params.get('limit')).toBe('20');

    req.flush(mockResponse);
    expect(result).toEqual(mockResponse);
  });

  it('createProduct() POSTs to /products with leaf_category_id in body', () => {
    const mockResponse = {
      id: 'prod-123',
      leaf_category_id: 'leaf-1',
      status: 'draft' as const,
      created_at: '2026-06-06T00:00:00Z',
    };

    let result: unknown;
    service.createProduct('leaf-1').subscribe((r) => (result = r));

    const req = httpMock.expectOne(`${BASE_URL}/products`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ leaf_category_id: 'leaf-1' });

    req.flush(mockResponse);
    expect(result).toEqual(mockResponse);
  });
});

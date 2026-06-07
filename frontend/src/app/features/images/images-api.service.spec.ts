// features/images/images-api.service.spec.ts
// 3 required tests:
//   1. uploadImage builds correct FormData fields (slot_index + image)
//   2. pollImages calls correct GET path
//   3. deleteImage uses DELETE verb via apiClient.delete

import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ApiClient } from '@core/api/api-client.service';
import { ImagesApiService, ProductImage } from './images-api.service';

const MOCK_IMAGE: ProductImage = {
  id: 'img-001',
  product_id: 'prod-001',
  slot_index: 0,
  status: 'pending',
  gcs_url: null,
  precheck_jsonb: null,
  uploaded_at: '2026-06-07T00:00:00Z',
};

describe('ImagesApiService', () => {
  let service: ImagesApiService;
  let apiClient: {
    postMultipart: ReturnType<typeof vi.fn>;
    get: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    apiClient = {
      postMultipart: vi.fn(() => of(MOCK_IMAGE)),
      get: vi.fn(() => of({ images: [MOCK_IMAGE] })),
      delete: vi.fn(() => of(undefined)),
    };

    TestBed.configureTestingModule({
      providers: [
        ImagesApiService,
        { provide: ApiClient, useValue: apiClient },
      ],
    });

    service = TestBed.inject(ImagesApiService);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  // Test 1: uploadImage builds FormData with correct fields
  it('uploadImage — builds FormData with slot_index and image fields and retryOn503', () => {
    const blob = new Blob(['fake-image-data'], { type: 'image/jpeg' });
    service.uploadImage('prod-001', 0, blob).subscribe();

    expect(apiClient.postMultipart).toHaveBeenCalledOnce();
    const [path, formData, options] = apiClient.postMultipart.mock.calls[0] as [string, FormData, { retryOn503: boolean }];
    expect(path).toBe('/products/prod-001/images');
    expect(formData instanceof FormData).toBe(true);
    expect((formData as FormData).get('slot_index')).toBe('0');
    // 'image' field should be the blob (FormData stores Blobs; File extends Blob)
    const imageField = (formData as FormData).get('image');
    expect(imageField instanceof Blob).toBe(true);
    expect(options?.retryOn503).toBe(true);
  });

  // Test 2: pollImages calls correct GET path and maps to images array
  it('pollImages — calls GET /products/:id/images and maps response to images array', () => {
    vi.useFakeTimers();

    let emittedImages: ProductImage[] | undefined;
    const sub = service.pollImages('prod-001').subscribe(images => {
      emittedImages = images;
    });

    // Advance 2001ms to trigger the first interval tick
    vi.advanceTimersByTime(2001);

    expect(apiClient.get).toHaveBeenCalledWith('/products/prod-001/images');
    expect(emittedImages).toEqual([MOCK_IMAGE]);

    sub.unsubscribe();
  });

  // Test 3: deleteImage uses DELETE verb via apiClient.delete
  it('deleteImage — calls apiClient.delete with correct path', () => {
    service.deleteImage('prod-001', 'img-001').subscribe();
    expect(apiClient.delete).toHaveBeenCalledWith('/products/prod-001/images/img-001');
  });
});

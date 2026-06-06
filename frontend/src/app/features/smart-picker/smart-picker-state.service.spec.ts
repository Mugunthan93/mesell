// features/smart-picker/smart-picker-state.service.spec.ts
// Tests per AC-10: (a) suggest sets loading true then false, (b) 422 error propagated not swallowed
// Pattern: Vitest + Angular TestBed (zoneless) + vi.fn() mocks

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { of, throwError } from 'rxjs';

import { SmartPickerStateService } from './smart-picker-state.service';
import { SmartPickerApiService } from './smart-picker-api.service';
import type { SuggestResponse } from './smart-picker.model';

const MOCK_SUGGESTION: SuggestResponse = {
  suggestions: [
    {
      super_category: 'Clothing',
      leaf_category: 'Kurti',
      leaf_category_id: 'leaf-uuid-1',
      confidence: 0.92,
      sample_attributes: [{ canonical_name: 'color', display_label: 'Color' }],
    },
  ],
  fallback_offered: false,
};

describe('SmartPickerStateService', () => {
  let service: SmartPickerStateService;
  let suggestSpy: ReturnType<typeof vi.fn>;
  let createProductSpy: ReturnType<typeof vi.fn>;

  afterEach(() => {
    vi.useRealTimers();
  });

  beforeEach(() => {
    suggestSpy = vi.fn();
    createProductSpy = vi.fn();

    TestBed.configureTestingModule({
      providers: [
        provideExperimentalZonelessChangeDetection(),
        SmartPickerStateService,
        {
          provide: SmartPickerApiService,
          useValue: {
            suggest: suggestSpy,
            getSuperCategories: vi.fn(() => of({ categories: [] })),
            searchLeaves: vi.fn(() => of({ leaves: [] })),
            createProduct: createProductSpy,
          },
        },
      ],
    });
    service = TestBed.inject(SmartPickerStateService);
  });

  // ── Test (a): suggest sets loading=true then false ──

  it('sets loading=true when suggest fires then loading=false on success', async () => {
    vi.useFakeTimers();

    // Return a delayed observable to verify loading state transitions
    suggestSpy.mockReturnValue(of(MOCK_SUGGESTION));

    // loading starts false
    expect(service.loading()).toBe(false);

    // Trigger suggest — the debounce (500ms) must advance before the call fires
    service.suggest('Women cotton kurti floral print');

    // Before debounce fires: loading is still false (not yet triggered)
    vi.advanceTimersByTime(300);
    expect(service.loading()).toBe(false);

    // After 500ms: debounce fires, loading goes true then immediately false
    // (synchronous observable from mock)
    vi.advanceTimersByTime(200); // total = 500ms

    // After synchronous observable completes, loading is false
    expect(service.loading()).toBe(false);

    // Suggestions have been set
    expect(service.suggestions$.getValue()).toHaveLength(1);
    expect(service.suggestions$.getValue()[0].leaf_category).toBe('Kurti');
  });

  it('sets loading=false and rateLimitHit=true on 429 error', async () => {
    vi.useFakeTimers();

    const rateLimitError = { status: 429, displayMessage: 'Rate limit exceeded' };
    suggestSpy.mockReturnValue(throwError(() => rateLimitError));

    service.suggest('Women cotton kurti floral print');
    vi.advanceTimersByTime(500);

    expect(service.loading()).toBe(false);
    expect(service.rateLimitHit()).toBe(true);
    expect(service.showBrowseFallback()).toBe(true);
  });

  // ── Test (b): 422 error propagated not swallowed ──

  it('selectCategory propagates 422 profile-incomplete error to caller', async () => {
    const profileError = {
      status: 422,
      raw: {
        error: {
          detail: 'customer.profile_incomplete_for_category',
          missing_super_category: 'sc-1',
          missing_super_name: 'Clothing',
          missing_compliance_fields: ['brand_declaration_id'],
          profile_url: '/profile?category=sc-1',
        },
      },
    };

    createProductSpy.mockReturnValue(throwError(() => profileError));

    let caughtError: unknown;

    service
      .selectCategory({
        super_category: 'Clothing',
        leaf_category: 'Kurti',
        leaf_category_id: 'leaf-1',
        confidence: 0.9,
        sample_attributes: [],
      })
      .subscribe({
        error: (err) => {
          caughtError = err;
        },
      });

    // Error must reach the subscriber — not swallowed
    expect(caughtError).toBeDefined();
    expect((caughtError as { status?: number })?.status).toBe(422);
  });

  it('selectCategory maps 201 response to {productId}', () => {
    createProductSpy.mockReturnValue(
      of({
        id: 'prod-abc',
        leaf_category_id: 'leaf-1',
        status: 'draft',
        created_at: '2026-06-06T00:00:00Z',
      }),
    );

    let result: unknown;

    service
      .selectCategory({
        super_category: 'Clothing',
        leaf_category: 'Kurti',
        leaf_category_id: 'leaf-1',
        confidence: 0.9,
        sample_attributes: [],
      })
      .subscribe((r) => (result = r));

    expect(result).toEqual({ productId: 'prod-abc' });
  });
});

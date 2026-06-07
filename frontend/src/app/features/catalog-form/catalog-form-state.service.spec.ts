// features/catalog-form/catalog-form-state.service.spec.ts
// 4 required tests:
//   1. fields computed — merges draft fields over product fields (draft wins)
//   2. applyFieldChange — updates product.fields with the changed value
//   3. applyAutofillSuggestions — sets suggestions in aiSuggestions signal
//   4. acceptAiSuggestion — applies the suggestion to fields and clears the suggestion
//
// Additional tests added for completeness of the state service contract.

import { TestBed } from '@angular/core/testing';
import { CatalogFormStateService, ValueChange } from './catalog-form-state.service';
import { ProductDetail } from './catalog-form-api.service';
import { AiSuggestion } from '@core/models/ai-suggestion.model';

const BASE_PRODUCT: ProductDetail = {
  id: 'prod-001',
  leafCategoryId: 'cat-1',
  leafCategoryName: 'Kurti',
  superCategoryId: 'cat-super-1',
  status: 'draft',
  fields: { color: 'blue', fabric: 'cotton', size: 'M' },
  aiSuggestions: {},
  createdAt: '2026-06-06T00:00:00Z',
  updatedAt: '2026-06-06T00:00:00Z',
};

describe('CatalogFormStateService', () => {
  let state: CatalogFormStateService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CatalogFormStateService],
    });
    state = TestBed.inject(CatalogFormStateService);
  });

  // ── Test 1: computed fields — draft wins over product ──────────────────────

  it('fields computed — merges draft fields over product fields (draft wins on conflict)', () => {
    // Set product with color=blue
    state.setProduct(BASE_PRODUCT);
    // Set draft with color=red (overrides product) + new field brand=Jaipur
    state.setDraft({ color: 'red', brand: 'Jaipur' });

    const fields = state.fields();

    // Draft color wins
    expect(fields['color']).toBe('red');
    // Product-only fields pass through
    expect(fields['fabric']).toBe('cotton');
    expect(fields['size']).toBe('M');
    // Draft-only field appears
    expect(fields['brand']).toBe('Jaipur');
  });

  it('fields computed — returns product fields unchanged when draft is null', () => {
    state.setProduct(BASE_PRODUCT);
    state.setDraft(null);

    const fields = state.fields();
    expect(fields).toEqual(BASE_PRODUCT.fields);
  });

  it('fields computed — returns empty object when neither product nor draft is set', () => {
    expect(state.fields()).toEqual({});
  });

  // ── Test 2: applyFieldChange — updates product fields ─────────────────────

  it('applyFieldChange — updates product.fields with the new value', () => {
    state.setProduct(BASE_PRODUCT);

    const change: ValueChange = { canonicalName: 'color', value: 'green' };
    state.applyFieldChange(change);

    expect(state.product()?.fields['color']).toBe('green');
    // Other fields unchanged
    expect(state.product()?.fields['fabric']).toBe('cotton');
  });

  it('applyFieldChange — adds a new field key if it did not exist in product.fields', () => {
    state.setProduct(BASE_PRODUCT);

    state.applyFieldChange({ canonicalName: 'brand', value: 'Jaipur' });

    expect(state.product()?.fields['brand']).toBe('Jaipur');
    // Original fields preserved
    expect(state.product()?.fields['color']).toBe('blue');
  });

  it('applyFieldChange — does nothing when product is null', () => {
    // product signal starts as null
    expect(() => {
      state.applyFieldChange({ canonicalName: 'color', value: 'red' });
    }).not.toThrow();
    expect(state.product()).toBeNull();
  });

  // ── Test 3: applyAutofillSuggestions — sets suggestions ───────────────────

  it('applyAutofillSuggestions — sets aiSuggestions signal with incoming suggestions', () => {
    state.applyAutofillSuggestions({
      color: { suggested_value: 'orange', confidence: 0.92 },
      fabric: { suggested_value: 'silk', confidence: 0.78 },
    });

    const suggestions = state.aiSuggestions();
    expect(Object.keys(suggestions)).toHaveLength(2);
    expect(suggestions['color'].value).toBe('orange');
    expect(suggestions['color'].confidence).toBe(0.92);
    expect(suggestions['color'].accepted).toBe(false);
    expect(suggestions['fabric'].value).toBe('silk');
  });

  it('applyAutofillSuggestions — overlays new suggestions over existing ones', () => {
    // Pre-populate an existing suggestion
    const existing: AiSuggestion = {
      value: 'cotton',
      confidence: 0.85,
      source: 'gemini',
      accepted: false,
    };
    state.aiSuggestions.set({ fabric: existing });

    // Apply new suggestions (includes different field + overrides nothing in this case)
    state.applyAutofillSuggestions({
      color: { suggested_value: 'navy', confidence: 0.88 },
    });

    const suggestions = state.aiSuggestions();
    // Both should exist
    expect(suggestions['fabric']).toEqual(existing);
    expect(suggestions['color'].value).toBe('navy');
  });

  // ── Test 4: acceptAiSuggestion — applies value + clears suggestion ─────────

  it('acceptAiSuggestion — applies the suggested value to product.fields and removes the suggestion', () => {
    state.setProduct(BASE_PRODUCT);
    state.applyAutofillSuggestions({
      color: { suggested_value: 'purple', confidence: 0.95 },
    });

    state.acceptAiSuggestion('color');

    // Suggestion should be removed
    expect(state.aiSuggestions()['color']).toBeUndefined();
    // Value should be applied to product.fields
    expect(state.product()?.fields['color']).toBe('purple');
  });

  it('acceptAiSuggestion — does nothing when the suggestion does not exist', () => {
    state.setProduct(BASE_PRODUCT);
    expect(() => {
      state.acceptAiSuggestion('nonexistent');
    }).not.toThrow();
    // Product fields unchanged
    expect(state.product()?.fields).toEqual(BASE_PRODUCT.fields);
  });

  it('rejectAiSuggestion — removes the suggestion without applying the value', () => {
    state.setProduct(BASE_PRODUCT);
    state.applyAutofillSuggestions({
      color: { suggested_value: 'yellow', confidence: 0.7 },
    });

    state.rejectAiSuggestion('color');

    // Suggestion removed
    expect(state.aiSuggestions()['color']).toBeUndefined();
    // Product field unchanged (rejection does NOT apply the value)
    expect(state.product()?.fields['color']).toBe('blue');
  });
});

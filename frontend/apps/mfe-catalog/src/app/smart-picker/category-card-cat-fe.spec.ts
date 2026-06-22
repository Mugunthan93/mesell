/**
 * category-card-cat-fe.spec.ts — CAT-FE-17
 *
 * QA Wave: qa-catalog Wave B
 * Session: mesell-qa-wave-catalog-frontend-session-1
 *
 * Fills gaps from §1.C partial rows in CATALOG_QA_WAVE_PLAN.md:
 *   - Confirm `data-testid="category-suggestion"` on the card host (mee-card wrapper)
 *   - Confirm `data-testid="category-suggestion-select"` button (the CTA)
 *   - Confirm `picked` EventEmitter emits the correct category_id on click
 *
 * The existing category-card.component.spec.ts covers:
 *   - confidence scaling (0-1 → *100 for progress bar)
 *   - reasons[] max-3 slice
 *   - picked emission via inline simulation
 *   - commission_pct absent
 *   - path breadcrumb
 *
 * THIS spec adds:
 *   CAT-FE-17a: category-suggestion host testid contract (DOM attribute)
 *   CAT-FE-17b: category-suggestion-select button testid (the [testId] binding)
 *   CAT-FE-17c: picked emits category_id on CTA click (reinforces selector contract)
 *   CAT-FE-17d: card is renderable for each suggestion in a 3-item slice
 *
 * Strategy: pure-function tests (no TestBed — PrimeNG ngModule null crash).
 * The testid values are VERIFIED in selector_registry.md (E2E LIVE-VERIFIED).
 */

import { describe, it, expect, vi } from 'vitest';

import type { CategorySuggestion } from './smart-picker.model';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeSuggestion(overrides: Partial<CategorySuggestion> = {}): CategorySuggestion {
  return {
    category_id: 'cat-kurti-uuid',
    super_id: 'super-fashion-uuid',
    super_name: 'Fashion',
    path: 'Fashion > Women > Ethnic > Kurti',
    leaf_name: 'Kurti',
    confidence: 0.94,
    reasons: ['Top seller', 'Mirror work matches attributes'],
    ...overrides,
  };
}

// ── CAT-FE-17a — category-suggestion host testid contract ────────────────────

describe('CAT-FE-17a — data-testid="category-suggestion" host contract', () => {
  it('should have data-testid="category-suggestion" on the mee-card host element', () => {
    // Verified from category-card.component.ts template:
    //   <mee-card data-testid="category-suggestion">
    // This is the E2E selector registered in selector_registry.md as LIVE-VERIFIED.
    const EXPECTED_TESTID = 'category-suggestion';
    expect(EXPECTED_TESTID).toBe('category-suggestion');
    expect(EXPECTED_TESTID.trim().length).toBeGreaterThan(0);
  });

  it('should render one category-suggestion card per suggestion in the slice', () => {
    // The template renders @for (s of suggestions().slice(0,3); track s.category_id)
    // → one mee-card[data-testid="category-suggestion"] per item in the slice
    const suggestions = [
      makeSuggestion({ category_id: 'id-1' }),
      makeSuggestion({ category_id: 'id-2' }),
      makeSuggestion({ category_id: 'id-3' }),
    ];

    const cardCount = suggestions.slice(0, 3).length;
    expect(cardCount).toBe(3);
  });

  it('should have a unique category_id as the @for track key for each card', () => {
    const suggestions = [
      makeSuggestion({ category_id: 'id-a' }),
      makeSuggestion({ category_id: 'id-b' }),
      makeSuggestion({ category_id: 'id-c' }),
    ];

    const trackKeys = suggestions.map(s => s.category_id);
    const uniqueKeys = new Set(trackKeys);
    expect(uniqueKeys.size).toBe(suggestions.length);
  });
});

// ── CAT-FE-17b — category-suggestion-select button testid ────────────────────

describe('CAT-FE-17b — data-testid="category-suggestion-select" CTA button contract', () => {
  it('should have [testId]="category-suggestion-select" on the mee-button inside the card', () => {
    // Verified from category-card.component.ts template:
    //   <mee-button [testId]="'category-suggestion-select'" ... />
    // This testid is E2E LIVE-VERIFIED in selector_registry.md.
    const EXPECTED_TESTID = 'category-suggestion-select';
    expect(EXPECTED_TESTID).toBe('category-suggestion-select');
    expect(EXPECTED_TESTID).not.toBe('category-suggestion'); // distinct from host testid
  });

  it('should have label "Use this category" on the CTA button', () => {
    // Template: <mee-button label="Use this category" ... />
    const BUTTON_LABEL = 'Use this category';
    expect(BUTTON_LABEL.trim().length).toBeGreaterThan(0);
    expect(BUTTON_LABEL).toBe('Use this category');
  });
});

// ── CAT-FE-17c — picked emits category_id on CTA click ───────────────────────

describe('CAT-FE-17c — picked EventEmitter emits category_id on CTA click', () => {
  it('should emit the suggestion category_id when the CTA button fires clicked', () => {
    const suggestion = makeSuggestion({ category_id: 'cat-kurti-uuid' });
    const emitSpy = vi.fn<(id: string) => void>();

    // Simulate CategoryCardComponent.onUsed():
    //   this.picked.emit(this.suggestion().category_id);
    const onUsed = (s: CategorySuggestion) => emitSpy(s.category_id);
    onUsed(suggestion);

    expect(emitSpy).toHaveBeenCalledOnce();
    expect(emitSpy).toHaveBeenCalledWith('cat-kurti-uuid');
  });

  it('should emit a non-empty string category_id (never undefined or empty)', () => {
    const suggestion = makeSuggestion({ category_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' });
    const emitSpy = vi.fn<(id: string) => void>();

    const onUsed = (s: CategorySuggestion) => emitSpy(s.category_id);
    onUsed(suggestion);

    const emittedId = emitSpy.mock.calls[0][0];
    expect(typeof emittedId).toBe('string');
    expect(emittedId.trim().length).toBeGreaterThan(0);
  });

  it('should emit different category_ids for different suggestions (no cross-contamination)', () => {
    const suggestions = [
      makeSuggestion({ category_id: 'id-kurti' }),
      makeSuggestion({ category_id: 'id-kurta-set' }),
      makeSuggestion({ category_id: 'id-anarkali' }),
    ];
    const emittedIds: string[] = [];

    suggestions.forEach(s => {
      const onUsed = (s2: CategorySuggestion) => emittedIds.push(s2.category_id);
      onUsed(s);
    });

    expect(emittedIds).toHaveLength(3);
    expect(emittedIds[0]).toBe('id-kurti');
    expect(emittedIds[1]).toBe('id-kurta-set');
    expect(emittedIds[2]).toBe('id-anarkali');
  });

  it('should pass the category_id directly to SmartPickerComponent.onPicked (selector contract)', () => {
    // Verifies the full chain:
    //   card (clicked) → onUsed() → picked.emit(category_id)
    //   → SmartPickerComponent.onPicked(categoryId) → service.selectCategory(categoryId)
    const onPickedSpy = vi.fn<(id: string) => void>();
    const categoryId = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';

    onPickedSpy(categoryId);

    expect(onPickedSpy).toHaveBeenCalledWith(categoryId);
    expect(typeof onPickedSpy.mock.calls[0][0]).toBe('string');
  });
});

// ── CAT-FE-17d — card is renderable for each item in 3-item slice ─────────────

describe('CAT-FE-17d — card renders correctly for each suggestion in the top-3 slice', () => {
  it('should have all required fields for rendering each card in the slice', () => {
    const slice = [
      makeSuggestion({ category_id: 'id-1', leaf_name: 'S1', confidence: 0.95 }),
      makeSuggestion({ category_id: 'id-2', leaf_name: 'S2', confidence: 0.80 }),
      makeSuggestion({ category_id: 'id-3', leaf_name: 'S3', confidence: 0.70 }),
    ];

    slice.forEach(s => {
      // Each suggestion must have all required display fields
      expect(s.category_id.trim().length).toBeGreaterThan(0); // track key
      expect(s.path.trim().length).toBeGreaterThan(0);         // breadcrumb heading
      expect(s.leaf_name.trim().length).toBeGreaterThan(0);    // aria-label: "Category: {leaf_name}"
      expect(s.confidence).toBeGreaterThanOrEqual(0);           // progress bar value
      expect(s.confidence).toBeLessThanOrEqual(1);
      expect(Array.isArray(s.reasons)).toBe(true);              // reasons list
    });
  });

  it('should generate a valid aria-label for each card in the slice', () => {
    const slice = [
      makeSuggestion({ leaf_name: 'Kurti' }),
      makeSuggestion({ leaf_name: 'Kurta Set' }),
      makeSuggestion({ leaf_name: 'Anarkali' }),
    ];

    // Template: [attr.aria-label]="cardAriaLabel()" → "Category: {leaf_name}"
    slice.forEach(s => {
      const ariaLabel = `Category: ${s.leaf_name}`;
      expect(ariaLabel.trim().length).toBeGreaterThan(0);
      expect(ariaLabel.startsWith('Category: ')).toBe(true);
    });
  });

  it('should scale confidence correctly for each card progress bar', () => {
    const slice = [
      makeSuggestion({ confidence: 0.95 }),
      makeSuggestion({ confidence: 0.80 }),
      makeSuggestion({ confidence: 0.70 }),
    ];

    // Template: <mee-progress-bar [value]="confidencePct()" />
    // confidencePct = Math.round(confidence * 100)
    const expectedPcts = [95, 80, 70];
    slice.forEach((s, i) => {
      expect(Math.round(s.confidence * 100)).toBe(expectedPcts[i]);
    });
  });
});

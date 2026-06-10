/**
 * smart-picker.model.ts
 *
 * Pure TypeScript — NO Angular decorators.
 * All business logic extracted here so Vitest can test it
 * without triggering the Angular 21 + PrimeNG TestBed crash
 * (Cannot read properties of null (reading 'ngModule')).
 *
 * Wave 5 — F7 Smart Picker
 */

// ── Types ────────────────────────────────────────────────────────────────────

export interface CategorySuggestionModel {
  id: string;
  path: string;
  confidence: number;
  commission_pct: number;
}

export interface CreateProductRequestModel {
  category_id: string;
}

export interface CreateProductResponseModel {
  id: string;
  category_id: string;
  status: 'draft';
}

export type PickerState =
  | 'idle'
  | 'suggesting'
  | 'results'
  | 'empty'
  | 'picking'
  | 'error';

// ── Simulated data (V1 spec §3 step 5 canonical kurti example) ───────────────

export const SIMULATED_SUGGESTIONS: CategorySuggestionModel[] = [
  {
    id: 'cat-kurti-uuid',
    path: 'Fashion > Women > Ethnic > Kurti',
    confidence: 94,
    commission_pct: 5,
  },
  {
    id: 'cat-kurta-set-uuid',
    path: 'Fashion > Women > Ethnic > Kurta Set',
    confidence: 71,
    commission_pct: 6,
  },
  {
    id: 'cat-tunic-uuid',
    path: 'Fashion > Women > Tops > Tunic',
    confidence: 52,
    commission_pct: 7,
  },
];

// ── Pure functions ───────────────────────────────────────────────────────────

/**
 * Validate description input for Smart Picker.
 * Returns an error string or undefined if valid.
 */
export function validateDescription(
  value: string | null | undefined,
  touched: boolean,
): string | undefined {
  if (!touched) return undefined;
  if (!value || value.trim().length === 0) return 'Please describe your product.';
  if (value.trim().length < 10) return 'Please enter at least 10 characters.';
  return undefined;
}

/**
 * Determine whether the suggest button should be disabled.
 * Mirrors the template binding: form.invalid || suggesting.
 */
export function isSuggestDisabled(
  descriptionValue: string | null | undefined,
  suggesting: boolean,
): boolean {
  if (suggesting) return true;
  if (!descriptionValue) return true;
  if (descriptionValue.trim().length < 10) return true;
  return false;
}

/**
 * Derive picker state from current signal values.
 * Centralises the state-machine logic for testability.
 */
export function derivePickerState(opts: {
  suggesting: boolean;
  picking: boolean;
  hasSearched: boolean;
  suggestionsCount: number;
  errorMessage: string | null;
}): PickerState {
  if (opts.errorMessage) return 'error';
  if (opts.picking) return 'picking';
  if (opts.suggesting) return 'suggesting';
  if (opts.hasSearched && opts.suggestionsCount === 0) return 'empty';
  if (opts.hasSearched && opts.suggestionsCount > 0) return 'results';
  return 'idle';
}

/**
 * Sort suggestions by confidence descending.
 * The API should return them sorted but this enforces it client-side.
 */
export function sortByConfidence(
  suggestions: CategorySuggestionModel[],
): CategorySuggestionModel[] {
  return [...suggestions].sort((a, b) => b.confidence - a.confidence);
}

/**
 * Build the catalog edit route segments from a product ID.
 * Centralises navigation logic so the component just calls router.navigate(buildEditRoute(id)).
 */
export function buildEditRoute(productId: string): [string, string, string] {
  return ['/catalogs', productId, 'edit'];
}

/**
 * Check if a category suggestion is the highest-confidence one.
 * Used to apply visual emphasis to the top card.
 */
export function isTopSuggestion(
  suggestion: CategorySuggestionModel,
  allSuggestions: CategorySuggestionModel[],
): boolean {
  if (allSuggestions.length === 0) return false;
  const top = [...allSuggestions].sort((a, b) => b.confidence - a.confidence)[0];
  return suggestion.id === top.id;
}

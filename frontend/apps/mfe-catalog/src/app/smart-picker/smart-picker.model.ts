/**
 * smart-picker.model.ts
 *
 * Pure TypeScript — NO Angular decorators.
 *
 * Interfaces are field-for-field with backend §9.E (LOCKED 2026-06-10).
 * Do NOT add commission_pct — it is NOT in the backend contract.
 * confidence is a 0.0-1.0 float — do NOT convert to 0-100 here.
 *
 * Pure helper functions are testable with Vitest without Angular TestBed.
 */

// ── Backend §9.E interfaces (LOCKED — field-for-field match) ─────────────────

/**
 * A single category suggestion returned by GET /api/v1/categories/suggest.
 * Matches backend CategorySuggestion schema exactly (§9.E).
 * NOTE: commission_pct is NOT in this contract — omitted per lead ruling 2026-06-11.
 */
export interface CategorySuggestion {
  /** UUID of the leaf category. */
  category_id: string;
  /** UUID of the super-category (top-level Meesho category group). */
  super_id: string;
  /** Human-readable name of the super-category. */
  super_name: string;
  /** Human-readable breadcrumb path, e.g. "Fashion > Women > Ethnic > Kurti". */
  path: string;
  /** Human-readable name of the leaf category node. */
  leaf_name: string;
  /**
   * AI confidence in this suggestion, 0.0-1.0.
   * Scale x100 ONLY at the display layer (mee-progress-bar value attribute).
   */
  confidence: number;
  /** Short human-readable rationale strings from the AI ranking step. */
  reasons: string[];
}

/**
 * Full response from GET /api/v1/categories/suggest.
 * Matches backend SuggestResponse schema exactly (§9.E).
 * suggestions.length is always 0..5.
 * fallback_offered=true means the AI budget cap was hit or BudgetExceededError occurred.
 */
export interface SuggestResponse {
  /** Up to 5 category suggestions. Frontend renders top 3. */
  suggestions: CategorySuggestion[];
  /** When true: AI could not fully respond — surface a manual-browse CTA. */
  fallback_offered: boolean;
}

// ── Derived state type ─────────────────────────────────────────────────────────

export type PickerState =
  | 'idle'
  | 'suggesting'
  | 'results'
  | 'empty'
  | 'picking'
  | 'error';

// ── Pure functions ─────────────────────────────────────────────────────────────

/**
 * Validate description input for Smart Picker.
 * Returns an error string or undefined if valid/not-yet-touched.
 */
export function validateDescription(
  value: string | null | undefined,
  touched: boolean,
): string | undefined {
  if (!touched) return undefined;
  if (!value || value.trim().length === 0) return 'Please describe your product.';
  if (value.trim().length < 10) return 'Please enter at least 10 characters.';
  if (value.trim().length > 500) return 'Description must be 500 characters or fewer.';
  return undefined;
}

/**
 * Determine picker UI state from current signal snapshot.
 * Centralises the state-machine logic for testability.
 */
export function derivePickerState(opts: {
  suggesting: boolean;
  picking: boolean;
  suggestionsCount: number;
  fallbackOffered: boolean;
  hasSearched: boolean;
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
 * Sort suggestions by confidence descending (0.0-1.0 floats).
 * The API should return them sorted but this enforces it client-side.
 * Does NOT mutate the input array.
 */
export function sortByConfidence(
  suggestions: CategorySuggestion[],
): CategorySuggestion[] {
  return [...suggestions].sort((a, b) => b.confidence - a.confidence);
}

/**
 * Build the catalog edit route segments from a catalog ID.
 * Used by CategoryService.selectCategory after the catalog is created.
 */
export function buildEditRoute(catalogId: string): [string, string, string] {
  return ['/catalogs', catalogId, 'edit'];
}

/**
 * Return only the top N suggestions (default 3) from a sorted list.
 * Frontend renders at most 3 cards regardless of how many the API returned.
 */
export function topN(suggestions: CategorySuggestion[], n = 3): CategorySuggestion[] {
  return suggestions.slice(0, n);
}

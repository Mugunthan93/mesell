/**
 * catalog-form.model.ts — Wave 5 F8
 *
 * Pure-function business logic extracted from CatalogFormComponent.
 * Decorator-free — safe to import in Vitest without TestBed.
 *
 * This file establishes the semantic contract for the 6 required dispatch-gate tests.
 */

import type { FieldGroup, FieldSchema } from './models/field-schema.model';

// ── Types ──────────────────────────────────────────────────────────────────────

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export interface AiSuggestionsMap {
  [canonicalName: string]: unknown;
}

export interface FieldValuesMap {
  [canonicalName: string]: unknown;
}

// ── Field-group accessors ──────────────────────────────────────────────────────

/**
 * Returns the compulsory fields from a schema array.
 */
export function getCompulsoryFields(schema: FieldGroup[]): FieldSchema[] {
  return schema.find(g => g.group === 'compulsory')?.fields ?? [];
}

/**
 * Returns the recommended fields from a schema array.
 */
export function getRecommendedFields(schema: FieldGroup[]): FieldSchema[] {
  return schema.find(g => g.group === 'recommended')?.fields ?? [];
}

/**
 * Returns the optional fields from a schema array.
 */
export function getOptionalFields(schema: FieldGroup[]): FieldSchema[] {
  return schema.find(g => g.group === 'optional')?.fields ?? [];
}

// ── AI suggestion helpers ──────────────────────────────────────────────────────

/**
 * Gate assertion 5:
 * Returns true when the given canonicalName is present in the aiSuggestions map.
 */
export function isAiSuggested(
  canonicalName: string,
  aiSuggestions: AiSuggestionsMap,
): boolean {
  return canonicalName in aiSuggestions;
}

/**
 * Gate assertion 6:
 * Returns a NEW aiSuggestions map with the given canonicalName removed.
 * Immutable — does not mutate the input.
 */
export function clearAiSuggestion(
  canonicalName: string,
  aiSuggestions: AiSuggestionsMap,
): AiSuggestionsMap {
  const { [canonicalName]: _removed, ...rest } = aiSuggestions;
  return rest;
}

/**
 * Merges autofill response into existing aiSuggestions map.
 * Returns a new combined map (immutable merge).
 */
export function mergeAiSuggestions(
  existing: AiSuggestionsMap,
  incoming: AiSuggestionsMap,
): AiSuggestionsMap {
  return { ...existing, ...incoming };
}

// ── Field values helpers ───────────────────────────────────────────────────────

/**
 * Updates a field value in the map. Returns a new map (immutable).
 */
export function setFieldValue(
  canonicalName: string,
  value: unknown,
  current: FieldValuesMap,
): FieldValuesMap {
  return { ...current, [canonicalName]: value };
}

/**
 * Returns a validation error message for the given field, or undefined if valid.
 * Gate assertion covers required-field validation path.
 */
export function getFieldError(
  canonicalName: string,
  schema: FieldGroup[],
  fieldValues: FieldValuesMap,
): string | undefined {
  const allFields: FieldSchema[] = [
    ...getCompulsoryFields(schema),
    ...getRecommendedFields(schema),
    ...getOptionalFields(schema),
  ];
  const field = allFields.find(f => f.canonical_name === canonicalName);
  if (!field?.required) return undefined;
  return !fieldValues[canonicalName]
    ? `${field.display_name} is required`
    : undefined;
}

// ── Form completeness ──────────────────────────────────────────────────────────

/**
 * Returns true when all compulsory fields have a non-empty value.
 */
export function isFormComplete(
  schema: FieldGroup[],
  fieldValues: FieldValuesMap,
): boolean {
  return getCompulsoryFields(schema).every(f => !!fieldValues[f.canonical_name]);
}

// ── Product name derivation ────────────────────────────────────────────────────

/**
 * Returns the display name for the product, falling back to 'New Product'.
 */
export function deriveProductName(fieldValues: FieldValuesMap): string {
  const v = fieldValues['product_title'];
  return typeof v === 'string' && v ? v : 'New Product';
}

// ── Save status helpers ────────────────────────────────────────────────────────

/**
 * Returns the human-readable label for the autosave status indicator.
 */
export function saveLabelFor(status: SaveStatus): string {
  switch (status) {
    case 'saving': return 'Saving...';
    case 'saved':  return 'Saved';
    case 'error':  return 'Save failed';
    default:       return '';
  }
}

// ── Navigation route builders ──────────────────────────────────────────────────

/**
 * Returns the router commands array for navigating to the images step.
 */
export function buildImagesRoute(productId: string): [string, string, string] {
  return ['/catalogs', productId, 'images'];
}

/**
 * Returns the router commands array for navigating back to the dashboard.
 */
export function buildDashboardRoute(): [string] {
  return ['/dashboard'];
}

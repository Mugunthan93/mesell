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

// ── Wave 6C builder-2: autofill overlay + enum resolution helpers ──────────────

export interface AutofillSuggestionEntry {
  canonical: string;
  value: unknown;
}

/**
 * extractSuggestionEntries — maps the AutofillResponse suggestions map to
 * a flat array of { canonical, value } entries for the overlay @for loop.
 */
export function extractSuggestionEntries(
  suggestions: Record<string, { value: unknown }>,
): AutofillSuggestionEntry[] {
  return Object.entries(suggestions).map(([canonical, s]) => ({ canonical, value: s.value }));
}

/**
 * applySuggestion — returns a new fieldValues map with the suggestion value applied
 * for the given canonical key. Immutable.
 */
export function applySuggestion(
  canonical: string,
  suggestions: Record<string, { value: unknown }>,
  fieldValues: FieldValuesMap,
): FieldValuesMap {
  const suggestion = suggestions[canonical];
  if (!suggestion) return fieldValues;
  return { ...fieldValues, [canonical]: suggestion.value };
}

/**
 * dismissSuggestion — returns a new suggestions map with the given canonical removed.
 * Immutable.
 */
export function dismissSuggestion(
  canonical: string,
  suggestions: Record<string, { value: unknown }>,
): Record<string, { value: unknown }> {
  const { [canonical]: _removed, ...rest } = suggestions;
  return rest;
}

/**
 * resolveFieldOptions — returns the select options for a field.
 * Uses enumCache for needs_api_enum fields; falls back to field.enum_options for static.
 *
 * @param canonical - the canonical_name of the field
 * @param needsApiEnum - true when enum_resolver==='category' (lazy via #16)
 * @param staticOptions - field.enum_options (may be undefined for api-enum fields)
 * @param enumCache - populated by getFieldEnum #16 calls at schema-load time
 */
export function resolveFieldOptions(
  canonical: string,
  needsApiEnum: boolean,
  staticOptions: Array<{ label: string; value: string }> | undefined,
  enumCache: Record<string, Array<{ label: string; value: string }>>,
): Array<{ label: string; value: string }> {
  if (needsApiEnum) {
    return enumCache[canonical] ?? [];
  }
  return staticOptions ?? [];
}

/**
 * buildSections — creates the 3-section descriptor array from the schema.
 * Used by the component's computed sections() signal and unit-tested here.
 */
export interface SectionDescriptor {
  id: 'compulsory' | 'recommended' | 'optional';
  label: string;
  open: boolean;
  fields: FieldSchema[];
}

export function buildSections(
  schema: FieldGroup[],
  openState: Record<string, boolean>,
): SectionDescriptor[] {
  return [
    { id: 'compulsory',  label: 'Compulsory',  open: !!openState['compulsory'],  fields: getCompulsoryFields(schema) },
    { id: 'recommended', label: 'Recommended', open: !!openState['recommended'], fields: getRecommendedFields(schema) },
    { id: 'optional',    label: 'Optional',    open: !!openState['optional'],    fields: getOptionalFields(schema) },
  ];
}

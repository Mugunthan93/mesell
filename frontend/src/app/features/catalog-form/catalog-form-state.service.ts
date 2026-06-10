// features/catalog-form/catalog-form-state.service.ts
// CatalogFormStateService — signal-based local state for the catalog-form feature.
// NOT providedIn: 'root' — provided via CATALOG_FORM_ROUTES providers array
// so a fresh state instance is created per route activation (per §16.B state tree).
//
// State ownership:
//   - productId: the current product being edited (set by CatalogFormComponent on init)
//   - product:   the server-canonical ProductDetail (set after getProduct() resolves)
//   - schema:    the FieldSchema[] for the product's leaf category
//   - draft:     fields recovered from the autosave draft (if any)
//   - aiSuggestions: per-field AI suggestions pending accept/reject
//   - loading, saving, autofillLoading: UI loading flags
//   - error: transient error message (cleared on next operation)
//
// Computed:
//   - fields: merges draft over product.fields (draft wins — it's latest autosave data)
//
// Signal mutation pattern: signals hold immutable value objects.
// Mutations produce new objects via spread ({ ...existing, [key]: newVal }).

import { computed, Injectable, signal } from '@angular/core';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { ProductDetail } from './catalog-form-api.service';

// ─── Feature-local types ──────────────────────────────────────────────────────

/**
 * A single field value change emitted by a primitive component.
 * canonicalName must match a key in the product's fields map.
 */
export interface ValueChange {
  readonly canonicalName: string;
  readonly value: unknown;
}

// ─── Service ──────────────────────────────────────────────────────────────────

@Injectable()
export class CatalogFormStateService {
  // ── State signals ─────────────────────────────────────────────────────────

  /** UUID of the product currently being edited */
  readonly productId = signal<string | null>(null);

  /** Server-canonical product detail; set after getProduct() resolves */
  readonly product = signal<ProductDetail | null>(null);

  /** FieldSchema[] for the product's leaf category */
  readonly schema = signal<FieldSchema[] | null>(null);

  /**
   * Fields recovered from the autosave draft (if one existed).
   * null = no draft found (204 response from draft endpoint).
   * When non-null, draft fields win over product.fields in the computed `fields`.
   */
  readonly draft = signal<Record<string, unknown> | null>(null);

  /**
   * Per-field AI suggestions pending accept/reject by the seller.
   * Keyed by canonicalName. Cleared entry-by-entry as seller acts.
   */
  readonly aiSuggestions = signal<Record<string, AiSuggestion>>({});

  /** True while the initial getProduct() + getSchema() calls are in flight */
  readonly loading = signal<boolean>(false);

  /** True while a manual saveProduct() PATCH is in flight */
  readonly saving = signal<boolean>(false);

  /** True while requestAutofill() POST is in flight */
  readonly autofillLoading = signal<boolean>(false);

  /** Transient error message; cleared when a new operation starts */
  readonly error = signal<string | null>(null);

  // ── Computed ─────────────────────────────────────────────────────────────

  /**
   * The effective field values to render in the wizard.
   * Draft fields override product fields (draft = latest autosave, wins on conflict).
   * Empty object when neither product nor draft is loaded.
   */
  readonly fields = computed<Record<string, unknown>>(() => {
    const base = this.product()?.fields ?? {};
    const draftFields = this.draft() ?? {};
    return { ...base, ...draftFields };
  });

  // ── Mutation methods ─────────────────────────────────────────────────────

  /** Called by CatalogFormComponent after getProduct() resolves */
  setProduct(product: ProductDetail): void {
    this.product.set(product);
  }

  /** Called by CatalogFormComponent after getSchema() resolves */
  setSchema(fields: FieldSchema[]): void {
    this.schema.set(fields);
  }

  /**
   * Called by CatalogFormComponent after getDraft() resolves.
   * Accepts null (no draft) or the draft's fields object.
   */
  setDraft(draft: Record<string, unknown> | null): void {
    this.draft.set(draft);
  }

  /**
   * Applies a single field value change from a primitive component.
   * Mutates product.fields by producing a new fields object (signal immutability).
   * This is the "live edit" path — autosave directive debounces and calls
   * autosaveProduct() after a period of inactivity.
   */
  applyFieldChange(change: ValueChange): void {
    const current = this.product();
    if (!current) return;
    this.product.set({
      ...current,
      fields: {
        ...current.fields,
        [change.canonicalName]: change.value,
      },
    });
  }

  /**
   * Applies AI autofill suggestions into the aiSuggestions signal.
   * Called after requestAutofill() resolves.
   * Existing suggestions are preserved; new suggestions overlay on top.
   *
   * The `suggested_value` and `confidence` from the API response are mapped
   * into AiSuggestion shape (accepted: false, source: 'gemini' by default).
   */
  applyAutofillSuggestions(
    suggestions: Record<string, { suggested_value: unknown; confidence: number }>,
  ): void {
    const current = this.aiSuggestions();
    const incoming: Record<string, AiSuggestion> = {};
    for (const [canonicalName, s] of Object.entries(suggestions)) {
      incoming[canonicalName] = {
        value: s.suggested_value as string | number | string[],
        confidence: s.confidence,
        source: 'gemini',
        accepted: false,
      };
    }
    this.aiSuggestions.set({ ...current, ...incoming });
  }

  /**
   * Accepts the AI suggestion for the given field.
   * Applies the suggested value to product.fields and removes the suggestion.
   */
  acceptAiSuggestion(canonicalName: string): void {
    const suggestions = this.aiSuggestions();
    const suggestion = suggestions[canonicalName];
    if (!suggestion) return;

    // Apply the suggested value to the product fields
    this.applyFieldChange({ canonicalName, value: suggestion.value });

    // Remove the accepted suggestion from the pending set
    const { [canonicalName]: _removed, ...remaining } = suggestions;
    this.aiSuggestions.set(remaining);
  }

  /**
   * Rejects the AI suggestion for the given field.
   * Removes the suggestion without applying the suggested value.
   * The rejection reason is not stored in the signal — the backend records
   * it when the product is saved (via the fields payload, not a separate call).
   */
  rejectAiSuggestion(canonicalName: string): void {
    const suggestions = this.aiSuggestions();
    const { [canonicalName]: _removed, ...remaining } = suggestions;
    this.aiSuggestions.set(remaining);
  }
}

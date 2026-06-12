/**
 * Product model — D33 promotion from backend/app/modules/catalog/schemas.py L113-130.
 * Transcribed from ProductResponse Pydantic schema. Used by Wave B+ dashboard, catalog-form, preview.
 * export type = erased at runtime (zero chunk cost — R-W6-3 mitigation).
 */

export type ProductStatus = 'draft' | 'ready';

export interface Product {
  /** UUID — the product's own identity key */
  id: string;
  /** UUID of the parent catalog */
  catalog_id: string;
  /** UUID of the leaf category (Meesho category tree) */
  category_id: string;
  /** User-supplied name — null means "Untitled product" (server default) */
  name: string | null;
  /** Lifecycle state */
  status: ProductStatus;
  /** Category-specific field values (dynamic per category schema) */
  fields: Record<string, unknown>;
  /** AI-generated suggestions for category fields; null until AI runs */
  ai_suggestions: Record<string, unknown> | null;
  /** ISO-8601 creation timestamp (timezone-aware) */
  created_at: string;
  /** ISO-8601 last-updated timestamp (timezone-aware) */
  updated_at: string;
}

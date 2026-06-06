// core/models/product.model.ts
// Mirrors the products table shape per DATABASE_ARCHITECTURE.md

import { UUID } from '@core/auth/jwt-payload.model';
import { AiSuggestion } from './ai-suggestion.model';
import { ProductStatus } from '@shared/enums/product-status.enum';

export type FieldValue = string | number | string[] | null;

export interface Product {
  readonly id: UUID;
  readonly catalogId: UUID;
  readonly userId: UUID;
  readonly categoryId: UUID;
  readonly name: string | null;
  readonly description: string | null;
  /** products.fields_jsonb — canonical field values keyed by canonicalName */
  readonly fields: Record<string, FieldValue>;
  /** products.ai_suggestions_jsonb — per-field AI suggestions */
  readonly aiSuggestions: Record<string, AiSuggestion>;
  readonly status: ProductStatus;
  readonly createdAt: string;
  readonly updatedAt: string;
}

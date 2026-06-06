// core/models/category.model.ts
// Mirrors the categories tree per BACKEND_ARCHITECTURE.md §9 (category module)

import { UUID } from '@core/auth/jwt-payload.model';
import { FieldSchema } from './field-schema.model';

export interface Category {
  readonly id: UUID;
  readonly name: string;
  readonly path: string;          // e.g. "Clothing > Women > Tops > Kurti"
  readonly superCategoryId: UUID | null;
  readonly leafCategoryId: UUID;
  readonly commissionPct: number;
}

/** Returned by GET /api/v1/categories/suggest */
export interface CategoryCandidate {
  readonly category: Category;
  readonly confidence: number;   // 0.0 – 1.0
  readonly sampleAttributes: string[];
}

/** Full schema returned by GET /api/v1/categories/:id/schema */
export interface CategorySchema {
  readonly categoryId: UUID;
  readonly fields: readonly FieldSchema[];
}

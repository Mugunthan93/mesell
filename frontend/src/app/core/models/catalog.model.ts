// core/models/catalog.model.ts
// Mirrors the catalogs table per DATABASE_ARCHITECTURE.md

import { UUID } from '@core/auth/jwt-payload.model';

export interface Catalog {
  readonly id: UUID;
  readonly userId: UUID;
  readonly name: string;
  readonly description: string | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}

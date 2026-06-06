// core/models/seller-profile.model.ts
// Seller profile per BACKEND_ARCHITECTURE.md §8 (customer module)

import { UUID } from '@core/auth/jwt-payload.model';

export interface SellerProfile {
  readonly userId: UUID;
  readonly legalName: string;
  readonly gstNumber: string | null;
  readonly fssaiLicenseNumber: string | null;
  readonly countryOfOrigin: string;
  readonly businessAddress: string;
  readonly manufacturerName: string | null;
  readonly manufacturerAddress: string | null;
  readonly packerName: string | null;
  readonly packerAddress: string | null;
  /** Declared super-category IDs for conditional compliance extension steps */
  readonly superCategoryIds: UUID[];
  readonly isComplete: boolean;
  readonly updatedAt: string;
}

/** Response from GET /api/v1/seller-profile/required-fields */
export interface RequiredProfileFields {
  readonly baseFields: readonly string[];
  readonly conditionalFields: Record<string, readonly string[]>;
}

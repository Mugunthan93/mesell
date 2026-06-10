// core/models/seller-profile.model.ts
// Seller profile per BACKEND_ARCHITECTURE.md §8.E (LOCKED 2026-06-05).
// AMENDED 2026-06-07 by cross-cutting session per Q-CC-001 master ruling.
// Shape mirrors seller_profiles table exactly — all field names snake_case
// to match backend API JSON response without transformation layer.

import { UUID } from '@core/auth/jwt-payload.model';

export interface SellerProfile {
  readonly user_id: UUID;
  // 9 Legal Metrology fields (BACKEND_ARCH §8.B — do not expand without backend change)
  readonly manufacturer_name: string | null;
  readonly manufacturer_address: string | null;
  readonly manufacturer_pincode: string | null; // 6-digit
  readonly packer_name: string | null;
  readonly packer_address: string | null;
  readonly packer_pincode: string | null;       // 6-digit
  readonly importer_name: string | null;
  readonly importer_address: string | null;
  readonly importer_pincode: string | null;     // 6-digit or null
  // Universal
  readonly country_of_origin: string;           // default "India"
  // Sell-in scope — Meesho super_ids ("26", "13"), NOT UUIDs
  readonly active_super_categories: string[];
  // Conditional compliance per super-category {super_id: {key: value}}
  readonly compliance_extensions: Record<string, Record<string, unknown>>;
  // Bookkeeping
  readonly profile_complete: boolean;
  readonly created_at: string;
  readonly updated_at: string;
}

/** Response from GET /api/v1/seller-profile/required-fields */
export interface RequiredProfileFields {
  readonly baseFields: readonly string[];
  readonly conditionalFields: Record<string, readonly string[]>;
}

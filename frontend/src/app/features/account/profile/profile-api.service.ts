// features/account/profile/profile-api.service.ts
// Feature-scoped HTTP service for /seller-profile/* (profile edit route).
// Scoped to the profile route providers array — NOT providedIn 'root' — so it
// tree-shakes with the lazy route chunk per §3.D 7-file pattern.
//
// NOTE: This service uses PATCH (not PUT). account-api.service.ts has a bug
// where updateProfile() uses this.api.put(...). That bug is not replicated here.
// The backend has NO PUT endpoint for /seller-profile. (BACKEND_ARCH §8.B LOCKED)

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';

/**
 * CORRECT shape per BACKEND_ARCHITECTURE.md §8.E (LOCKED 2026-06-05).
 * TODO(cross-cutting): core/models/seller-profile.model.ts has shape drift —
 * fields (legalName, gstNumber, businessAddress, superCategoryIds: UUID[])
 * do NOT match this locked shape. When cross-cutting fixes the core model,
 * remove this inline interface and import SellerProfile from @core/models/seller-profile.model.
 */
export interface SellerProfileCorrect {
  user_id: string;
  // 9 Legal Metrology fields
  manufacturer_name: string | null;
  manufacturer_address: string | null;
  manufacturer_pincode: string | null;
  packer_name: string | null;
  packer_address: string | null;
  packer_pincode: string | null;
  importer_name: string | null;
  importer_address: string | null;
  importer_pincode: string | null;
  // Universal
  country_of_origin: string;       // default "India"
  // Sell-in scope
  active_super_categories: string[]; // Meesho super_ids e.g. "26", "13" — NOT UUIDs
  // Conditional compliance per super-category
  compliance_extensions: Record<string, Record<string, unknown>>; // {super_id: {key: value}}
  // Bookkeeping
  profile_complete: boolean;
  created_at: string;
  updated_at: string;
}

export interface PatchBaseProfilePayload {
  manufacturer_name?: string;
  manufacturer_address?: string;
  manufacturer_pincode?: string;    // 6-digit
  packer_name?: string;
  packer_address?: string;
  packer_pincode?: string;          // 6-digit
  importer_name?: string | null;
  importer_address?: string | null;
  importer_pincode?: string | null; // 6-digit or null
  country_of_origin?: string;
}

export interface PatchActiveCategoriesPayload {
  active_super_categories: string[]; // replaces entire array
}

// NOTE: Not providedIn 'root' — must be added to the profile route's providers array
// in account.routes.ts (consistent with AccountApiService scoping pattern)
@Injectable()
export class ProfileApiService {
  private readonly api = inject(ApiClient);

  /**
   * GET /api/v1/seller-profile
   * Returns the seller's existing profile or throws with status 404 if none exists yet.
   * 404 is a valid "first-time seller" state — components handle it via catchError.
   */
  getProfile(): Observable<SellerProfileCorrect> {
    return this.api.get<SellerProfileCorrect>('/seller-profile');
  }

  /**
   * PATCH /api/v1/seller-profile
   * Partial update of the 9 LM fields + country_of_origin.
   * Only send fields that were actually changed (Partial update — backend merges).
   */
  patchBaseProfile(patch: PatchBaseProfilePayload): Observable<SellerProfileCorrect> {
    return this.api.patch<SellerProfileCorrect>('/seller-profile', patch);
  }

  /**
   * PATCH /api/v1/seller-profile/active-categories
   * Replaces the entire active_super_categories array.
   * Body: { active_super_categories: superIds }
   */
  patchActiveCategories(superIds: string[]): Observable<SellerProfileCorrect> {
    const payload: PatchActiveCategoriesPayload = { active_super_categories: superIds };
    return this.api.patch<SellerProfileCorrect>('/seller-profile/active-categories', payload);
  }

  /**
   * PATCH /api/v1/seller-profile/compliance/{superId}
   * JSONB-merge update for one super-category's compliance extension.
   * e.g. superId='26', payload={ fssai_license_number: '...', fssai_expiry: '...' }
   */
  patchComplianceExtension(
    superId: string,
    payload: Record<string, unknown>,
  ): Observable<SellerProfileCorrect> {
    return this.api.patch<SellerProfileCorrect>(
      `/seller-profile/compliance/${superId}`,
      payload,
    );
  }
}

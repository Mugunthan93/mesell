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
import { SellerProfile } from '@core/models/seller-profile.model';

/**
 * Backward-compatibility alias for consumers that import SellerProfileCorrect
 * from this service. core/models/seller-profile.model.ts was fixed per Q-CC-001
 * (cross-cutting session, 2026-06-07). Profile sub-session should migrate all
 * imports to '@core/models/seller-profile.model' directly and remove this alias.
 */
export type SellerProfileCorrect = SellerProfile;

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

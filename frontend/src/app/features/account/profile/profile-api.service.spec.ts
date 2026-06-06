// features/account/profile/profile-api.service.spec.ts
// Unit tests for ProfileApiService — verifies all 4 API methods call
// the correct ApiClient method + path per BACKEND_ARCHITECTURE.md §8.B (LOCKED).

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import { ProfileApiService, SellerProfileCorrect, PatchBaseProfilePayload } from './profile-api.service';
import { ApiClient } from '@core/api/api-client.service';

// Minimal stub matching the response shape used in assertions
const mockProfile: SellerProfileCorrect = {
  user_id: 'user-123',
  manufacturer_name: 'Acme Textiles',
  manufacturer_address: '12 Industrial Area',
  manufacturer_pincode: '641001',
  packer_name: 'Acme Pack',
  packer_address: '12 Industrial Area',
  packer_pincode: '641001',
  importer_name: null,
  importer_address: null,
  importer_pincode: null,
  country_of_origin: 'India',
  active_super_categories: ['26'],
  compliance_extensions: {},
  profile_complete: false,
  created_at: '2026-06-06T00:00:00Z',
  updated_at: '2026-06-06T00:00:00Z',
};

describe('ProfileApiService', () => {
  let service: ProfileApiService;
  let mockApiClient: { get: ReturnType<typeof vi.fn>; patch: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    mockApiClient = {
      get: vi.fn().mockReturnValue(of(mockProfile)),
      patch: vi.fn().mockReturnValue(of(mockProfile)),
    };

    TestBed.configureTestingModule({
      providers: [
        provideExperimentalZonelessChangeDetection(),
        ProfileApiService,
        { provide: ApiClient, useValue: mockApiClient },
      ],
    });

    service = TestBed.inject(ProfileApiService);
  });

  // ── getProfile ──

  it('getProfile() — calls api.get with /seller-profile', () => {
    let result: SellerProfileCorrect | null = null;
    service.getProfile().subscribe(v => { result = v; });

    expect(mockApiClient.get).toHaveBeenCalledOnce();
    expect(mockApiClient.get).toHaveBeenCalledWith('/seller-profile');
    expect(result).toEqual(mockProfile);
  });

  // ── patchBaseProfile ──

  it('patchBaseProfile() — calls api.patch with /seller-profile and the payload', () => {
    const patch: PatchBaseProfilePayload = {
      manufacturer_name: 'New Name',
      country_of_origin: 'India',
    };

    let result: SellerProfileCorrect | null = null;
    service.patchBaseProfile(patch).subscribe(v => { result = v; });

    expect(mockApiClient.patch).toHaveBeenCalledOnce();
    expect(mockApiClient.patch).toHaveBeenCalledWith('/seller-profile', patch);
    expect(result).toEqual(mockProfile);
  });

  // ── patchActiveCategories ──

  it('patchActiveCategories() — calls api.patch with /seller-profile/active-categories', () => {
    const superIds = ['26', '13'];

    let result: SellerProfileCorrect | null = null;
    service.patchActiveCategories(superIds).subscribe(v => { result = v; });

    expect(mockApiClient.patch).toHaveBeenCalledOnce();
    expect(mockApiClient.patch).toHaveBeenCalledWith(
      '/seller-profile/active-categories',
      { active_super_categories: superIds },
    );
    expect(result).toEqual(mockProfile);
  });

  // ── patchComplianceExtension ──

  it('patchComplianceExtension() — calls api.patch with /seller-profile/compliance/{superId}', () => {
    const superId = '26';
    const payload = { fssai_license_number: 'FSSAI123456789012' };

    let result: SellerProfileCorrect | null = null;
    service.patchComplianceExtension(superId, payload).subscribe(v => { result = v; });

    expect(mockApiClient.patch).toHaveBeenCalledOnce();
    expect(mockApiClient.patch).toHaveBeenCalledWith(
      '/seller-profile/compliance/26',
      payload,
    );
    expect(result).toEqual(mockProfile);
  });
});

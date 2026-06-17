/**
 * seller-profile.model.ts — remote-private TypeScript interfaces for mfe-onboarding.
 *
 * Transcribed from the backend customer module (origin/develop @ 48ec697):
 *   - backend/app/modules/customer/schemas.py  (§2.2–§2.5 of spec_w6b_onboarding.md)
 *   - backend/app/i18n/schema_contract.py       (FieldSpec 9 locked keys per §5A.C)
 *
 * All shapes are mfe-onboarding-PRIVATE (single consumer, SP05 D32).
 * Do NOT promote to @mesell/core until a second remote consumes them.
 *
 * Wave 6 · Wave B · lane 2 — authored by meesell-angular-service-builder.
 */

// ─────────────────────────────────────────────────────────────────────────────
// FieldSpec — 9 locked keys per §5A.C (schema_contract.py lines 77-102)
// §5A.C: total=False → optional keys; forward-compat keys may appear at runtime.
// ─────────────────────────────────────────────────────────────────────────────

/** 8 data_type values (schema_contract.py DATA_TYPE). */
export type FieldDataType =
  | 'text'
  | 'long_text'
  | 'number'
  | 'number_with_unit'
  | 'currency'
  | 'dropdown'
  | 'image'
  | 'address';

/** 11 primitive renderer values (schema_contract.py PRIMITIVE). */
export type FieldPrimitive =
  | 'text_short'
  | 'text_long'
  | 'number'
  | 'number_with_unit'
  | 'currency'
  | 'dropdown_small'
  | 'dropdown_medium'
  | 'dropdown_large'
  | 'dropdown_api_search'
  | 'image_upload'
  | 'address_group';

/** 2 marker values (schema_contract.py FIELD_MARKER). */
export type FieldMarker = 'compulsory' | 'optional';

/** 3 enum_resolver values (schema_contract.py ENUM_RESOLVER). */
export type EnumResolver = 'category' | 'static' | null;

/**
 * FieldSpec — one element of base_fields[] / extension_fields[][].
 * Keys per §5A.C (9 locked keys). Forward-compat keys use [key: string]: unknown.
 * Sourced from: backend/app/i18n/schema_contract.py FieldSpec TypedDict.
 */
export interface FieldSpec {
  /** Display label. */
  name: string;
  /** Snake-case dot-path key used in the `completed` map (e.g. "manufacturer_name"). */
  canonical_name: string;
  /** Tier marker: compulsory | optional. */
  marker: FieldMarker;
  /** Data classification (parser-time). */
  data_type: FieldDataType;
  /** Renderer primitive (renderer-time). */
  primitive: FieldPrimitive;
  /** Inline hint text for the field. */
  help_text: string;
  /** Whether to hide in the default wizard step (default false when absent). */
  is_advanced?: boolean;
  /** Controls enum population; null = free-text. */
  enum_resolver: EnumResolver;
  /** i18n validation message IDs for this field's constraints. */
  validation_message_ids: string[];
  /** Forward-compat — any additional keys from the backend shape. */
  [key: string]: unknown;
}

// ─────────────────────────────────────────────────────────────────────────────
// SellerProfile / SellerProfileResponse
// Sourced from: backend/app/modules/customer/schemas.py SellerProfileResponse
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The full seller-profile wire shape.
 * Returned by: GET /seller-profile (#7), PATCH /seller-profile (#8),
 *              PATCH /seller-profile/active-categories (#9),
 *              PATCH /seller-profile/compliance/{super_id} (#10).
 */
export interface SellerProfile {
  /** UUID string. */
  user_id: string;
  // 9 Legal Metrology fields — all nullable on the wire
  manufacturer_name: string | null;
  manufacturer_address: string | null;
  /** 6-digit Indian PIN — backend pattern ^\d{6}$. */
  manufacturer_pincode: string | null;
  packer_name: string | null;
  packer_address: string | null;
  /** 6-digit Indian PIN — backend pattern ^\d{6}$. */
  packer_pincode: string | null;
  importer_name: string | null;
  importer_address: string | null;
  /** 6-digit Indian PIN — backend pattern ^\d{6}$. */
  importer_pincode: string | null;
  /** Defaults to "India". */
  country_of_origin: string;
  /** Active sell-in super-categories. Replaced (not additive) via endpoint #9. */
  active_super_categories: string[];
  /** Per-super compliance extensions. Keyed by super_id. */
  compliance_extensions: Record<string, Record<string, unknown>>;
  /** True once the seller completes the onboarding wizard. */
  onboarding_complete: boolean;
  /** ISO 8601 datetime string. */
  created_at: string;
  /** ISO 8601 datetime string. */
  updated_at: string;
}

/** An empty/fresh SellerProfile for first-time sellers (404 on GET #7 → use this). */
export const FRESH_SELLER_PROFILE: SellerProfile = {
  user_id: '',
  manufacturer_name: null,
  manufacturer_address: null,
  manufacturer_pincode: null,
  packer_name: null,
  packer_address: null,
  packer_pincode: null,
  importer_name: null,
  importer_address: null,
  importer_pincode: null,
  country_of_origin: 'India',
  active_super_categories: [],
  compliance_extensions: {},
  onboarding_complete: false,
  created_at: '',
  updated_at: '',
};

// ─────────────────────────────────────────────────────────────────────────────
// PatchProfileRequest — PATCH #8 body (all optional, subset semantics)
// extra="forbid" on backend — ONLY send fields in this interface.
// Sourced from: backend/app/modules/customer/schemas.py PatchProfileRequest
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Body for PATCH /seller-profile (#8).
 * All fields optional (subset semantics). Backend: extra="forbid".
 * NEVER add fields not present here — any unknown key → 422 from the backend.
 * Pincode fields must match ^\d{6}$ or backend returns 422.
 */
export interface PatchProfileRequest {
  manufacturer_name?: string | null;
  manufacturer_address?: string | null;
  /** Must match ^\d{6}$ */
  manufacturer_pincode?: string | null;
  packer_name?: string | null;
  packer_address?: string | null;
  /** Must match ^\d{6}$ */
  packer_pincode?: string | null;
  importer_name?: string | null;
  importer_address?: string | null;
  /** Must match ^\d{6}$ */
  importer_pincode?: string | null;
  country_of_origin?: string | null;
  // active_super_categories → endpoint #9 (PatchActiveCategoriesRequest)
  // compliance_extensions  → endpoint #10 (PatchComplianceExtensionRequest)
}

// ─────────────────────────────────────────────────────────────────────────────
// PatchActiveCategoriesRequest — PATCH #9 body
// Sourced from: backend/app/modules/customer/schemas.py PatchActiveCategoriesRequest
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Body for PATCH /seller-profile/active-categories (#9).
 * REPLACES the array entirely (not additive). min_length=1 enforced by backend.
 * extra="forbid" — only this one key is accepted.
 */
export interface PatchActiveCategoriesRequest {
  /** Must have at least 1 element. */
  active_super_categories: string[];
}

// ─────────────────────────────────────────────────────────────────────────────
// RequiredFieldsResponse — GET #11
// Sourced from: backend/app/modules/customer/schemas.py RequiredFieldsResponse
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Response from GET /seller-profile/required-fields (#11).
 * Drives the onboarding wizard — same FieldSpec convention as the catalog wizard.
 *
 * `completed` keys use dot-path notation:
 *   - "manufacturer_name"              (base field)
 *   - "country_of_origin"              (base field)
 *   - "ext.26.fssai_license_number"    (Grocery extension)
 */
export interface RequiredFieldsResponse {
  /** Base profile fields per §5A.C FieldSpec contract. */
  base_fields: FieldSpec[];
  /** Extension fields keyed by super_id (empty when no active categories declared). */
  extension_fields: Record<string, FieldSpec[]>;
  /** Completion status per field canonical_name path. */
  completed: Record<string, boolean>;
}

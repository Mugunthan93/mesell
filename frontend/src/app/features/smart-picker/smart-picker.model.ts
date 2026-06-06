// features/smart-picker/smart-picker.model.ts
// Feature-private types for smart-picker per §3.G (single-feature types stay here)

export interface CategorySuggestion {
  readonly super_category: string;
  readonly leaf_category: string;
  readonly leaf_category_id: string;
  readonly confidence: number;           // 0.0 – 1.0
  readonly sample_attributes: Array<{
    canonical_name: string;
    display_label: string;
  }>;
}

export interface SuggestResponse {
  readonly suggestions: CategorySuggestion[];
  readonly fallback_offered: boolean;
}

export interface SuperCategory {
  readonly id: string;
  readonly name: string;
  readonly leaf_count: number;
}

export interface SuperCategoriesResponse {
  readonly categories: SuperCategory[];
}

export interface LeafCategory {
  readonly id: string;
  readonly name: string;
  readonly full_path: string;
}

export interface LeavesResponse {
  readonly leaves: LeafCategory[];
}

export interface CreateProductRequest {
  readonly leaf_category_id: string;
}

export interface CreateProductResponse {
  readonly id: string;
  readonly leaf_category_id: string;
  readonly status: 'draft';
  readonly created_at: string;
}

export interface ProfileIncompleteError {
  readonly detail: 'customer.profile_incomplete_for_category';
  readonly missing_super_category: string;
  readonly missing_super_name: string;
  readonly missing_compliance_fields: string[];
  readonly profile_url: string;
}

export interface BrowseSelection {
  readonly leaf_id: string;
  readonly leaf_name: string;
  readonly full_path: string;
}

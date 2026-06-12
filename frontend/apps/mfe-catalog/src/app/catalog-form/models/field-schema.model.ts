/**
 * field-schema.model.ts — Wave 6 Wave C
 *
 * Dual-layer types for the catalog-form field schema:
 *   Layer 1 — DTOs: exact wire shapes from the backend Pydantic schemas (source of truth).
 *   Layer 2 — View-model: FieldGroup[] / FieldSchema consumed by the component template.
 *
 * The adapter `adaptSchemaResponse` bridges Layer 1 → Layer 2.
 * `mapPrimitiveToWidget` maps the 11-value LOCKED primitive enum → widget hint.
 *
 * Both adapter and map are PURE FUNCTIONS — no Angular, no DI, no side effects.
 * They are unit-tested in catalog-form.model.spec.ts without TestBed.
 *
 * KEYSTONE constraint (§3, verified backend/tests/test_per_field_shape_keys.py:4-18):
 * The 9 LOCKED field keys on SchemaFieldDTO must NEVER be invented or renamed:
 *   name, canonical_name, marker, data_type, primitive, help_text,
 *   is_advanced, enum_resolver, validation_message_ids
 *
 * Grouping logic (pragmatic 3-section mapping, §3 lead resolution):
 *   marker==='compulsory'                        → group 'compulsory'
 *   marker==='optional' && !is_advanced          → group 'recommended'  (reuse "More details" section)
 *   marker==='optional' && is_advanced === true  → group 'optional'     (advanced, collapsible)
 *
 * This preserves the existing 3-section component template with zero structural churn.
 *
 * ETag note: V1 does NOT send If-None-Match. Backend returns 200+body every call.
 * 304 branch is unreachable in V1 — documented here to avoid confusion.
 *
 * GAP-1 note: No GET /products/{id} exists. category_id is obtained from navigation state
 * (Router.getCurrentNavigation().extras.state.categoryId). On hard-reload where nav-state is
 * absent, the form renders an explicit error state. This is the documented interim per spec §4.
 */

// ── Layer 1: DTOs (wire shape) ─────────────────────────────────────────────────

/**
 * SchemaFieldDTO — one element of SchemaResponseDTO.fields[].
 * The 9 LOCKED keys plus the forward-compat optional key enum_values.
 * Extra keys allowed (extra="allow" on the backend model) — ignored here.
 */
export interface SchemaFieldDTO {
  /** Human display label (the field's display label). */
  name: string;
  /** snake_case key — the form value key and the PATCH body key. */
  canonical_name: string;
  /** 'compulsory' | 'optional' — TWO values only (no 'recommended' on wire). */
  marker: 'compulsory' | 'optional';
  /** UI widget hint — e.g. 'dropdown', 'text', 'textarea'. */
  data_type: string;
  /**
   * 11-value LOCKED primitive enum (verified against backend seed data):
   *   text_short | text_long | number | currency |
   *   dropdown_small | dropdown_api_search |
   *   image_upload | toggle | date | multiselect | rating
   */
  primitive:
    | 'text_short'
    | 'text_long'
    | 'number'
    | 'currency'
    | 'dropdown_small'
    | 'dropdown_api_search'
    | 'image_upload'
    | 'toggle'
    | 'date'
    | 'multiselect'
    | 'rating';
  /** Optional hint text rendered below the field. */
  help_text?: string;
  /** True only for advanced fields (collapsed in the advanced section). */
  is_advanced: boolean;
  /**
   * 'category' — load options via GET /categories/{id}/field-enum/{name} (#16)
   * 'static'   — options are in enum_values (forward-compat key)
   * null/undefined — not a dropdown
   */
  enum_resolver?: 'category' | 'static' | null;
  /** Validation message IDs — opaque list; FE renders them as warnings (V1.5). */
  validation_message_ids?: string[];
  /** Forward-compat: static option list when enum_resolver==='static'. */
  enum_values?: string[];
}

/**
 * SchemaResponseDTO — exact wire shape from GET /api/v1/categories/{id}/schema.
 * Maps to backend category/schemas.py SchemaResponse (model_config extra="allow").
 */
export interface SchemaResponseDTO {
  /** Flat list of field descriptors — NOT pre-grouped. */
  fields: SchemaFieldDTO[];
  /** Count of compulsory fields (marker==='compulsory'). */
  compulsory_count: number;
  /** Count of optional fields (marker==='optional'). */
  optional_count: number;
  /** Total field count. */
  total_count: number;
  /** Number of wizard steps (export sheet metadata — NOT rendered by the wizard). */
  wizard_step_count: number;
  /** Export sheet column label — export-only; wizard does NOT render. */
  main_sheet_label: string;
  /** 'standard' | 'collapsed' — layout hint. */
  compliance_shape: 'standard' | 'collapsed';
}

/**
 * EnumEntryDTO — one element of FieldEnumResponseDTO.enum_entries[].
 * Wire shape from GET /api/v1/categories/{id}/field-enum/{name} (#16).
 */
export interface EnumEntryDTO {
  /** The canonical (API-safe) value to store in the product fields dict. */
  canonical: string;
  /** The Meesho-display value (may differ from canonical). */
  meesho: string;
  /** Localised label variants — FE renders the first available. */
  labels: string[];
}

/**
 * FieldEnumResponseDTO — wire shape from #16 GET /categories/{id}/field-enum/{name}.
 * Maps to backend category/schemas.py FieldEnumResponse.
 */
export interface FieldEnumResponseDTO {
  enum_entries: EnumEntryDTO[];
  total: number;
  truncated: boolean;
}

/**
 * ProductResponse — wire shape from PATCH /api/v1/products/{id} (#18).
 * Maps to backend catalog/schemas.py ProductResponse.
 */
export interface ProductResponse {
  id: string;
  catalog_id: string;
  category_id: string;
  name: string;
  status: 'draft' | 'ready';
  fields: Record<string, unknown>;
  ai_suggestions: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/**
 * ProductDraftResponse — wire shape from GET /api/v1/products/{id}/draft (#22).
 * Maps to backend catalog/schemas.py ProductDraftResponse.
 * Returns 204 (no body) when the product has never been autosaved.
 */
export interface ProductDraftResponse {
  fields: Record<string, unknown>;
  last_updated: string;
  autosave_count: number;
}

/**
 * AutofillSuggestion — one entry in AutofillResponse.suggestions[k].
 */
export interface AutofillSuggestion {
  value: unknown;
  confidence: number;  // 0..1
  source: 'ai';
}

/**
 * AutofillResponse — wire shape from POST /api/v1/products/{id}/autofill (#19).
 * Maps to backend catalog/schemas.py AutofillResponse.
 */
export interface AutofillResponse {
  suggestions: Record<string, AutofillSuggestion>;
  applied: Record<string, boolean>;
  fallback_offered: boolean;
}

// ── Layer 2: View-model (consumed by component template) ──────────────────────

/**
 * FieldSchema — the per-field view-model consumed by the component template.
 *
 * Keep legacy field names (display_name, primitive, required, enum_options)
 * so existing template bindings and spec fixtures compile without changes.
 * The adapter maps from SchemaFieldDTO → FieldSchema.
 */
export interface FieldSchema {
  /** Mapped from SchemaFieldDTO.canonical_name — the form key. */
  canonical_name: string;
  /** Mapped from SchemaFieldDTO.name — the display label. */
  display_name: string;
  /**
   * Widget hint for the template @switch.
   * Mapped via mapPrimitiveToWidget() from the 11-value wire primitive.
   * 'text_short' and 'text_long' kept for compat with existing @case bindings.
   * 'number' | 'select' | 'skip' are new.
   * 'skip' = image_upload — not rendered here (images page).
   */
  primitive: 'text_short' | 'text_long' | 'number' | 'select' | 'skip' | 'enum';
  /** True when marker==='compulsory'. */
  required: boolean;
  /** Optional hint text. */
  help_text?: string;
  /**
   * Static enum options for dropdown_small fields.
   * Populated from SchemaFieldDTO.enum_values when enum_resolver==='static'.
   * Empty for dropdown_api_search (loaded lazily via #16).
   */
  enum_options?: Array<{ label: string; value: string }>;
  /** Preserved for template compatibility. */
  max_length?: number;
  min_length?: number;
  /** True when the field should be collapsed in the advanced section. */
  is_advanced?: boolean;
  /**
   * True when this field's options must be loaded lazily via #16.
   * Present only when enum_resolver==='category'.
   */
  needs_api_enum?: boolean;
  /** The SchemaFieldDTO.canonical_name used for the field-enum #16 lookup. */
  api_enum_field_name?: string;
}

/**
 * FieldGroup — array of fields with a section label.
 * Three sections: 'compulsory' | 'recommended' | 'optional'.
 */
export interface FieldGroup {
  group: 'compulsory' | 'recommended' | 'optional';
  fields: FieldSchema[];
}

// ── Adapter: pure functions ────────────────────────────────────────────────────

/**
 * Widget type returned by mapPrimitiveToWidget.
 *
 * 'text_short'  → mee-input[type=text]      (matches existing @case in template)
 * 'text_long'   → mee-textarea              (matches existing @case in template)
 * 'number'      → mee-input[type=number]    (new @case; @default already covers this)
 * 'select'      → mee-select                (new @case for all dropdown variants)
 * 'skip'        → not rendered (image_upload — images page)
 */
export type WidgetType = 'text_short' | 'text_long' | 'number' | 'select' | 'skip';

/**
 * mapPrimitiveToWidget — maps the 11-value LOCKED wire primitive → widget hint.
 *
 * Mapping (§3 spec):
 *   text_short            → 'text_short'      (direct match — mee-input)
 *   text_long             → 'text_long'       (direct match — mee-textarea)
 *   number                → 'number'          (mee-input type=number)
 *   currency              → 'number'          (numeric input, unit at display layer)
 *   dropdown_small        → 'select'          (static options from enum_values or api-enum)
 *   dropdown_api_search   → 'select'          (async options via #16)
 *   image_upload          → 'skip'            (images page owns this)
 *   toggle                → 'select'          (yes/no as select in V1)
 *   date                  → 'text_short'      (text input; date picker V1.5)
 *   multiselect           → 'select'          (single-select in V1)
 *   rating                → 'number'          (numeric 1..5 in V1)
 *
 * Any unknown value defaults to 'text_short' for forward-compat.
 */
export function mapPrimitiveToWidget(
  primitive: SchemaFieldDTO['primitive'] | string,
): WidgetType {
  switch (primitive) {
    case 'text_short':          return 'text_short';
    case 'text_long':           return 'text_long';
    case 'number':              return 'number';
    case 'currency':            return 'number';
    case 'dropdown_small':      return 'select';
    case 'dropdown_api_search': return 'select';
    case 'image_upload':        return 'skip';
    case 'toggle':              return 'select';
    case 'date':                return 'text_short';
    case 'multiselect':         return 'select';
    case 'rating':              return 'number';
    default:                    return 'text_short';
  }
}

/**
 * adaptSchemaField — maps one SchemaFieldDTO → FieldSchema (view-model).
 *
 * - display_name  ← dto.name
 * - primitive     ← mapPrimitiveToWidget(dto.primitive)
 * - required      ← dto.marker === 'compulsory'
 * - enum_options  ← dto.enum_values mapped to {label,value} when resolver==='static'
 * - needs_api_enum ← true when enum_resolver==='category'
 */
export function adaptSchemaField(dto: SchemaFieldDTO): FieldSchema {
  const widget = mapPrimitiveToWidget(dto.primitive);

  // Static options from enum_values (forward-compat key, present when resolver==='static').
  let enum_options: Array<{ label: string; value: string }> | undefined;
  if (
    dto.enum_resolver === 'static' &&
    dto.enum_values &&
    dto.enum_values.length > 0
  ) {
    enum_options = dto.enum_values.map(v => ({ label: v, value: v }));
  }

  const needs_api_enum = dto.enum_resolver === 'category';

  const field: FieldSchema = {
    canonical_name: dto.canonical_name,
    display_name:   dto.name,
    primitive:      widget,
    required:       dto.marker === 'compulsory',
    help_text:      dto.help_text,
    is_advanced:    dto.is_advanced,
    needs_api_enum,
  };

  if (enum_options) {
    field.enum_options = enum_options;
  }

  if (needs_api_enum) {
    field.api_enum_field_name = dto.canonical_name;
  }

  return field;
}

/**
 * adaptSchemaResponse — maps SchemaResponseDTO → FieldGroup[] (3-section view-model).
 *
 * Grouping (§3 spec, lead resolution):
 *   marker==='compulsory'                       → group 'compulsory'
 *   marker==='optional' && !is_advanced         → group 'recommended'
 *   marker==='optional' && is_advanced === true → group 'optional'
 *
 * image_upload fields (primitive==='image_upload', widget==='skip') are EXCLUDED
 * from all groups — images are managed on the /images page.
 *
 * Group order: compulsory → recommended → optional.
 * Groups with zero fields are still included (empty section is correct behaviour).
 */
export function adaptSchemaResponse(dto: SchemaResponseDTO): FieldGroup[] {
  const compulsory: FieldSchema[] = [];
  const recommended: FieldSchema[] = [];
  const optional: FieldSchema[] = [];

  for (const rawField of dto.fields) {
    const widget = mapPrimitiveToWidget(rawField.primitive);
    // Skip image_upload fields — managed on /images page.
    if (widget === 'skip') continue;

    const field = adaptSchemaField(rawField);

    if (rawField.marker === 'compulsory') {
      compulsory.push(field);
    } else if (rawField.is_advanced) {
      optional.push(field);
    } else {
      recommended.push(field);
    }
  }

  return [
    { group: 'compulsory', fields: compulsory },
    { group: 'recommended', fields: recommended },
    { group: 'optional',    fields: optional },
  ];
}

// ── Legacy alias ──────────────────────────────────────────────────────────────

/**
 * SchemaResponse — legacy type alias kept for backward compat.
 * The component template still refers to `schema: FieldGroup[]`.
 */
export type SchemaResponse = FieldGroup[];

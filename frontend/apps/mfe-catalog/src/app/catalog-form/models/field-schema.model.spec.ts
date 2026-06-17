/**
 * field-schema.model.spec.ts — Wave 6 Wave C
 *
 * Pure-function unit tests for the adapter and primitive mapper.
 * Zero TestBed, zero Angular imports — runs in Vitest directly.
 *
 * Tests:
 *   adaptSchemaResponse — flat → 3-section mapping
 *     - marker=compulsory → compulsory group
 *     - marker=optional + !is_advanced → recommended group
 *     - marker=optional + is_advanced → optional group
 *     - image_upload fields excluded from all groups
 *     - empty dto.fields → 3 groups all empty
 *   adaptSchemaResponse — enum passthrough
 *     - enum_resolver=static + enum_values → enum_options populated
 *     - enum_resolver=category → needs_api_enum=true, api_enum_field_name set
 *     - no enum_resolver → no enum_options, no needs_api_enum
 *   adaptSchemaResponse — required mapping
 *     - marker=compulsory → required: true
 *     - marker=optional  → required: false
 *   mapPrimitiveToWidget — all 11 locked values
 *   Source: backend/app/i18n/schema_contract.py:175 PRIMITIVE_VALUES
 *     - text_short → text_short
 *     - text_long → text_long
 *     - number → number
 *     - number_with_unit → number
 *     - currency → number
 *     - dropdown_small → select
 *     - dropdown_medium → select
 *     - dropdown_large → select
 *     - dropdown_api_search → select
 *     - image_upload → skip
 *     - address_group → skip
 *     - unknown value → text_short (forward-compat)
 */

import { describe, it, expect } from 'vitest';
import {
  adaptSchemaResponse,
  adaptSchemaField,
  mapPrimitiveToWidget,
} from './field-schema.model';
import type { SchemaResponseDTO, SchemaFieldDTO } from './field-schema.model';

// ── Helpers ────────────────────────────────────────────────────────────────────

/**
 * makeField — construct a SchemaFieldDTO with required keys,
 * overridable via partial.
 */
function makeField(overrides: Partial<SchemaFieldDTO> & { canonical_name: string }): SchemaFieldDTO {
  return {
    name:          overrides.canonical_name.replace(/_/g, ' '),
    data_type:     'text',
    primitive:     'text_short',
    is_advanced:   false,
    marker:        'optional',
    ...overrides,
  };
}

/**
 * makeDTO — wrap a list of SchemaFieldDTOs in a minimal SchemaResponseDTO.
 */
function makeDTO(fields: SchemaFieldDTO[]): SchemaResponseDTO {
  return {
    fields,
    compulsory_count: fields.filter(f => f.marker === 'compulsory').length,
    optional_count:   fields.filter(f => f.marker === 'optional').length,
    total_count:      fields.length,
    wizard_step_count: 1,
    main_sheet_label: 'Sheet1',
    compliance_shape: 'standard',
  };
}

// ── mapPrimitiveToWidget ───────────────────────────────────────────────────────
// Source: backend/app/i18n/schema_contract.py:175 PRIMITIVE_VALUES (frozenset, 11 values).
// Emitter: backend/app/i18n/primitive_classifier.py classify_primitive().

describe('mapPrimitiveToWidget — 11 LOCKED values (schema_contract.py:175)', () => {
  it('text_short → text_short (data_type=text, fallback)', () => {
    expect(mapPrimitiveToWidget('text_short')).toBe('text_short');
  });

  it('text_long → text_long (data_type=text, long-text patterns)', () => {
    expect(mapPrimitiveToWidget('text_long')).toBe('text_long');
  });

  it('number → number (data_type=number, no unit)', () => {
    expect(mapPrimitiveToWidget('number')).toBe('number');
  });

  it('number_with_unit → number (data_type=number, unit companion or keyword)', () => {
    expect(mapPrimitiveToWidget('number_with_unit')).toBe('number');
  });

  it('currency → number (data_type=text, price/mrp patterns; ₹ prefix at display layer)', () => {
    expect(mapPrimitiveToWidget('currency')).toBe('number');
  });

  it('dropdown_small → select (enum_count 1-20, static options)', () => {
    expect(mapPrimitiveToWidget('dropdown_small')).toBe('select');
  });

  it('dropdown_medium → select (enum_count 21-100, api-enum pre-loaded)', () => {
    expect(mapPrimitiveToWidget('dropdown_medium')).toBe('select');
  });

  it('dropdown_large → select (enum_count 101-500, api-enum pre-loaded)', () => {
    expect(mapPrimitiveToWidget('dropdown_large')).toBe('select');
  });

  it('dropdown_api_search → select (enum_count >500, lazy options via #16)', () => {
    expect(mapPrimitiveToWidget('dropdown_api_search')).toBe('select');
  });

  it('image_upload → skip (images page owns this; excluded from form groups)', () => {
    expect(mapPrimitiveToWidget('image_upload')).toBe('skip');
  });

  it('address_group → skip (seller-profile composite; never a catalog primitive per primitive_classifier.py:16)', () => {
    expect(mapPrimitiveToWidget('address_group')).toBe('skip');
  });

  it('unknown value → text_short (forward-compat default)', () => {
    expect(mapPrimitiveToWidget('future_widget_type')).toBe('text_short');
  });
});

// ── adaptSchemaField ──────────────────────────────────────────────────────────

describe('adaptSchemaField — DTO → view-model mapping', () => {
  it('maps canonical_name and name (display_name) correctly', () => {
    const field = adaptSchemaField(
      makeField({ canonical_name: 'product_title', name: 'Product Title', primitive: 'text_short', marker: 'compulsory', is_advanced: false }),
    );
    expect(field.canonical_name).toBe('product_title');
    expect(field.display_name).toBe('Product Title');
  });

  it('compulsory → required: true', () => {
    const field = adaptSchemaField(makeField({ canonical_name: 'x', marker: 'compulsory' }));
    expect(field.required).toBe(true);
  });

  it('optional → required: false', () => {
    const field = adaptSchemaField(makeField({ canonical_name: 'x', marker: 'optional' }));
    expect(field.required).toBe(false);
  });

  it('static enum: enum_resolver=static + enum_values → enum_options populated', () => {
    const field = adaptSchemaField(
      makeField({
        canonical_name: 'color',
        primitive: 'dropdown_small',
        enum_resolver: 'static',
        enum_values: ['Blue', 'Red', 'Green'],
      }),
    );
    expect(field.enum_options).toEqual([
      { label: 'Blue', value: 'Blue' },
      { label: 'Red', value: 'Red' },
      { label: 'Green', value: 'Green' },
    ]);
    expect(field.needs_api_enum).toBe(false);
  });

  it('api enum: enum_resolver=category → needs_api_enum=true, api_enum_field_name set', () => {
    const field = adaptSchemaField(
      makeField({
        canonical_name: 'brand',
        primitive: 'dropdown_api_search',
        enum_resolver: 'category',
      }),
    );
    expect(field.needs_api_enum).toBe(true);
    expect(field.api_enum_field_name).toBe('brand');
    expect(field.enum_options).toBeUndefined();
  });

  it('no enum_resolver → no enum_options, no needs_api_enum', () => {
    const field = adaptSchemaField(makeField({ canonical_name: 'x', primitive: 'text_short' }));
    expect(field.enum_options).toBeUndefined();
    expect(field.needs_api_enum).toBe(false);
  });

  it('static enum with empty enum_values → no enum_options', () => {
    const field = adaptSchemaField(
      makeField({ canonical_name: 'x', primitive: 'dropdown_small', enum_resolver: 'static', enum_values: [] }),
    );
    expect(field.enum_options).toBeUndefined();
  });

  it('preserves help_text', () => {
    const field = adaptSchemaField(
      makeField({ canonical_name: 'x', help_text: 'Enter carefully' }),
    );
    expect(field.help_text).toBe('Enter carefully');
  });

  it('preserves is_advanced flag', () => {
    const field = adaptSchemaField(makeField({ canonical_name: 'x', is_advanced: true }));
    expect(field.is_advanced).toBe(true);
  });
});

// ── adaptSchemaResponse — grouping ────────────────────────────────────────────

describe('adaptSchemaResponse — flat → 3-section grouping', () => {
  it('returns exactly 3 groups in order: compulsory, recommended, optional', () => {
    const dto = makeDTO([]);
    const groups = adaptSchemaResponse(dto);
    expect(groups).toHaveLength(3);
    expect(groups[0].group).toBe('compulsory');
    expect(groups[1].group).toBe('recommended');
    expect(groups[2].group).toBe('optional');
  });

  it('empty dto.fields → 3 groups all empty', () => {
    const groups = adaptSchemaResponse(makeDTO([]));
    groups.forEach(g => expect(g.fields).toHaveLength(0));
  });

  it('compulsory marker → compulsory group', () => {
    const dto = makeDTO([
      makeField({ canonical_name: 'product_title', marker: 'compulsory', is_advanced: false }),
    ]);
    const groups = adaptSchemaResponse(dto);
    expect(groups[0].fields).toHaveLength(1);
    expect(groups[0].fields[0].canonical_name).toBe('product_title');
    expect(groups[1].fields).toHaveLength(0);
    expect(groups[2].fields).toHaveLength(0);
  });

  it('optional + !is_advanced → recommended group', () => {
    const dto = makeDTO([
      makeField({ canonical_name: 'sleeve_length', marker: 'optional', is_advanced: false }),
    ]);
    const groups = adaptSchemaResponse(dto);
    expect(groups[0].fields).toHaveLength(0);
    expect(groups[1].fields).toHaveLength(1);
    expect(groups[1].fields[0].canonical_name).toBe('sleeve_length');
    expect(groups[2].fields).toHaveLength(0);
  });

  it('optional + is_advanced=true → optional group', () => {
    const dto = makeDTO([
      makeField({ canonical_name: 'ean_code', marker: 'optional', is_advanced: true }),
    ]);
    const groups = adaptSchemaResponse(dto);
    expect(groups[0].fields).toHaveLength(0);
    expect(groups[1].fields).toHaveLength(0);
    expect(groups[2].fields).toHaveLength(1);
    expect(groups[2].fields[0].canonical_name).toBe('ean_code');
  });

  it('image_upload fields are excluded from all groups', () => {
    const dto = makeDTO([
      makeField({ canonical_name: 'hero_image', primitive: 'image_upload', marker: 'compulsory', is_advanced: false }),
      makeField({ canonical_name: 'product_title', marker: 'compulsory', is_advanced: false }),
    ]);
    const groups = adaptSchemaResponse(dto);
    // hero_image excluded; only product_title in compulsory
    expect(groups[0].fields).toHaveLength(1);
    expect(groups[0].fields[0].canonical_name).toBe('product_title');
  });

  it('mixed field set: correct distribution across all 3 groups', () => {
    const dto = makeDTO([
      makeField({ canonical_name: 'product_title', marker: 'compulsory', is_advanced: false }),
      makeField({ canonical_name: 'brand', marker: 'compulsory', is_advanced: false }),
      makeField({ canonical_name: 'sleeve_length', marker: 'optional', is_advanced: false }),
      makeField({ canonical_name: 'ean_code', marker: 'optional', is_advanced: true }),
      makeField({ canonical_name: 'hero_image', primitive: 'image_upload', marker: 'compulsory', is_advanced: false }),
    ]);
    const groups = adaptSchemaResponse(dto);
    expect(groups[0].fields).toHaveLength(2);  // product_title + brand (hero_image excluded)
    expect(groups[1].fields).toHaveLength(1);  // sleeve_length
    expect(groups[2].fields).toHaveLength(1);  // ean_code
  });

  it('preserves field order within each group', () => {
    const dto = makeDTO([
      makeField({ canonical_name: 'b', marker: 'compulsory', is_advanced: false }),
      makeField({ canonical_name: 'a', marker: 'compulsory', is_advanced: false }),
    ]);
    const groups = adaptSchemaResponse(dto);
    expect(groups[0].fields[0].canonical_name).toBe('b');
    expect(groups[0].fields[1].canonical_name).toBe('a');
  });

  it('required field true for compulsory, false for optional groups', () => {
    const dto = makeDTO([
      makeField({ canonical_name: 'c', marker: 'compulsory', is_advanced: false }),
      makeField({ canonical_name: 'r', marker: 'optional', is_advanced: false }),
      makeField({ canonical_name: 'o', marker: 'optional', is_advanced: true }),
    ]);
    const groups = adaptSchemaResponse(dto);
    expect(groups[0].fields[0].required).toBe(true);   // compulsory
    expect(groups[1].fields[0].required).toBe(false);  // recommended (optional)
    expect(groups[2].fields[0].required).toBe(false);  // optional (advanced)
  });

  it('static enum_values passthrough to recommended group', () => {
    const dto = makeDTO([
      makeField({
        canonical_name: 'color',
        marker: 'optional',
        is_advanced: false,
        primitive: 'dropdown_small',
        enum_resolver: 'static',
        enum_values: ['Blue', 'Red'],
      }),
    ]);
    const groups = adaptSchemaResponse(dto);
    expect(groups[1].fields[0].enum_options).toEqual([
      { label: 'Blue', value: 'Blue' },
      { label: 'Red', value: 'Red' },
    ]);
  });

  it('all image_upload → all groups empty', () => {
    const dto = makeDTO([
      makeField({ canonical_name: 'img1', primitive: 'image_upload', marker: 'compulsory', is_advanced: false }),
      makeField({ canonical_name: 'img2', primitive: 'image_upload', marker: 'optional', is_advanced: false }),
    ]);
    const groups = adaptSchemaResponse(dto);
    groups.forEach(g => expect(g.fields).toHaveLength(0));
  });
});

// ── Integration: adapter roundtrip ────────────────────────────────────────────

describe('adaptSchemaResponse — roundtrip integration', () => {
  const KURTI_FIELDS: SchemaFieldDTO[] = [
    makeField({ canonical_name: 'product_title', name: 'Product Title', marker: 'compulsory', is_advanced: false, primitive: 'text_short', help_text: 'Enter the full product name' }),
    makeField({ canonical_name: 'brand', name: 'Brand', marker: 'compulsory', is_advanced: false, primitive: 'dropdown_api_search', enum_resolver: 'category' }),
    makeField({ canonical_name: 'color', name: 'Color', marker: 'compulsory', is_advanced: false, primitive: 'dropdown_small', enum_resolver: 'static', enum_values: ['Blue', 'Red', 'Green'] }),
    makeField({ canonical_name: 'description', name: 'Description', marker: 'compulsory', is_advanced: false, primitive: 'text_long', help_text: 'Describe the product' }),
    makeField({ canonical_name: 'hero_image', name: 'Hero Image', marker: 'compulsory', is_advanced: false, primitive: 'image_upload' }),
    makeField({ canonical_name: 'sleeve_length', name: 'Sleeve Length', marker: 'optional', is_advanced: false, primitive: 'dropdown_small', enum_resolver: 'static', enum_values: ['Full', 'Half'] }),
    makeField({ canonical_name: 'weight_grams', name: 'Weight (grams)', marker: 'optional', is_advanced: false, primitive: 'number' }),
    makeField({ canonical_name: 'ean_code', name: 'EAN Code', marker: 'optional', is_advanced: true, primitive: 'text_short' }),
  ];

  const dto = makeDTO(KURTI_FIELDS);
  const groups = adaptSchemaResponse(dto);

  it('compulsory group has 4 fields (5 minus 1 image_upload)', () => {
    expect(groups[0].fields).toHaveLength(4);
  });

  it('recommended group has 2 fields (sleeve_length + weight)', () => {
    expect(groups[1].fields).toHaveLength(2);
  });

  it('optional group has 1 field (ean_code — advanced)', () => {
    expect(groups[2].fields).toHaveLength(1);
    expect(groups[2].fields[0].canonical_name).toBe('ean_code');
  });

  it('brand has needs_api_enum=true (dropdown_api_search)', () => {
    const brand = groups[0].fields.find(f => f.canonical_name === 'brand');
    expect(brand?.needs_api_enum).toBe(true);
    expect(brand?.api_enum_field_name).toBe('brand');
  });

  it('color has static enum_options (dropdown_small with enum_values)', () => {
    const color = groups[0].fields.find(f => f.canonical_name === 'color');
    expect(color?.enum_options).toHaveLength(3);
  });

  it('description primitive is text_long', () => {
    const desc = groups[0].fields.find(f => f.canonical_name === 'description');
    expect(desc?.primitive).toBe('text_long');
  });

  it('hero_image is NOT in any group (excluded)', () => {
    const allFields = groups.flatMap(g => g.fields);
    expect(allFields.find(f => f.canonical_name === 'hero_image')).toBeUndefined();
  });
});

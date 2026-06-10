import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import type { FieldGroup } from '../models/field-schema.model';

// Simulated 32-field Kurti schema (Wave 5 — no real HTTP until Wave 6)
const KURTI_SCHEMA: FieldGroup[] = [
  {
    group: 'compulsory',
    fields: [
      { canonical_name: 'product_title', display_name: 'Product Title', primitive: 'text_short', required: true, help_text: 'Enter the full product name' },
      { canonical_name: 'brand', display_name: 'Brand', primitive: 'text_short', required: true },
      {
        canonical_name: 'color', display_name: 'Color', primitive: 'enum', required: true,
        enum_options: [
          { label: 'Blue', value: 'Blue' }, { label: 'Red', value: 'Red' },
          { label: 'Yellow', value: 'Yellow' }, { label: 'Green', value: 'Green' },
          { label: 'Pink', value: 'Pink' }, { label: 'White', value: 'White' },
        ],
      },
      {
        canonical_name: 'material', display_name: 'Material', primitive: 'enum', required: true,
        enum_options: [
          { label: 'Cotton', value: 'Cotton' }, { label: 'Polyester', value: 'Polyester' },
          { label: 'Silk', value: 'Silk' }, { label: 'Linen', value: 'Linen' },
        ],
      },
      {
        canonical_name: 'pattern', display_name: 'Pattern', primitive: 'enum', required: true,
        enum_options: [
          { label: 'Mirror Work', value: 'Mirror Work' }, { label: 'Embroidered', value: 'Embroidered' },
          { label: 'Printed', value: 'Printed' }, { label: 'Solid', value: 'Solid' },
        ],
      },
      {
        canonical_name: 'occasion', display_name: 'Occasion', primitive: 'enum', required: true,
        enum_options: [
          { label: 'Casual', value: 'Casual' }, { label: 'Festive', value: 'Festive' },
          { label: 'Party', value: 'Party' }, { label: 'Wedding', value: 'Wedding' },
        ],
      },
      { canonical_name: 'fabric_care', display_name: 'Fabric Care', primitive: 'text_short', required: true, help_text: 'e.g. Hand wash cold' },
      { canonical_name: 'description', display_name: 'Description', primitive: 'text_long', required: true, help_text: 'Describe the product in detail' },
      {
        canonical_name: 'size_type', display_name: 'Size Type', primitive: 'enum', required: true,
        enum_options: [
          { label: 'Free Size', value: 'Free Size' }, { label: 'S', value: 'S' },
          { label: 'M', value: 'M' }, { label: 'L', value: 'L' },
          { label: 'XL', value: 'XL' }, { label: 'XXL', value: 'XXL' },
        ],
      },
      { canonical_name: 'pack_of', display_name: 'Pack Of', primitive: 'number', required: true },
      {
        canonical_name: 'country_of_origin', display_name: 'Country of Origin', primitive: 'enum', required: true,
        enum_options: [{ label: 'India', value: 'India' }],
      },
      { canonical_name: 'model_name', display_name: 'Model Name', primitive: 'text_short', required: true },
    ],
  },
  {
    group: 'recommended',
    fields: [
      {
        canonical_name: 'sleeve_length', display_name: 'Sleeve Length', primitive: 'enum', required: false,
        enum_options: [
          { label: 'Full Sleeve', value: 'Full Sleeve' }, { label: 'Half Sleeve', value: 'Half Sleeve' },
          { label: 'Sleeveless', value: 'Sleeveless' }, { label: '3/4 Sleeve', value: '3/4 Sleeve' },
        ],
      },
      {
        canonical_name: 'neck_type', display_name: 'Neck Type', primitive: 'enum', required: false,
        enum_options: [
          { label: 'Round Neck', value: 'Round Neck' }, { label: 'V-Neck', value: 'V-Neck' },
          { label: 'Boat Neck', value: 'Boat Neck' },
        ],
      },
      {
        canonical_name: 'fit_type', display_name: 'Fit Type', primitive: 'enum', required: false,
        enum_options: [
          { label: 'Regular', value: 'Regular' }, { label: 'Slim', value: 'Slim' }, { label: 'Relaxed', value: 'Relaxed' },
        ],
      },
      {
        canonical_name: 'print_type', display_name: 'Print Type', primitive: 'enum', required: false,
        enum_options: [
          { label: 'Floral', value: 'Floral' }, { label: 'Geometric', value: 'Geometric' }, { label: 'Abstract', value: 'Abstract' },
        ],
      },
      {
        canonical_name: 'closure_type', display_name: 'Closure Type', primitive: 'enum', required: false,
        enum_options: [
          { label: 'Button', value: 'Button' }, { label: 'Zip', value: 'Zip' }, { label: 'Pullover', value: 'Pullover' },
        ],
      },
      { canonical_name: 'wash_care', display_name: 'Wash Care Instructions', primitive: 'text_long', required: false },
      { canonical_name: 'weight_grams', display_name: 'Weight (grams)', primitive: 'number', required: false },
      {
        canonical_name: 'inner_lining', display_name: 'Inner Lining', primitive: 'enum', required: false,
        enum_options: [{ label: 'Yes', value: 'Yes' }, { label: 'No', value: 'No' }],
      },
      { canonical_name: 'item_height', display_name: 'Item Height (cm)', primitive: 'number', required: false },
      { canonical_name: 'item_width', display_name: 'Item Width (cm)', primitive: 'number', required: false },
    ],
  },
  {
    group: 'optional',
    fields: [
      {
        canonical_name: 'fragrance', display_name: 'Fragrance', primitive: 'enum', required: false,
        enum_options: [{ label: 'Yes', value: 'Yes' }, { label: 'No', value: 'No' }],
      },
      {
        canonical_name: 'sustainable_material', display_name: 'Sustainable Material', primitive: 'enum', required: false,
        enum_options: [{ label: 'Yes', value: 'Yes' }, { label: 'No', value: 'No' }],
      },
      { canonical_name: 'frill_detail', display_name: 'Frill Detail', primitive: 'text_short', required: false },
      { canonical_name: 'embroidery_detail', display_name: 'Embroidery Detail', primitive: 'text_short', required: false },
      {
        canonical_name: 'dupatta_included', display_name: 'Dupatta Included', primitive: 'enum', required: false,
        enum_options: [{ label: 'Yes', value: 'Yes' }, { label: 'No', value: 'No' }],
      },
      { canonical_name: 'waist_band', display_name: 'Waist Band', primitive: 'text_short', required: false },
      { canonical_name: 'hem_detail', display_name: 'Hem Detail', primitive: 'text_short', required: false },
      { canonical_name: 'sleeve_detail', display_name: 'Sleeve Detail', primitive: 'text_short', required: false },
      { canonical_name: 'back_detail', display_name: 'Back Detail', primitive: 'text_short', required: false },
      { canonical_name: 'additional_material', display_name: 'Additional Material', primitive: 'text_short', required: false },
    ],
  },
];

const AUTOFILL_RESPONSE: Record<string, unknown> = {
  product_title: 'Blue Cotton Kurti — Mirror Work',
  brand: 'Generic',
  color: 'Blue',
  material: 'Cotton',
  pattern: 'Mirror Work',
  occasion: 'Casual',
  fabric_care: 'Hand wash cold',
  description: 'Beautiful blue cotton kurti with intricate mirror work, perfect for casual and festive occasions.',
};

@Injectable()
export class CatalogFormApiService {
  getSchema(_categoryId: string): Observable<FieldGroup[]> {
    return of(KURTI_SCHEMA).pipe(delay(800));
  }

  autosave(_productId: string, _fields: Record<string, unknown>): Observable<null> {
    return of(null).pipe(delay(300));
  }

  autofill(_productId: string): Observable<Record<string, unknown>> {
    return of(AUTOFILL_RESPONSE).pipe(delay(2000));
  }
}

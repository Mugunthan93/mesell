/**
 * Feature-local field schema types for the Catalog Form.
 * These match the expected API contract from GET /api/v1/categories/{id}/schema.
 * TODO(cross-cutting): reconcile with core models once backend schema is stable.
 */

export interface FieldSchema {
  canonical_name: string;
  display_name: string;
  primitive: 'text_short' | 'text_long' | 'number' | 'enum';
  required: boolean;
  help_text?: string;
  enum_options?: Array<{ label: string; value: string }>;
  max_length?: number;
  min_length?: number;
}

export interface FieldGroup {
  group: 'compulsory' | 'recommended' | 'optional';
  fields: FieldSchema[];
}

export type SchemaResponse = FieldGroup[];

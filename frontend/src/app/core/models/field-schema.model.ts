// core/models/field-schema.model.ts
// Mirrors the three-layer schema_jsonb shape from MVP §5.6.1 — DISPLAY + CANONICAL layers only.
// The meesho_* layer is stripped by the backend per Philosophy F1 and never reaches the frontend.

import { LocaleMap } from './locale-map.model';
import { PrimitiveKind } from '@shared/enums/primitive-kind.enum';
import { StepId } from '@shared/enums/step-id.enum';

export interface FieldSchema {
  readonly canonicalName: string;
  readonly dataType: 'text' | 'number' | 'dropdown' | 'image_url' | 'date' | 'boolean';
  /** One of the 11 primitive identifiers */
  readonly primitive: PrimitiveKind;
  readonly marker: 'compulsory' | 'optional';
  readonly isAdvanced: boolean;
  readonly isHidden: boolean;
  /** One of the 13 wizard step IDs */
  readonly stepId: StepId;
  readonly maxLength: number | null;
  readonly minLength: number | null;
  readonly regex: string | null;
  readonly minValue: number | null;
  readonly maxValue: number | null;
  readonly unitSuffix: string | null;
  readonly displayLabel: LocaleMap;
  readonly displayHelp: LocaleMap | null;
  readonly displayPlaceholder: LocaleMap | null;
  readonly displayUnitLabel: LocaleMap | null;
  readonly validationMessage: LocaleMap | null;
  readonly helpUrl: string | null;
  // meesho_column_header, meesho_column_index, enum_codes_map — NEVER present per Philosophy M10 + F1
}

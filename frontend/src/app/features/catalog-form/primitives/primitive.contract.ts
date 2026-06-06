// features/catalog-form/primitives/primitive.contract.ts
// Contract for all 11 primitive input components per §18.D

import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';

export interface PrimitiveInputs {
  readonly schema: FieldSchema;
  readonly value: unknown;
  readonly aiSuggestion: AiSuggestion | null;
  readonly disabled: boolean;
}

export interface ValueChange {
  readonly canonicalName: string;
  readonly value: unknown;
  readonly source: 'seller' | 'ai-accept';
}

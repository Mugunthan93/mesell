// features/catalog-form/wizard-renderer/step-composer.service.ts
// Groups schema fields by step_id, sorts by canonical order per §18.F + MVP §5.6.3

import { Injectable } from '@angular/core';
import { FieldSchema } from '@core/models/field-schema.model';
import { LocaleMap } from '@core/models/locale-map.model';
import { StepId, STEP_ORDER } from '@shared/enums/step-id.enum';
import { WizardStep } from './wizard-renderer.component';

const STEP_TITLES: Record<StepId, LocaleMap> = {
  basics:      { en: 'Tell us about your product' },
  pricing:     { en: 'Set your price' },
  inventory:   { en: 'Stock and weight' },
  sizing:      { en: 'Sizing' },
  materials:   { en: 'Materials and pattern' },
  food:        { en: 'Food details' },
  tech_specs:  { en: 'Specifications' },
  safety:      { en: 'Safety information' },
  warranty:    { en: 'Warranty' },
  compliance:  { en: 'Your seller details' },
  photos:      { en: 'Add photos' },
  description: { en: 'Description (optional)' },
  advanced:    { en: 'Advanced fields' },
};

@Injectable()
export class StepComposerService {
  /** Groups fields by step_id, drops empty steps, sorts by canonical order */
  compose(fields: readonly FieldSchema[]): WizardStep[] {
    const grouped = fields.reduce<Partial<Record<StepId, FieldSchema[]>>>((acc, field) => {
      const stepId = field.stepId;
      if (!acc[stepId]) acc[stepId] = [];
      acc[stepId]!.push(field);
      return acc;
    }, {});

    return STEP_ORDER
      .filter(stepId => (grouped[stepId]?.length ?? 0) > 0)
      .map(stepId => ({
        id: stepId,
        title: STEP_TITLES[stepId],
        fields: grouped[stepId] ?? [],
      }));
  }
}

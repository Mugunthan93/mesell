// step-composer.service.spec.ts — 3 tests: filters hidden, orders by STEP_ORDER, drops empty steps

import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';
import { StepComposerService } from './step-composer.service';
import { FieldSchema } from '@core/models/field-schema.model';

function makeField(overrides: Partial<FieldSchema>): FieldSchema {
  return {
    canonicalName: 'test_field',
    dataType: 'text',
    primitive: 'text_short',
    marker: 'optional',
    isAdvanced: false,
    isHidden: false,
    stepId: 'basics',
    maxLength: null,
    minLength: null,
    regex: null,
    minValue: null,
    maxValue: null,
    unitSuffix: null,
    displayLabel: { en: 'Test' },
    displayHelp: null,
    displayPlaceholder: null,
    displayUnitLabel: null,
    validationMessage: null,
    helpUrl: null,
    ...overrides,
  };
}

describe('StepComposerService', () => {
  let service: StepComposerService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [StepComposerService],
    });
    service = TestBed.inject(StepComposerService);
  });

  it('should filter out hidden fields', () => {
    const fields: FieldSchema[] = [
      makeField({ canonicalName: 'visible', isHidden: false }),
      makeField({ canonicalName: 'hidden', isHidden: true }),
    ];
    const steps = service.compose(fields);
    const allFields = steps.flatMap(s => s.fields);
    expect(allFields.find(f => f.canonicalName === 'hidden')).toBeUndefined();
    expect(allFields.find(f => f.canonicalName === 'visible')).toBeDefined();
  });

  it('should order steps by STEP_ORDER', () => {
    const fields: FieldSchema[] = [
      makeField({ canonicalName: 'price', stepId: 'pricing' }),
      makeField({ canonicalName: 'name', stepId: 'basics' }),
      makeField({ canonicalName: 'weight', stepId: 'inventory' }),
    ];
    const steps = service.compose(fields);
    const stepIds = steps.map(s => s.id);
    expect(stepIds).toEqual(['basics', 'pricing', 'inventory']);
  });

  it('should drop step groups that are empty after hidden filtering', () => {
    const fields: FieldSchema[] = [
      makeField({ canonicalName: 'name', stepId: 'basics', isHidden: false }),
      makeField({ canonicalName: 'hidden_price', stepId: 'pricing', isHidden: true }),
    ];
    const steps = service.compose(fields);
    const stepIds = steps.map(s => s.id);
    expect(stepIds).toContain('basics');
    expect(stepIds).not.toContain('pricing');
  });
});

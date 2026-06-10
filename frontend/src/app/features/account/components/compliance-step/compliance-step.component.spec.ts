// features/account/components/compliance-step/compliance-step.component.spec.ts
// Tests for ComplianceStepComponent — dynamic reactive form from FieldSpec[].
//
// Pattern: Vitest + Angular TestBed (zoneless) + vi.fn() mocks.
// TranslocoTestingModule.forRoot() in imports[] (not providers[]).
// provideAnimationsAsync('noop') suppresses animation overhead.
//
// NOTE on @Input + ngOnChanges in zoneless TestBed:
// Setting plain @Input() properties directly on componentInstance does NOT trigger
// ngOnChanges in zoneless TestBed. Use fixture.componentRef.setInput('name', value)
// which correctly fires ngOnChanges and builds the FormGroup.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { describe, it, expect, vi } from 'vitest';

import {
  ComplianceStepComponent,
  FieldSpec,
} from './compliance-step.component';

// ── Test fixture data ──

const GROCERY_FIELDS: FieldSpec[] = [
  {
    field_name: 'fssai_license_number',
    display_name: 'FSSAI License Number',
    display_help:
      'Your FSSAI licence issued by the Food Safety and Standards Authority of India.',
    field_type: 'text',
    required: true,
    options: null,
  },
  {
    field_name: 'fssai_expiry',
    display_name: 'FSSAI Expiry Date',
    display_help: 'Expiry date on your FSSAI certificate.',
    field_type: 'date',
    required: false,
    options: null,
  },
];

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'onboarding.compliance.title': '{{category}} Compliance',
      'onboarding.compliance.fieldRequired': 'This field is required',
      'onboarding.compliance.save': 'Save & Continue',
      'onboarding.actions.back': 'Back',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

// ── Shared setup helper ──

async function createComponent(
  superCategoryId = '26',
  fields: FieldSpec[] = GROCERY_FIELDS,
) {
  await TestBed.configureTestingModule({
    imports: [
      ComplianceStepComponent,
      TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
    ],
    providers: [
      provideExperimentalZonelessChangeDetection(),
      provideAnimationsAsync('noop'),
    ],
  }).compileComponents();

  const fixture = TestBed.createComponent(ComplianceStepComponent);

  // Use setInput() for plain @Input() properties in zoneless TestBed.
  // This correctly triggers ngOnChanges (unlike direct property assignment on componentInstance).
  fixture.componentRef.setInput('superCategoryId', superCategoryId);
  fixture.componentRef.setInput('fields', fields);

  fixture.detectChanges();
  await fixture.whenStable();

  return { fixture, component: fixture.componentInstance };
}

// ── Tests ──

describe('ComplianceStepComponent', () => {
  // Test 1: Component creates successfully when required inputs are provided.
  it('should create', async () => {
    const { component } = await createComponent();
    expect(component).toBeTruthy();
  });

  // Test 2: ngOnChanges builds FormGroup controls from the fields input.
  it('should build form controls from fields input', async () => {
    const { component } = await createComponent('26', GROCERY_FIELDS);

    // ngOnChanges fires via setInput → detectChanges — form must be built.
    expect(component.form).toBeDefined();
    expect(component.form.contains('fssai_license_number')).toBe(true);
    expect(component.form.contains('fssai_expiry')).toBe(true);
  });

  // Test 3: onSubmit() emits formSubmit with form values when the form is valid.
  it('should emit formSubmit with form values when form is valid', async () => {
    const { component } = await createComponent('26', GROCERY_FIELDS);

    // Spy on the EventEmitter's emit method.
    const emitSpy = vi.spyOn(component.formSubmit, 'emit');

    // Fill required field; optional field left null.
    component.form.setValue({
      fssai_license_number: '12345678901234',
      fssai_expiry: null,
    });

    component.onSubmit();

    expect(emitSpy).toHaveBeenCalledOnce();
    expect(emitSpy).toHaveBeenCalledWith({
      fssai_license_number: '12345678901234',
      fssai_expiry: null,
    });
  });

  // Test 4: onSubmit() marks all as touched and does NOT emit when form is invalid.
  it('should mark all as touched and NOT emit when form is invalid', async () => {
    const { component } = await createComponent('26', GROCERY_FIELDS);

    const emitSpy = vi.spyOn(component.formSubmit, 'emit');

    // Required field starts as null (no completed[] entry for it) — form is invalid.
    expect(component.form.get('fssai_license_number')?.value).toBeNull();
    expect(component.form.invalid).toBe(true);

    component.onSubmit();

    // Emit must NOT have fired.
    expect(emitSpy).not.toHaveBeenCalled();

    // All controls must be touched so validation messages appear in the template.
    expect(component.form.get('fssai_license_number')?.touched).toBe(true);
    expect(component.form.touched).toBe(true);
  });
});

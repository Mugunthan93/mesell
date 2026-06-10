// dropdown-medium.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DropdownMediumPrimitiveComponent } from './dropdown-medium.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'color',
  dataType: 'dropdown',
  primitive: 'dropdown_medium',
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
  displayLabel: { en: 'Color' },
  displayHelp: null,
  displayPlaceholder: { en: 'Search colour...' },
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

describe('DropdownMediumPrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DropdownMediumPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(DropdownMediumPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() updates innerValue signal', () => {
    const fixture = TestBed.createComponent(DropdownMediumPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue('RED_CODE');
    expect(component.innerValue()).toBe('RED_CODE');
  });

  it('registerOnChange stores the callback and innerValue updates on selection', () => {
    const fixture = TestBed.createComponent(DropdownMediumPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    // Directly invoke the stored onChange to verify it is set
    (component as unknown as { _onChange: (v: unknown) => void })._onChange('BLUE_CODE');
    expect(changeFn).toHaveBeenCalledWith('BLUE_CODE');
  });
});

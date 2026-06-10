// dropdown-large.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DropdownLargePrimitiveComponent } from './dropdown-large.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'brand',
  dataType: 'dropdown',
  primitive: 'dropdown_large',
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
  displayLabel: { en: 'Brand' },
  displayHelp: null,
  displayPlaceholder: { en: 'Search brand...' },
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

describe('DropdownLargePrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DropdownLargePrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(DropdownLargePrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() updates innerValue signal', () => {
    const fixture = TestBed.createComponent(DropdownLargePrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue('NIKE_CODE');
    expect(component.innerValue()).toBe('NIKE_CODE');
  });

  it('registerOnChange stores the callback correctly', () => {
    const fixture = TestBed.createComponent(DropdownLargePrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    (component as unknown as { _onChange: (v: unknown) => void })._onChange('ADIDAS_CODE');
    expect(changeFn).toHaveBeenCalledWith('ADIDAS_CODE');
  });
});

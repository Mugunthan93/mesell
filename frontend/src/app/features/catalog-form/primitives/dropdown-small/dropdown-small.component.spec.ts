// dropdown-small.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DropdownSmallPrimitiveComponent } from './dropdown-small.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { MatRadioChange } from '@angular/material/radio';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'fabric_type',
  dataType: 'dropdown',
  primitive: 'dropdown_small',
  marker: 'compulsory',
  isAdvanced: false,
  isHidden: false,
  stepId: 'materials',
  maxLength: null,
  minLength: null,
  regex: null,
  minValue: null,
  maxValue: null,
  unitSuffix: null,
  displayLabel: { en: 'Fabric Type' },
  displayHelp: null,
  displayPlaceholder: null,
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

describe('DropdownSmallPrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        DropdownSmallPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(DropdownSmallPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() updates innerValue signal', () => {
    const fixture = TestBed.createComponent(DropdownSmallPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue('COTTON');
    expect(component.innerValue()).toBe('COTTON');
  });

  it('registerOnChange stores the callback for later invocation', () => {
    const fixture = TestBed.createComponent(DropdownSmallPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    // Directly invoke onChange to verify the callback is stored
    (component as unknown as { _onChange: (v: unknown) => void })._onChange('POLYESTER');
    expect(changeFn).toHaveBeenCalledWith('POLYESTER');
  });
});

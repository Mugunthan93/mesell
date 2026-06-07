// number-with-unit.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NumberWithUnitPrimitiveComponent } from './number-with-unit.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'weight',
  dataType: 'number',
  primitive: 'number_with_unit',
  marker: 'compulsory',
  isAdvanced: false,
  isHidden: false,
  stepId: 'inventory',
  maxLength: null,
  minLength: null,
  regex: null,
  minValue: 0,
  maxValue: null,
  unitSuffix: 'kg',
  displayLabel: { en: 'Weight' },
  displayHelp: null,
  displayPlaceholder: { en: 'e.g. 0.5' },
  displayUnitLabel: { en: 'kg' },
  validationMessage: null,
  helpUrl: null,
};

describe('NumberWithUnitPrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        NumberWithUnitPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(NumberWithUnitPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() parses string to float in innerValue', () => {
    const fixture = TestBed.createComponent(NumberWithUnitPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue('1.5');
    expect(component.innerValue()).toBe(1.5);
  });

  it('registerOnChange fires with parsed number on onInput', () => {
    const fixture = TestBed.createComponent(NumberWithUnitPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    const event = { target: { value: '2.5' } } as unknown as Event;
    component.onInput(event);
    expect(changeFn).toHaveBeenCalledWith(2.5);
  });
});

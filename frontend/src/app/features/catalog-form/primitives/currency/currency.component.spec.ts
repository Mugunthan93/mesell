// currency.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CurrencyPrimitiveComponent } from './currency.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'selling_price',
  dataType: 'number',
  primitive: 'currency',
  marker: 'compulsory',
  isAdvanced: false,
  isHidden: false,
  stepId: 'pricing',
  maxLength: null,
  minLength: null,
  regex: null,
  minValue: 1,
  maxValue: null,
  unitSuffix: null,
  displayLabel: { en: 'Selling Price' },
  displayHelp: { en: 'Price shown to buyers' },
  displayPlaceholder: { en: 'e.g. 499' },
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

describe('CurrencyPrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        CurrencyPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(CurrencyPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() parses number to innerValue', () => {
    const fixture = TestBed.createComponent(CurrencyPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue(499);
    expect(component.innerValue()).toBe(499);
  });

  it('registerOnChange fires with numeric value on onInput', () => {
    const fixture = TestBed.createComponent(CurrencyPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    const event = { target: { value: '299.50' } } as unknown as Event;
    component.onInput(event);
    expect(changeFn).toHaveBeenCalledWith(299.5);
  });
});

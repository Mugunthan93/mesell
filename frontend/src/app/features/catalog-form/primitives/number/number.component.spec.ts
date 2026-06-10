// number.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NumberPrimitiveComponent } from './number.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'stock_quantity',
  dataType: 'number',
  primitive: 'number',
  marker: 'compulsory',
  isAdvanced: false,
  isHidden: false,
  stepId: 'inventory',
  maxLength: null,
  minLength: null,
  regex: null,
  minValue: 0,
  maxValue: 9999,
  unitSuffix: null,
  displayLabel: { en: 'Stock Quantity' },
  displayHelp: null,
  displayPlaceholder: { en: 'e.g. 100' },
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

describe('NumberPrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        NumberPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(NumberPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() parses string to number in innerValue', () => {
    const fixture = TestBed.createComponent(NumberPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue('42');
    expect(component.innerValue()).toBe(42);
  });

  it('registerOnChange fires with parsed number on onInput', () => {
    const fixture = TestBed.createComponent(NumberPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    const event = { target: { value: '55' } } as unknown as Event;
    component.onInput(event);
    expect(changeFn).toHaveBeenCalledWith(55);
  });
});

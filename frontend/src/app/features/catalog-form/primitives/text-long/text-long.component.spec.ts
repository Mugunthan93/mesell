// text-long.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TextLongPrimitiveComponent } from './text-long.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'product_description',
  dataType: 'text',
  primitive: 'text_long',
  marker: 'optional',
  isAdvanced: false,
  isHidden: false,
  stepId: 'description',
  maxLength: 500,
  minLength: null,
  regex: null,
  minValue: null,
  maxValue: null,
  unitSuffix: null,
  displayLabel: { en: 'Description' },
  displayHelp: { en: 'Describe your product' },
  displayPlaceholder: null,
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

describe('TextLongPrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        TextLongPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(TextLongPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() updates innerValue signal', () => {
    const fixture = TestBed.createComponent(TextLongPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue('Long description text');
    expect(component.innerValue()).toBe('Long description text');
  });

  it('registerOnChange callback fires when onInput is called', () => {
    const fixture = TestBed.createComponent(TextLongPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    const event = { target: { value: 'New text' } } as unknown as Event;
    component.onInput(event);
    expect(changeFn).toHaveBeenCalledWith('New text');
  });
});

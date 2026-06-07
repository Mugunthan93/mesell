// text-short.component.spec.ts — 3 minimum tests per dispatch spec
// Testing pattern: test class logic directly (writeValue/registerOnChange) without template
// rendering to avoid NG0950 with signal inputs in vitest+jsdom environment.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TextShortPrimitiveComponent } from './text-short.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'product_name',
  dataType: 'text',
  primitive: 'text_short',
  marker: 'compulsory',
  isAdvanced: false,
  isHidden: false,
  stepId: 'basics',
  maxLength: 100,
  minLength: null,
  regex: null,
  minValue: null,
  maxValue: null,
  unitSuffix: null,
  displayLabel: { en: 'Product Name' },
  displayHelp: null,
  displayPlaceholder: { en: 'Enter product name' },
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

describe('TextShortPrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        TextShortPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate the class', () => {
    // Create fixture and set input before any detectChanges to avoid NG0950
    const fixture = TestBed.createComponent(TextShortPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    // Component class should be instantiated
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() updates innerValue signal', () => {
    const fixture = TestBed.createComponent(TextShortPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue('Hello World');
    expect(component.innerValue()).toBe('Hello World');
  });

  it('registerOnChange callback fires when onInput is called', () => {
    const fixture = TestBed.createComponent(TextShortPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    // Call onInput with a synthetic event
    const event = { target: { value: 'Test value' } } as unknown as Event;
    component.onInput(event);
    expect(changeFn).toHaveBeenCalledWith('Test value');
  });
});

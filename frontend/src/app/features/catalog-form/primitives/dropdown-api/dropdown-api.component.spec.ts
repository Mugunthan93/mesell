// dropdown-api.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { of } from 'rxjs';
import { DropdownApiPrimitiveComponent } from './dropdown-api.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { EnumLookupService } from '../../enum-lookup.service';
import { ActivatedRoute } from '@angular/router';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'material_composition',
  dataType: 'dropdown',
  primitive: 'dropdown_api_search',
  marker: 'optional',
  isAdvanced: false,
  isHidden: false,
  stepId: 'materials',
  maxLength: null,
  minLength: null,
  regex: null,
  minValue: null,
  maxValue: null,
  unitSuffix: null,
  displayLabel: { en: 'Material' },
  displayHelp: null,
  displayPlaceholder: { en: 'Type to search...' },
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

const mockEnumLookup = {
  lookupEnum: vi.fn(() => of([])),
};

const mockRoute = {
  snapshot: { params: { id: 'cat-123' } },
};

describe('DropdownApiPrimitiveComponent', () => {
  beforeEach(async () => {
    mockEnumLookup.lookupEnum.mockReset();
    mockEnumLookup.lookupEnum.mockReturnValue(of([]));

    await TestBed.configureTestingModule({
      imports: [
        DropdownApiPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        { provide: EnumLookupService, useValue: mockEnumLookup },
        { provide: ActivatedRoute, useValue: mockRoute },
      ],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(DropdownApiPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() updates innerValue and displayText', () => {
    const fixture = TestBed.createComponent(DropdownApiPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue('COTTON_CODE');
    expect(component.innerValue()).toBe('COTTON_CODE');
  });

  it('registerOnChange stores the callback correctly', () => {
    const fixture = TestBed.createComponent(DropdownApiPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    (component as unknown as { _onChange: (v: unknown) => void })._onChange('SILK_CODE');
    expect(changeFn).toHaveBeenCalledWith('SILK_CODE');
  });
});

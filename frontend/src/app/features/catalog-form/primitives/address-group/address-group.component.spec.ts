// address-group.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AddressGroupPrimitiveComponent, AddressValue } from './address-group.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'manufacturer_address',
  dataType: 'text',
  primitive: 'address_group',
  marker: 'compulsory',
  isAdvanced: false,
  isHidden: false,
  stepId: 'compliance',
  maxLength: null,
  minLength: null,
  regex: null,
  minValue: null,
  maxValue: null,
  unitSuffix: null,
  displayLabel: { en: 'Manufacturer Address' },
  displayHelp: null,
  displayPlaceholder: null,
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

describe('AddressGroupPrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AddressGroupPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(AddressGroupPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() patches sub-fields from address object', () => {
    const fixture = TestBed.createComponent(AddressGroupPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const addr: AddressValue = {
      address_line_1: '42 Main Street',
      city: 'Tirupur',
      pincode: '641604',
    };
    component.writeValue(addr);
    expect(component.form.value).toMatchObject(addr);
  });

  it('registerOnChange stores callback and fires on _onChange call', () => {
    const fixture = TestBed.createComponent(AddressGroupPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    const changeFn = vi.fn();
    component.registerOnChange(changeFn);
    const addr: AddressValue = {
      address_line_1: '10 Park Ave',
      city: 'Coimbatore',
      pincode: '641001',
    };
    // Verify registerOnChange stores the fn by invoking it directly
    (component as unknown as { _onChange: (v: unknown) => void })._onChange(addr);
    expect(changeFn).toHaveBeenCalledWith(addr);
  });
});

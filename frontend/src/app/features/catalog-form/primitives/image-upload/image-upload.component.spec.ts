// image-upload.component.spec.ts — 3 minimum tests
// Testing class logic directly to avoid NG0950 with signal inputs in vitest+jsdom.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, beforeEach } from 'vitest';
import { ImageUploadPrimitiveComponent } from './image-upload.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { ActivatedRoute } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

const MOCK_SCHEMA: FieldSchema = {
  canonicalName: 'product_images',
  dataType: 'image_url',
  primitive: 'image_upload',
  marker: 'compulsory',
  isAdvanced: false,
  isHidden: false,
  stepId: 'photos',
  maxLength: null,
  minLength: null,
  regex: null,
  minValue: null,
  maxValue: null,
  unitSuffix: null,
  displayLabel: { en: 'Product Images' },
  displayHelp: { en: 'Upload up to 7 images' },
  displayPlaceholder: null,
  displayUnitLabel: null,
  validationMessage: null,
  helpUrl: null,
};

const mockRoute = {
  snapshot: { params: { id: 'prod-abc' } },
};

describe('ImageUploadPrimitiveComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ImageUploadPrimitiveComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
        RouterTestingModule,
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        { provide: ActivatedRoute, useValue: mockRoute },
      ],
    }).compileComponents();
  });

  it('should instantiate', () => {
    const fixture = TestBed.createComponent(ImageUploadPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('writeValue() stores string URL in innerValue', () => {
    const fixture = TestBed.createComponent(ImageUploadPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    component.writeValue('https://example.com/img.jpg');
    expect(component.innerValue()).toBe('https://example.com/img.jpg');
  });

  it('imagesUrl() computes correct images route from route params', () => {
    const fixture = TestBed.createComponent(ImageUploadPrimitiveComponent);
    fixture.componentRef.setInput('schema', MOCK_SCHEMA);
    const component = fixture.componentInstance;
    expect(component.imagesUrl()).toBe('/catalogs/prod-abc/images');
  });
});

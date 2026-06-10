// features/images/precheck-report/precheck-report.component.spec.ts
// 3 required tests:
//   1. creates successfully (smoke — no detectChanges)
//   2. buildPrecheckItems() returns 5 items (pure function — no NG0950 risk)
//   3. buildPrecheckItems() maps watermark_pass=true as pass, resolution_ok=false as fail
//
// PATTERN NOTE (from MEMORY.md Wave 2b):
//   input.required() signals in vitest+jsdom: setInput() does not propagate the value
//   to the signal before the component is fully rendered. Calling computed() that reads
//   input.required() throws NG0950 even when setInput was called beforehand.
//   CORRECT APPROACH: export the computation as a pure function and test it directly.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { describe, it, expect, beforeEach } from 'vitest';

import { PrecheckReportComponent, buildPrecheckItems } from './precheck-report.component';
import type { ProductImage } from '../images-api.service';

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'images.precheck.is_jpeg': 'JPEG format',
      'images.precheck.color_space': 'RGB color space',
      'images.precheck.resolution': 'Minimum resolution (1500×1500px)',
      'images.precheck.white_bg': 'White background',
      'images.precheck.watermark': 'No watermark',
      'images.precheck.pass': 'Pass',
      'images.precheck.fail': 'Needs attention',
      'images.precheck.processing': 'Checking...',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

const MOCK_IMAGE_MIXED: ProductImage = {
  id: 'img-001',
  product_id: 'prod-001',
  slot_index: 0,
  status: 'failed',
  gcs_url: null,
  precheck_jsonb: {
    is_jpeg: true,
    color_space: 'RGB',
    resolution_ok: false,   // FAIL
    white_bg_ok: true,
    watermark_pass: true,   // PASS
  },
  uploaded_at: '2026-06-07T00:00:00Z',
};

describe('PrecheckReportComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        PrecheckReportComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
      ],
    }).compileComponents();
  });

  // Test 1: creates (no template render — avoids NG0950 from input.required())
  it('creates the component without errors', () => {
    const fixture = TestBed.createComponent(PrecheckReportComponent);
    // Do NOT call detectChanges() — input.required() has no value yet
    expect(fixture.componentInstance).toBeTruthy();
  });

  // Test 2: buildPrecheckItems pure function returns 5 items
  it('buildPrecheckItems() returns exactly 5 check items', () => {
    const items = buildPrecheckItems(MOCK_IMAGE_MIXED);
    expect(items.length).toBe(5);
  });

  // Test 3: buildPrecheckItems correctly maps pass/fail/hint
  it('buildPrecheckItems() sets watermark_pass=true as pass and resolution_ok=false as fail with hint', () => {
    const items = buildPrecheckItems(MOCK_IMAGE_MIXED);

    const watermark = items.find(i => i.key === 'watermark_pass');
    const resolution = items.find(i => i.key === 'resolution_ok');

    expect(watermark?.value).toBe(true);
    expect(watermark?.hint).toBeNull();

    expect(resolution?.value).toBe(false);
    expect(resolution?.hint).toBe('Image must be at least 1500×1500 pixels');
  });
});

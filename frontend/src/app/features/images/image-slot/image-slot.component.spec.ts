// features/images/image-slot/image-slot.component.spec.ts
// 3 required tests:
//   1. creates successfully (smoke — no detectChanges to avoid NG0950)
//   2. imageStatusBadgeClass('ready') returns success CSS class (pure function test)
//   3. image() returns null by default (empty slot — no image input provided)
//
// PATTERN NOTE (from MEMORY.md Wave 2b):
//   input.required() + detectChanges() → NG0950 in vitest+jsdom.
//   Optional inputs (input<T>(default)) ARE accessible but setInput() doesn't
//   always propagate in this jsdom environment.
//   CORRECT APPROACH: export computation logic as pure functions and test them directly.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { describe, it, expect, beforeEach } from 'vitest';

import { ImageSlotComponent, imageStatusBadgeClass } from './image-slot.component';

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'images.slot.compulsory': 'Required — front view',
      'images.slot.optional': 'Optional',
      'images.upload.drag': 'Drag photo here or click to upload',
      'images.upload.loading': 'Uploading...',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

describe('ImageSlotComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ImageSlotComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
      ],
    }).compileComponents();
  });

  // Test 1: creates (no template render — avoids NG0950 for input.required() slotIndex)
  it('creates the component without errors', () => {
    const fixture = TestBed.createComponent(ImageSlotComponent);
    // Do NOT call detectChanges() — slotIndex input.required() has no value yet
    expect(fixture.componentInstance).toBeTruthy();
  });

  // Test 2: pure function returns success class for 'ready' status
  it('imageStatusBadgeClass("ready") returns green success CSS classes', () => {
    const cls = imageStatusBadgeClass('ready');
    expect(cls).toContain('text-[var(--mee-color-success)]');
    expect(cls).toContain('bg-green-100');
  });

  // Test 3: image() optional input returns null by default (empty slot)
  it('image() returns null by default when no image is provided', () => {
    const fixture = TestBed.createComponent(ImageSlotComponent);
    const comp = fixture.componentInstance;
    fixture.componentRef.setInput('slotIndex', 0 as const);
    // image has default of null — verify
    expect(comp.image()).toBeNull();
  });
});

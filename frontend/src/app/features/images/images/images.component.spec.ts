// features/images/images/images.component.spec.ts
// 3 required tests:
//   1. creates successfully (smoke)
//   2. canProceed is false when slot 0 is null (default)
//   3. canProceed is true when slot 0 is status='ready' and watermark_pass=true
//
// PATTERN NOTE (from MEMORY.md Dashboard Dispatch 1):
//   Use overrideComponent to replace child components that have input.required()
//   with stubs — prevents NG0950 in overlay contexts.
//   remove: { imports: [RealChild] }, add: { imports: [StubChild] }
//   is the CORRECT pattern (specifying the actual class in remove).

import {
  Component,
  ChangeDetectionStrategy,
  input,
  output,
} from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { NgxImageCompressService } from 'ngx-image-compress';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import { ImagesComponent } from './images.component';
import { ImageSlotComponent } from '../image-slot/image-slot.component';
import { PrecheckReportComponent } from '../precheck-report/precheck-report.component';
import { ImagesApiService } from '../images-api.service';
import type { ProductImage } from '../images-api.service';

// ── Stub child components with input.required() ──
// Prevents NG0950 (signal input accessed outside injection context)
// and NG0300 (multiple components matching same selector)

@Component({
  selector: 'mee-image-slot',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<div class="stub-image-slot"></div>',
})
class ImageSlotStub {
  readonly slotIndex = input.required<0 | 1 | 2 | 3>();
  readonly image = input<ProductImage | null>(null);
  readonly isCompulsory = input<boolean>(false);
  readonly uploading = input<boolean>(false);
  readonly fileDropped = output<File>();
  readonly replaceRequested = output<void>();
}

@Component({
  selector: 'mee-precheck-report',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<div class="stub-precheck-report"></div>',
})
class PrecheckReportStub {
  readonly image = input.required<ProductImage>();
}

// ── i18n ──
const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'images.title': 'Product photos',
      'images.gate.slot1_required': 'Please add your main product photo to continue',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

// ── Test data ──
const READY_IMAGE: ProductImage = {
  id: 'img-001',
  product_id: 'prod-001',
  slot_index: 0,
  status: 'ready',
  gcs_url: 'https://storage.example.com/img-001.jpg',
  precheck_jsonb: {
    is_jpeg: true,
    color_space: 'RGB',
    resolution_ok: true,
    white_bg_ok: true,
    watermark_pass: true,
  },
  uploaded_at: '2026-06-07T00:00:00Z',
};

describe('ImagesComponent', () => {
  let mockImagesApi: {
    pollImages: ReturnType<typeof vi.fn>;
    uploadImage: ReturnType<typeof vi.fn>;
    deleteImage: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    mockImagesApi = {
      pollImages: vi.fn(() => of([])),
      uploadImage: vi.fn(() => of(READY_IMAGE)),
      deleteImage: vi.fn(() => of(undefined)),
    };

    await TestBed.configureTestingModule({
      imports: [
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => 'prod-001' } },
          },
        },
        { provide: ImagesApiService, useValue: mockImagesApi },
        {
          provide: MatSnackBar,
          useValue: { open: vi.fn() },
        },
        {
          provide: MatDialog,
          useValue: {
            open: vi.fn(() => ({
              afterClosed: () => of(false),
              componentRef: { setInput: vi.fn() },
            })),
          },
        },
        {
          provide: NgxImageCompressService,
          useValue: {
            compressFile: vi.fn(() =>
              Promise.resolve('data:image/jpeg;base64,abc'),
            ),
          },
        },
      ],
    })
      // Remove real child components that have input.required() to avoid NG0300 + NG0950
      .overrideComponent(ImagesComponent, {
        remove: { imports: [ImageSlotComponent, PrecheckReportComponent] },
        add: { imports: [ImageSlotStub, PrecheckReportStub] },
      })
      .compileComponents();
  });

  // Test 1: creates
  it('creates the component', () => {
    const fixture = TestBed.createComponent(ImagesComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance).toBeTruthy();
  });

  // Test 2: canProceed false when slot 0 is null (default state)
  it('canProceed is false when slot 0 is null', () => {
    const fixture = TestBed.createComponent(ImagesComponent);
    const comp = fixture.componentInstance;
    // Default: imagesBySlot = [null, null, null, null]
    expect(comp.canProceed()).toBe(false);
  });

  // Test 3: canProceed true when slot 0 ready + watermark_pass=true
  it('canProceed is true when slot 0 has status=ready and watermark_pass=true', () => {
    const fixture = TestBed.createComponent(ImagesComponent);
    const comp = fixture.componentInstance;
    comp.imagesBySlot.set([READY_IMAGE, null, null, null]);
    expect(comp.canProceed()).toBe(true);
  });
});

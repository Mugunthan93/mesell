import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  OnDestroy,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import {
  MeeButtonComponent,
  MeeBadgeComponent,
  MeeCardComponent,
  MeeFileUploadComponent,
  MeeProgressBarComponent,
} from '../../../ui';
import type { MeeFileUploadEvent } from '../../../ui';

import {
  PageHeaderComponent,
  StatusBadgeComponent,
  LoadingSkeletonComponent,
} from '../../../shared';

import {
  buildPrecheckItems,
  slotProgress,
  computeCanContinue,
  computeActiveExpandedImage,
  toggleExpandedSlot,
  resetSlot,
  applySimulationResult,
  statusForMeeStatusBadge,
  ProductImage,
  PrecheckItem,
  PrecheckResult,
} from './image-uploader.model';

// ── Simulation data ────────────────────────────────────────────────────────────
// Journey step 7: slot 1 fails color_space_rgb (CMYK); others pass after delay.

type SimScript = {
  delayMs: number;
  precheck: PrecheckResult;
};

const SIMULATION: Record<number, SimScript> = {
  0: {
    delayMs: 2000,
    precheck: { jpeg_format: true, color_space_rgb: true,  min_resolution: true, white_bg: true, no_watermark: true },
  },
  1: {
    delayMs: 2000,
    precheck: { jpeg_format: true, color_space_rgb: false, min_resolution: true, white_bg: true, no_watermark: true },
  },
  2: {
    delayMs: 2500,
    precheck: { jpeg_format: true, color_space_rgb: true,  min_resolution: true, white_bg: true, no_watermark: true },
  },
  3: {
    delayMs: 1800,
    precheck: { jpeg_format: true, color_space_rgb: true,  min_resolution: true, white_bg: true, no_watermark: true },
  },
  4: {
    delayMs: 2000,
    precheck: { jpeg_format: true, color_space_rgb: true,  min_resolution: true, white_bg: true, no_watermark: true },
  },
  5: {
    delayMs: 2000,
    precheck: { jpeg_format: true, color_space_rgb: true,  min_resolution: true, white_bg: true, no_watermark: true },
  },
};

@Component({
  selector: 'app-image-uploader',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MeeButtonComponent,
    MeeBadgeComponent,
    MeeCardComponent,
    MeeFileUploadComponent,
    MeeProgressBarComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
    LoadingSkeletonComponent,
  ],
  template: `
    <div class="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-6">

      <!-- Page header -->
      <mee-page-header
        title="Product Images"
        subtitle="Upload up to 6 images. Each image is checked for format, color space, resolution, background, and watermarks."
      />

      <!-- Upload zone -->
      <div>
        <mee-file-upload
          accept="image/*"
          [multiple]="true"
          [max_size_mb]="5"
          label="Drop images here or click to select (JPEG · max 5 MB each)"
          (files_selected)="onFilesSelected($event)"
        />
      </div>

      <!-- Image tiles grid -->
      @if (images().length > 0) {
        <div
          class="grid grid-cols-2 sm:grid-cols-3 gap-4"
          aria-label="Uploaded image slots"
        >
          @for (img of images(); track img.slot_index) {
            <mee-card>
              <!-- Slot header -->
              <div class="flex items-center justify-between mb-2">
                <span
                  class="text-xs font-semibold uppercase tracking-wide"
                  style="color: var(--mee-color-on-surface-muted);"
                >
                  Slot {{ img.slot_index + 1 }}
                </span>
                <mee-status-badge [status]="slotDisplayStatus(img)" />
              </div>

              <!-- Thumbnail / placeholder -->
              <div
                class="w-full aspect-square rounded overflow-hidden flex items-center justify-center mb-3"
                style="background: var(--mee-color-bg);"
                [attr.aria-label]="'Image slot ' + (img.slot_index + 1)"
              >
                @if (img.gcs_url) {
                  <img
                    [src]="img.gcs_url"
                    [alt]="'Product image ' + (img.slot_index + 1)"
                    class="w-full h-full object-cover"
                  />
                } @else {
                  @if (img.status === 'pending') {
                    <mee-loading-skeleton variant="card" />
                  } @else {
                    <span
                      class="text-xs text-center px-2"
                      style="color: var(--mee-color-on-surface-muted);"
                    >
                      Processing…
                    </span>
                  }
                }
              </div>

              <!-- Progress bar -->
              <div class="mb-3">
                <mee-progress-bar [value]="slotProgressValue(img)" [show_value]="false" />
              </div>

              <!-- Per-check badge row -->
              @if (img.status !== 'pending' && img.precheck) {
                <div class="flex flex-wrap gap-1 mb-3" role="list" aria-label="Pre-check results">
                  @for (check of precheckItemsFor(img); track check.key) {
                    <span role="listitem">
                      <mee-badge
                        [value]="check.label"
                        [severity]="check.pass ? 'success' : 'danger'"
                      />
                    </span>
                  }
                </div>
              }

              <!-- Expand / collapse precheck report toggle -->
              @if (img.status !== 'pending') {
                <button
                  class="w-full text-xs underline mb-2"
                  style="min-height: 44px; color: var(--mee-color-primary); background: none; border: none; cursor: pointer;"
                  (click)="expandSlot(img.slot_index)"
                  [attr.aria-expanded]="expandedSlot() === img.slot_index"
                  [attr.aria-label]="'Toggle pre-check report for slot ' + (img.slot_index + 1)"
                >
                  {{ expandedSlot() === img.slot_index ? 'Hide report' : 'View report' }}
                </button>
              }

              <!-- Re-upload button for failed slots -->
              @if (img.status === 'fail') {
                <mee-button
                  label="Re-upload"
                  variant="secondary"
                  size="sm"
                  (clicked)="onReupload(img.slot_index)"
                />
              }
            </mee-card>
          }
        </div>
      }

      <!-- Expanded precheck report panel -->
      @if (expandedSlot() !== null) {
        @let activeImg = activeExpandedImage();
        @if (activeImg) {
          <div
            class="rounded-lg border p-4"
            style="border-color: var(--mee-color-outline); background: var(--mee-color-surface);"
            role="region"
            [attr.aria-label]="'Pre-check report for slot ' + ((expandedSlot() ?? 0) + 1)"
          >
            <h2
              class="text-sm font-semibold mb-3"
              style="color: var(--mee-color-on-surface);"
            >
              Pre-check Report — Slot {{ (expandedSlot() ?? 0) + 1 }}
            </h2>

            <table
              class="w-full text-sm"
              role="table"
              aria-label="Pre-check result table"
            >
              <thead>
                <tr>
                  <th
                    class="text-left py-1 pr-4 font-medium"
                    style="color: var(--mee-color-on-surface-muted);"
                    scope="col"
                  >Check</th>
                  <th
                    class="text-left py-1 pr-4 font-medium"
                    style="color: var(--mee-color-on-surface-muted);"
                    scope="col"
                  >Result</th>
                  <th
                    class="text-left py-1 font-medium"
                    style="color: var(--mee-color-on-surface-muted);"
                    scope="col"
                  >Fix hint</th>
                </tr>
              </thead>
              <tbody>
                @for (check of precheckItemsFor(activeImg); track check.key) {
                  <tr
                    class="border-t"
                    style="border-color: var(--mee-color-outline);"
                  >
                    <td
                      class="py-2 pr-4"
                      style="color: var(--mee-color-on-surface);"
                    >{{ check.label }}</td>
                    <td class="py-2 pr-4">
                      <mee-badge
                        [value]="check.pass ? 'PASS' : 'FAIL'"
                        [severity]="check.pass ? 'success' : 'danger'"
                      />
                    </td>
                    <td
                      class="py-2 text-xs"
                      style="color: var(--mee-color-error);"
                    >
                      @if (check.hint) {
                        {{ check.hint }}
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      }

      <!-- Continue CTA -->
      <div class="flex justify-end pt-4" style="border-top: 1px solid var(--mee-color-outline);">
        <mee-button
          label="Continue to Preview"
          variant="primary"
          [disabled]="!canContinue()"
          (clicked)="onContinue()"
        />
      </div>
    </div>
  `,
})
export class ImageUploaderComponent implements OnInit, OnDestroy {
  private readonly route      = inject(ActivatedRoute);
  private readonly router     = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  // ── State ────────────────────────────────────────────────────────────────────
  readonly images         = signal<ProductImage[]>([]);
  readonly uploading      = signal<boolean>(false);
  readonly pollingActive  = signal<boolean>(false);
  readonly expandedSlot   = signal<number | null>(null);

  // ── Computed (delegates to model pure functions) ──────────────────────────────
  readonly canContinue = computed(() => computeCanContinue(this.images()));

  readonly activeExpandedImage = computed<ProductImage | null>(() =>
    computeActiveExpandedImage(this.images(), this.expandedSlot()),
  );

  // ── Poll interval handle ─────────────────────────────────────────────────────
  private pollIntervalId: ReturnType<typeof setInterval> | null = null;

  // ── Route param ─────────────────────────────────────────────────────────────
  private productId = '';

  ngOnInit(): void {
    this.productId = this.route.snapshot.paramMap.get('id') ?? '';
  }

  ngOnDestroy(): void {
    this.clearPoll();
  }

  // ── Helpers (delegates to model pure functions) ───────────────────────────────
  precheckItemsFor(image: ProductImage): PrecheckItem[] {
    return buildPrecheckItems(image);
  }

  slotProgressValue(image: ProductImage): number {
    return slotProgress(image);
  }

  slotDisplayStatus(image: ProductImage): 'ready' | 'failed' | 'pending' {
    return statusForMeeStatusBadge(image.status);
  }

  // ── Event handlers ───────────────────────────────────────────────────────────
  onFilesSelected(event: MeeFileUploadEvent): void {
    const currentImages = this.images();
    if (currentImages.length >= 6) return;

    this.uploading.set(true);

    const fileNames = event.files.map((f, i) => f.name || `file-${i}`);
    const newSlots: ProductImage[] = event.files
      .slice(0, 6 - currentImages.length)
      .map((file, i) => ({
        id:         `slot-${currentImages.length + i}-${Date.now()}`,
        slot_index: currentImages.length + i,
        gcs_url:    URL.createObjectURL(file),
        status:     'pending' as const,
        precheck:   null,
      }));

    this.images.update(prev => [...prev, ...newSlots]);
    this.uploading.set(false);

    for (const slot of newSlots) {
      this.simulateSlot(slot.slot_index);
    }

    this.startPolling();
  }

  onReupload(slotIndex: number): void {
    this.images.update(prev => resetSlot(prev, slotIndex));
    this.simulateSlot(slotIndex);
    this.startPolling();
  }

  expandSlot(index: number): void {
    this.expandedSlot.update(current => toggleExpandedSlot(current, index));
  }

  onContinue(): void {
    void this.router.navigate(['/catalogs', this.productId, 'preview']);
  }

  // ── Simulation ───────────────────────────────────────────────────────────────
  private simulateSlot(slotIndex: number): void {
    const script = SIMULATION[slotIndex] ?? SIMULATION[0];

    setTimeout(() => {
      this.images.update(prev => applySimulationResult(prev, slotIndex, script.precheck));
    }, script.delayMs);
  }

  private startPolling(): void {
    if (this.pollIntervalId !== null) return;

    this.pollingActive.set(true);
    this.pollIntervalId = setInterval(() => {
      const anyPending = this.images().some(img => img.status === 'pending');
      if (!anyPending) {
        this.pollingActive.set(false);
        this.clearPoll();
      }
    }, 1500);
  }

  private clearPoll(): void {
    if (this.pollIntervalId !== null) {
      clearInterval(this.pollIntervalId);
      this.pollIntervalId = null;
    }
  }
}

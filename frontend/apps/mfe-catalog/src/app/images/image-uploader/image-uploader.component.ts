/**
 * ImageUploaderComponent — /catalogs/:id/images
 *
 * Standalone, OnPush page component for the Image Upload + Pre-check step (V1 Feature 5).
 *
 * ## Multipart upload flow
 *  1. Seller selects files via MeeFileUploadComponent (up to 4 slots, 1-based idx 1..4).
 *  2. For each file: ImageService.upload(productId, file, idx) is called.
 *     - 202 Accepted: image is queued; ImageService.pollImages(productId) is started.
 *     - Upload 404 (FEATURE_IMAGE_PRECHECK_ENABLED=false): feature is disabled — the
 *       upload returns EMPTY and the UI enters the disabled/empty state (featureDisabled signal).
 *     - Upload 401: AuthService.logout() + navigate('/login') — handled inside ImageService.
 *     - Other errors (402/400/5xx): slot is silently dropped (EMPTY from service).
 *
 * ## 4-slot grid (G4 fix — was 6 slots 0-based)
 *  - Maximum 4 images; slot idx is 1-based (1..4, D1-LOCKED backend CHECK constraint).
 *  - is_front = idx === 1 (first uploaded image is the product front image).
 *  - Guard: `currentImages.length >= 4` prevents over-upload.
 *
 * ## Retry semantics
 *  - Re-upload button appears for any slot with status 'failed_precheck'.
 *  - resetSlot() clears precheck/status/gcs_url; ImageService.upload() is re-called with
 *    the same slot idx; pollImages() restarts.
 *
 * ## Flag-OFF / error-path (G6/G7)
 *  - upload() returning EMPTY + no new images after all uploads = featureDisabled signal set.
 *  - listImages()/pollImages() returning {images:[]} safely renders empty grid (no crash).
 *  - Both cases render a graceful EmptyState ("Image upload is not available").
 *
 * ## Inline precheck-report table
 * The "view report" expand/collapse + precheck table are rendered directly in this template
 * (no separate PreCheckReportComponent — the report is inline per FEATURE_PLAN row-4 ruling).
 * Each row shows: check label | PASS/FAIL badge | fix-hint copy (from PRECHECK_HINTS).
 * The table is surrounded by a red border when status === 'failed_precheck'.
 */
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
import { Subscription } from 'rxjs';

import {
  MeeButtonComponent,
  MeeBadgeComponent,
  MeeCardComponent,
  MeeFileUploadComponent,
  MeeProgressBarComponent,
} from '@mesell/ui-kit';
import type { MeeFileUploadEvent } from '@mesell/ui-kit';

import {
  PageHeaderComponent,
  StatusBadgeComponent,
  LoadingSkeletonComponent,
  EmptyStateComponent,
} from '@mesell/composites';

import {
  buildPrecheckItems,
  slotProgress,
  computeCanContinue,
  computeActiveExpandedImage,
  toggleExpandedSlot,
  resetSlot,
  mapImageSummaryToProductImage,
  statusForMeeStatusBadge,
  ProductImage,
  PrecheckItem,
} from './image-uploader.model';

import { ImageService } from './image.service';

@Component({
  selector: 'app-image-uploader',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ImageService],
  imports: [
    MeeButtonComponent,
    MeeBadgeComponent,
    MeeCardComponent,
    MeeFileUploadComponent,
    MeeProgressBarComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
    LoadingSkeletonComponent,
    EmptyStateComponent,
  ],
  template: `
    <div class="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-6">

      <!-- Page header -->
      <mee-page-header
        title="Product Images"
        subtitle="Upload up to 4 images. Each image is checked for format, color space, resolution, background, and watermarks."
      />

      <!-- Feature disabled / flag-OFF state -->
      @if (featureDisabled()) {
        <mee-empty-state
          icon="image_not_supported"
          message="Image upload is not available. The image pre-check feature is currently disabled. Continue to the next step."
        />
        <div class="flex justify-end pt-4" style="border-top: 1px solid var(--mee-color-outline);">
          <mee-button
            label="Continue to Preview"
            variant="primary"
            (clicked)="onContinue()"
          />
        </div>
      } @else {

        <!-- Upload zone (hidden when 4 slots are filled) -->
        @if (images().length < 4) {
          <div>
            <mee-file-upload
              accept="image/*"
              [multiple]="true"
              [max_size_mb]="5"
              label="Drop images here or click to select (JPEG · max 5 MB each)"
              (files_selected)="onFilesSelected($event)"
            />
          </div>
        }

        <!-- Image tiles grid -->
        @if (images().length > 0) {
          <div
            class="grid grid-cols-2 sm:grid-cols-3 gap-4"
            aria-label="Uploaded image slots"
          >
            @for (img of images(); track img.slot_index) {
              <mee-card
                [style]="img.status === 'failed_precheck' ? 'border: 2px solid var(--mee-color-error);' : ''"
              >
                <!-- Slot header -->
                <div class="flex items-center justify-between mb-2">
                  <span
                    class="text-xs font-semibold uppercase tracking-wide"
                    style="color: var(--mee-color-on-surface-muted);"
                  >
                    Slot {{ img.idx }}{{ img.is_front ? ' (Front)' : '' }}
                  </span>
                  <mee-status-badge [status]="slotDisplayStatus(img)" />
                </div>

                <!-- Thumbnail / placeholder -->
                <div
                  class="w-full aspect-square rounded overflow-hidden flex items-center justify-center mb-3"
                  style="background: var(--mee-color-bg);"
                  [attr.aria-label]="'Image slot ' + img.idx"
                >
                  @if (img.gcs_url) {
                    <img
                      [src]="img.gcs_url"
                      [alt]="'Product image ' + img.idx"
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

                <!-- Per-check badge row (resolved images only) -->
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
                    [attr.aria-label]="'Toggle pre-check report for slot ' + img.idx"
                  >
                    {{ expandedSlot() === img.slot_index ? 'Hide report' : 'View report' }}
                  </button>
                }

                <!-- Re-upload button for failed_precheck slots -->
                @if (img.status === 'failed_precheck') {
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

        <!-- Expanded precheck report panel
             Inline rendering — no separate PreCheckReportComponent (FEATURE_PLAN row-4 ruling).
             Red border when status === 'failed_precheck'; fix hints shown per failing check.
        -->
        @if (expandedSlot() !== null) {
          @let activeImg = activeExpandedImage();
          @if (activeImg) {
            <div
              class="rounded-lg border p-4"
              [style]="activeImg.status === 'failed_precheck'
                ? 'border: 2px solid var(--mee-color-error); background: var(--mee-color-surface);'
                : 'border-color: var(--mee-color-outline); background: var(--mee-color-surface);'"
              role="region"
              [attr.aria-label]="'Pre-check report for slot ' + activeImg.idx"
            >
              <h2
                class="text-sm font-semibold mb-3"
                style="color: var(--mee-color-on-surface);"
              >
                Pre-check Report — Slot {{ activeImg.idx }}
                @if (activeImg.status === 'failed_precheck') {
                  <span
                    class="ml-2 text-xs font-normal"
                    style="color: var(--mee-color-error);"
                  >Fix the issues below and re-upload.</span>
                }
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

      } <!-- end @else featureDisabled -->
    </div>
  `,
})
export class ImageUploaderComponent implements OnInit, OnDestroy {
  private readonly route        = inject(ActivatedRoute);
  private readonly router       = inject(Router);
  readonly         imageService = inject(ImageService);    // public for spec injection-verify

  // ── State ────────────────────────────────────────────────────────────────────
  readonly images          = signal<ProductImage[]>([]);
  readonly uploading       = signal<boolean>(false);
  readonly pollingActive   = signal<boolean>(false);
  readonly expandedSlot    = signal<number | null>(null);
  /** True when the backend returns 404 on upload (FEATURE_IMAGE_PRECHECK_ENABLED=false) */
  readonly featureDisabled = signal<boolean>(false);

  // ── Computed (delegates to model pure functions) ──────────────────────────────
  readonly canContinue = computed(() => computeCanContinue(this.images()));

  readonly activeExpandedImage = computed<ProductImage | null>(() =>
    computeActiveExpandedImage(this.images(), this.expandedSlot()),
  );

  // ── Subscription handle (unsubscribed on destroy) ────────────────────────────
  private pollSub: Subscription | null = null;

  // ── Route param ─────────────────────────────────────────────────────────────
  private productId = '';

  ngOnInit(): void {
    this.productId = this.route.snapshot.paramMap.get('id') ?? '';
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
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

  /**
   * Called when the user selects files in the upload zone.
   * Assigns 1-based idx to each file (currentLength+1..4).
   * Calls ImageService.upload(productId, file, idx) for each file.
   * On the first successful 202, starts pollImages().
   * On upload returning EMPTY (404 flag-off or other error), no slot is added;
   * if no uploads succeed and no images exist, featureDisabled is set.
   */
  onFilesSelected(event: MeeFileUploadEvent): void {
    const currentImages = this.images();
    if (currentImages.length >= 4) return;

    this.uploading.set(true);

    const filesToUpload = event.files.slice(0, 4 - currentImages.length);
    let uploadAttemptCount = 0;
    let uploadSuccessCount = 0;

    for (let i = 0; i < filesToUpload.length; i++) {
      const file = filesToUpload[i];
      const idx = currentImages.length + i + 1;  // 1-based (1..4)
      uploadAttemptCount++;

      this.imageService.upload(this.productId, file, idx).subscribe({
        next: (resp) => {
          uploadSuccessCount++;
          // Add a pending placeholder slot mapped from the 202 response
          const placeholder: ProductImage = {
            id:         resp.image_id,
            slot_index: resp.idx - 1,     // 0-based for @for track
            idx:        resp.idx,
            gcs_url:    null,
            status:     'pending',
            precheck:   null,
            is_front:   resp.idx === 1,
          };
          this.images.update(prev => {
            const exists = prev.some(p => p.idx === resp.idx);
            return exists ? prev : [...prev, placeholder];
          });

          // Start (or restart) polling once we have at least one pending upload
          this.startPolling();
        },
        complete: () => {
          uploadAttemptCount--;
          if (uploadAttemptCount === 0) {
            this.uploading.set(false);
            // If ZERO uploads succeeded and there are still no images → feature disabled
            if (uploadSuccessCount === 0 && this.images().length === 0) {
              this.featureDisabled.set(true);
            }
          }
        },
        error: () => {
          uploadAttemptCount--;
          if (uploadAttemptCount === 0) {
            this.uploading.set(false);
          }
        },
      });
    }
  }

  onReupload(slotIndex: number): void {
    const img = this.images().find(i => i.slot_index === slotIndex);
    if (!img) return;

    this.images.update(prev => resetSlot(prev, slotIndex));

    this.imageService.upload(this.productId, new File([], `reupload-${img.idx}`), img.idx).subscribe({
      next: (resp) => {
        const placeholder: ProductImage = {
          id:         resp.image_id,
          slot_index: resp.idx - 1,
          idx:        resp.idx,
          gcs_url:    null,
          status:     'pending',
          precheck:   null,
          is_front:   resp.idx === 1,
        };
        this.images.update(prev =>
          prev.map(p => p.slot_index === placeholder.slot_index ? placeholder : p),
        );
        this.startPolling();
      },
    });
  }

  expandSlot(index: number): void {
    this.expandedSlot.update(current => toggleExpandedSlot(current, index));
  }

  onContinue(): void {
    void this.router.navigate(['/catalogs', this.productId, 'preview']);
  }

  // ── Polling (real — NOT simulation) ──────────────────────────────────────────

  /**
   * Starts a poll cycle via ImageService.pollImages().
   * The service owns the backoff schedule and hard-cap logic.
   * Each emission updates the images signal by mapping ImageSummary → ProductImage.
   * The subscription is stored so ngOnDestroy can cancel it.
   */
  private startPolling(): void {
    if (this.pollSub && !this.pollSub.closed) return;

    this.pollingActive.set(true);

    this.pollSub = this.imageService.pollImages(this.productId).subscribe({
      next: (response) => {
        if (response.images.length === 0) return;  // flag-off empty list — no update
        const mapped = response.images.map(mapImageSummaryToProductImage);
        this.images.set(mapped);
        const anyPending = mapped.some(img => img.status === 'pending');
        if (!anyPending) {
          this.pollingActive.set(false);
        }
      },
      error: () => {
        this.pollingActive.set(false);
      },
      complete: () => {
        this.pollingActive.set(false);
      },
    });
  }
}

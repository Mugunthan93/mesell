// features/images/images/images.component.ts
// Route: /catalogs/:id/images
// Orchestrator: 4-slot image uploader + precheck polling + export gate

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnDestroy,
  OnInit,
  signal,
  ViewChild,
  ElementRef,
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslocoModule } from '@jsverse/transloco';
import { NgxImageCompressService } from 'ngx-image-compress';

import { ImagesApiService, ProductImage } from '../images-api.service';
import { ImageSlotComponent } from '../image-slot/image-slot.component';
import { PrecheckReportComponent } from '../precheck-report/precheck-report.component';
import { ConfirmDialogComponent } from '@shared/components/confirm-dialog/confirm-dialog.component';

// Slot indices as a typed tuple for @for tracking
const SLOT_INDICES = [0, 1, 2, 3] as const;
type SlotIndex = 0 | 1 | 2 | 3;

@Component({
  selector: 'mee-images',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    MatSnackBarModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    TranslocoModule,
    ImageSlotComponent,
    PrecheckReportComponent,
  ],
  providers: [NgxImageCompressService],
  template: `
    <!-- Hidden file input (triggered programmatically per slot) -->
    <input
      #fileInput
      type="file"
      accept="image/*"
      class="hidden"
      aria-hidden="true"
      (change)="onFileInputChange($event)"
    />

    <div class="max-w-3xl mx-auto px-4 py-6 space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-bold text-on-surface">
          {{ 'images.title' | transloco }}
        </h1>
        <!-- Next step button: gated on canProceed() -->
        <button
          mat-flat-button
          color="primary"
          class="min-h-[44px]"
          [disabled]="!canProceed()"
          [attr.aria-disabled]="!canProceed()"
          (click)="onNext()"
        >
          Next step
        </button>
      </div>

      <!-- Gate notice when slot 0 not ready -->
      @if (!canProceed()) {
        <p class="text-sm text-[var(--mee-color-warning)]">
          {{ 'images.gate.slot1_required' | transloco }}
        </p>
      }

      <!-- 4-slot grid -->
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        @for (idx of slotIndices; track idx) {
          <mee-image-slot
            [slotIndex]="idx"
            [image]="imagesBySlot()[idx]"
            [isCompulsory]="idx === 0"
            [uploading]="uploading()[idx] ?? false"
            (fileDropped)="onFileDropped(idx, $event)"
            (replaceRequested)="onReplaceRequest(idx)"
            (click)="openFilePicker(idx)"
          />
        }
      </div>

      <!-- Precheck reports — only shown for slots with images -->
      <div class="space-y-4">
        @for (idx of slotIndices; track idx) {
          @if (imagesBySlot()[idx]; as img) {
            <mee-precheck-report [image]="img" />
          }
        }
      </div>
    </div>
  `,
})
export class ImagesComponent implements OnInit, OnDestroy {
  // ── DI ──
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly imagesApi = inject(ImagesApiService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);
  private readonly imageCompress = inject(NgxImageCompressService);

  // ── Template references ──
  @ViewChild('fileInput') private fileInputRef!: ElementRef<HTMLInputElement>;

  // ── Lifecycle ──
  private readonly destroy$ = new Subject<void>();
  private pendingSlot: SlotIndex = 0;

  // ── State signals ──
  readonly productId = signal<string>('');
  readonly imagesBySlot = signal<(ProductImage | null)[]>([null, null, null, null]);
  readonly uploading = signal<Record<number, boolean>>({});

  // ── Constants ──
  readonly slotIndices = SLOT_INDICES;

  // ── Computed ──
  readonly canProceed = computed(() => {
    const slot0 = this.imagesBySlot()[0];
    return slot0?.status === 'ready' && slot0.precheck_jsonb?.watermark_pass === true;
  });

  // ── Lifecycle hooks ──

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.productId.set(id);
    this.startPolling(id);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ── Polling ──

  private startPolling(productId: string): void {
    this.imagesApi
      .pollImages(productId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: images => this.applyImages(images),
        error: () =>
          this.snackBar.open('Failed to load image status', 'Dismiss', {
            duration: 4000,
          }),
      });
  }

  private applyImages(images: ProductImage[]): void {
    const slots: (ProductImage | null)[] = [null, null, null, null];
    for (const img of images) {
      const idx = img.slot_index;
      if (idx >= 0 && idx <= 3) {
        slots[idx] = img;
      }
    }
    this.imagesBySlot.set(slots);

    // Stop polling when all images have left 'pending'/'processing'
    const allSettled = images.every(
      img => img.status !== 'pending' && img.status !== 'processing',
    );
    if (allSettled && images.length > 0) {
      this.destroy$.next();
    }
  }

  // ── File picker ──

  openFilePicker(slotIndex: SlotIndex): void {
    this.pendingSlot = slotIndex;
    // Reset value so same file can be re-selected after a replace
    if (this.fileInputRef?.nativeElement) {
      this.fileInputRef.nativeElement.value = '';
      this.fileInputRef.nativeElement.click();
    }
  }

  onFileInputChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      void this.onFileDropped(this.pendingSlot, file);
    }
  }

  // ── Upload flow ──

  async onFileDropped(slotIndex: SlotIndex, file: File): Promise<void> {
    // 1. Read file as dataUrl for ngx-image-compress
    const dataUrl = await this.fileToDataUrl(file);

    // 2. Compress: 75% quality, 75% scale (per §12.B)
    let compressed: string;
    try {
      compressed = await this.imageCompress.compressFile(
        dataUrl,
        -2,   // orientation: -2 = auto-detect from EXIF
        75,   // ratio: 75% size reduction
        75,   // quality: 75% JPEG quality
      );
    } catch {
      this.snackBar.open('Failed to compress image. Please try again.', 'Dismiss', {
        duration: 4000,
      });
      return;
    }

    // 3. Convert compressed dataUrl to Blob
    const blob = this.dataUrlToBlob(compressed);

    // 4. Mark uploading
    this.uploading.update(prev => ({ ...prev, [slotIndex]: true }));

    // 5. Upload (no progress events — ApiClient.postMultipart returns Observable<T>)
    this.imagesApi
      .uploadImage(this.productId(), slotIndex, blob)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: uploadedImage => {
          // Update slot with returned image (status will be 'pending')
          this.imagesBySlot.update(prev => {
            const next = [...prev] as (ProductImage | null)[];
            next[slotIndex] = uploadedImage;
            return next;
          });
        },
        error: (err: unknown) => {
          const status = (err as { status?: number })?.status;
          if (status === 429) {
            this.snackBar.open(
              'Upload limit reached (20/h). Please try again later.',
              'Dismiss',
              { duration: 6000 },
            );
          } else {
            this.snackBar.open('Upload failed. Please try again.', 'Dismiss', {
              duration: 4000,
            });
          }
          this.uploading.update(prev => ({ ...prev, [slotIndex]: false }));
        },
        complete: () => {
          this.uploading.update(prev => ({ ...prev, [slotIndex]: false }));
          // Re-start polling to pick up precheck updates
          this.startPolling(this.productId());
        },
      });
  }

  // ── Replace slot ──

  onReplaceRequest(slotIndex: SlotIndex): void {
    const currentImage = this.imagesBySlot()[slotIndex];
    if (!currentImage) {
      this.openFilePicker(slotIndex);
      return;
    }

    const dialogRef = this.dialog.open(ConfirmDialogComponent);
    // ConfirmDialogComponent uses input() signals — set via componentRef.setInput()
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    dialogRef.componentRef!.setInput('title', 'Replace photo?');
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    dialogRef.componentRef!.setInput(
      'message',
      'This will permanently remove the current photo and let you upload a new one.',
    );
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    dialogRef.componentRef!.setInput('confirmLabel', 'Replace');
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    dialogRef.componentRef!.setInput('destructive', true);

    dialogRef.afterClosed().subscribe((confirmed: boolean) => {
      if (!confirmed) return;
      this.imagesApi
        .deleteImage(this.productId(), currentImage.id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            // Clear slot locally
            this.imagesBySlot.update(prev => {
              const next = [...prev] as (ProductImage | null)[];
              next[slotIndex] = null;
              return next;
            });
            // Open picker for new file
            this.openFilePicker(slotIndex);
          },
          error: () => {
            this.snackBar.open('Failed to remove photo. Please try again.', 'Dismiss', {
              duration: 4000,
            });
          },
        });
    });
  }

  // ── Navigation ──

  onNext(): void {
    void this.router.navigate(['/catalogs', this.productId(), 'preview']);
  }

  // ── Helpers ──

  private fileToDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  private dataUrlToBlob(dataUrl: string): Blob {
    const [header, data] = dataUrl.split(',');
    const mime = header.match(/:(.*?);/)?.[1] ?? 'image/jpeg';
    const byteString = atob(data);
    const ia = new Uint8Array(byteString.length);
    for (let i = 0; i < byteString.length; i++) {
      ia[i] = byteString.charCodeAt(i);
    }
    return new Blob([ia], { type: mime });
  }
}

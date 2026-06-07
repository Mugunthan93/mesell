// features/images/image-slot/image-slot.component.ts
// Selector: mee-image-slot
// 4-slot drag-drop uploader card per §12.B

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoModule } from '@jsverse/transloco';
import type { ProductImage } from '../images-api.service';

/**
 * Pure function — computes the status badge CSS classes for a given image status.
 * Exported for direct testing without component instantiation (avoids NG0950 risk).
 */
export function imageStatusBadgeClass(
  status: ProductImage['status'] | undefined,
): string {
  switch (status) {
    case 'ready':
      return 'bg-green-100 text-[var(--mee-color-success)]';
    case 'processing':
      return 'bg-yellow-50 text-[var(--mee-color-warning)]';
    case 'failed':
      return 'bg-red-50 text-[var(--mee-color-error)]';
    default:
      return 'bg-gray-100 text-gray-500';
  }
}

@Component({
  selector: 'mee-image-slot',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatProgressBarModule, MatIconModule, TranslocoModule],
  template: `
    <div
      class="relative flex flex-col items-center justify-center rounded-[var(--mee-radius-md)]
             border-2 border-dashed border-[var(--mee-color-outline)] bg-white
             min-h-[200px] cursor-pointer select-none transition-colors
             hover:border-[var(--mee-color-primary)] hover:bg-orange-50"
      [class.border-solid]="!!image()"
      role="button"
      [attr.aria-label]="isCompulsory() ? ('images.slot.compulsory' | transloco) : ('images.slot.optional' | transloco)"
      tabindex="0"
      (dragover)="$event.preventDefault()"
      (drop)="onDrop($event)"
    >
      <!-- Uploading state: indeterminate progress bar -->
      @if (uploading()) {
        <div class="absolute inset-x-0 top-0 rounded-t-[var(--mee-radius-md)] overflow-hidden">
          <mat-progress-bar mode="indeterminate" color="primary" />
        </div>
        <div class="flex flex-col items-center gap-2 p-4">
          <mat-icon class="text-[var(--mee-color-primary)]" style="font-size:36px;width:36px;height:36px;">
            cloud_upload
          </mat-icon>
          <span class="text-sm text-gray-500">{{ 'images.upload.loading' | transloco }}</span>
        </div>
      }

      <!-- Image present: thumbnail preview + status badge + replace button -->
      @else if (image()) {
        <img
          [src]="image()!.gcs_url ?? ''"
          [alt]="'Slot ' + slotIndex()"
          class="w-full h-full object-cover rounded-[var(--mee-radius-md)]"
          style="min-height:160px;"
        />
        <div
          class="absolute inset-0 flex flex-col items-end justify-between p-2
                 rounded-[var(--mee-radius-md)]"
        >
          <!-- Status badge top-right -->
          <span
            class="text-xs px-2 py-1 rounded-full font-medium"
            [class]="statusBadgeClass()"
          >{{ statusLabel() }}</span>
          <!-- Replace button bottom-right (44px touch target) -->
          <button
            type="button"
            class="min-h-[44px] min-w-[44px] flex items-center justify-center
                   bg-white/90 text-gray-700 rounded-full shadow
                   hover:bg-white active:scale-95 transition-all"
            [attr.aria-label]="'Replace image for slot ' + slotIndex()"
            (click)="$event.stopPropagation(); replaceRequested.emit()"
          >
            <mat-icon style="font-size:20px;width:20px;height:20px;">swap_horiz</mat-icon>
          </button>
        </div>
      }

      <!-- Empty state: drop zone + compulsory label -->
      @else {
        <div class="flex flex-col items-center gap-3 p-6 text-center">
          <mat-icon class="text-gray-300" style="font-size:48px;width:48px;height:48px;">
            add_photo_alternate
          </mat-icon>
          <p class="text-sm font-medium text-gray-600">
            {{ 'images.upload.drag' | transloco }}
          </p>
          @if (isCompulsory()) {
            <span
              class="text-xs px-2 py-1 rounded-full bg-orange-50
                     text-[var(--mee-color-primary)] font-medium border border-orange-200"
            >
              {{ 'images.slot.compulsory' | transloco }}
            </span>
          }
        </div>
      }

      <!-- Slot position label bottom-left -->
      <span
        class="absolute bottom-2 left-2 text-xs text-gray-400 font-medium"
        aria-hidden="true"
      >{{ slotIndex() + 1 }}/4</span>
    </div>
  `,
})
export class ImageSlotComponent {
  // ── Inputs ──
  readonly slotIndex = input.required<0 | 1 | 2 | 3>();
  readonly image = input<ProductImage | null>(null);
  readonly isCompulsory = input<boolean>(false);
  readonly uploading = input<boolean>(false);

  // ── Outputs ──
  readonly fileDropped = output<File>();
  readonly replaceRequested = output<void>();

  // ── Event handlers ──

  onDrop(event: DragEvent): void {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      this.fileDropped.emit(file);
    }
  }

  // ── Derived display helpers (delegate to pure functions) ──

  statusBadgeClass(): string {
    return imageStatusBadgeClass(this.image()?.status);
  }

  statusLabel(): string {
    const status = this.image()?.status;
    switch (status) {
      case 'ready': return 'Ready';
      case 'processing': return 'Checking...';
      case 'failed': return 'Failed';
      default: return 'Pending';
    }
  }
}

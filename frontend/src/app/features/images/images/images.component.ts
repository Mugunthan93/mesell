import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { StatusBadgeComponent } from '@shared/components/status-badge/status-badge.component';
import { ImagePrecheckResult } from '@shared/enums/image-precheck-result.enum';

interface StubImageCard {
  filename: string;
  status: ImagePrecheckResult;
}

@Component({
  selector: 'mee-image-uploader',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatIconModule, StatusBadgeComponent],
  template: `
    <!-- Page header -->
    <div style="margin-bottom: 24px;">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <span style="font-size:22px; font-weight:700; color:#1F2937;">Product Images</span>
        <button
          type="button"
          style="background:#F26B23; color:#ffffff; border:none; border-radius:8px;
                 padding:0 20px; height:40px; font-size:14px; font-weight:600;
                 cursor:pointer; min-width:44px; min-height:40px;"
        >
          Upload Images
        </button>
      </div>
      <p style="font-size:13px; color:#6B7280; margin:4px 0 0;">
        Upload and manage images for this product catalog
      </p>
    </div>

    <!-- Drop zone -->
    <div
      style="background:#ffffff; border-radius:12px; border:2px dashed #D1D5DB;
             padding:32px; text-align:center; margin-bottom:24px;"
    >
      <mat-icon style="font-size:48px; width:48px; height:48px; color:#D1D5DB;">
        cloud_upload
      </mat-icon>
      <p style="font-size:16px; font-weight:600; color:#374151; margin:12px 0 0;">
        Drag &amp; drop images here
      </p>
      <p style="font-size:12px; color:#9CA3AF; margin:8px 0;">or</p>
      <button
        type="button"
        style="background:#ffffff; color:#F26B23; border:1.5px solid #F26B23;
               border-radius:8px; padding:8px 20px; font-size:13px;
               cursor:pointer; min-height:44px;"
      >
        Browse Files
      </button>
      <p style="font-size:11px; color:#9CA3AF; margin:8px 0 0;">
        JPG, PNG up to 10MB each &middot; Min 800&times;800px &middot; White background recommended
      </p>
    </div>

    <!-- Image grid -->
    <div style="margin-top:4px;">
      <p style="font-size:14px; font-weight:600; color:#374151; margin-bottom:12px;">
        Uploaded Images (3)
      </p>
      <div
        style="display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:12px;"
      >
        @for (card of stubCards; track card.filename) {
          <div
            style="background:#ffffff; border-radius:10px; border:1px solid #E5E7EB;
                   overflow:hidden;"
          >
            <!-- Image placeholder -->
            <div
              style="height:140px;
                     background:linear-gradient(135deg, #f3f4f6, #e5e7eb);
                     display:flex; align-items:center; justify-content:center;"
            >
              <mat-icon style="font-size:40px; width:40px; height:40px; color:#D1D5DB;">
                image
              </mat-icon>
            </div>
            <!-- Card footer -->
            <div
              style="padding:8px 10px; display:flex; align-items:center;
                     justify-content:space-between; gap:4px;"
            >
              <span
                style="font-size:11px; color:#374151; white-space:nowrap;
                       overflow:hidden; text-overflow:ellipsis; min-width:0; flex:1;"
              >
                {{ card.filename }}
              </span>
              <mee-status-badge [status]="card.status" />
            </div>
          </div>
        }
      </div>
    </div>
  `,
})
export class ImageUploaderComponent {
  readonly stubCards: StubImageCard[] = [
    { filename: 'product-front.jpg', status: 'ready' },
    { filename: 'product-side.jpg', status: 'processing' },
    { filename: 'product-back.jpg', status: 'failed' },
  ];
}

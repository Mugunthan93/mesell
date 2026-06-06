import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { StatusBadgeComponent } from '@shared/components/status-badge/status-badge.component';
import { ProductStatus } from '@shared/enums/product-status.enum';

interface PreviewInfoRow {
  label: string;
  value: string;
  isStatus?: boolean;
}

@Component({
  selector: 'mee-preview',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatIconModule, StatusBadgeComponent],
  template: `
    <!-- Page header -->
    <div style="margin-bottom: 24px;">
      <span style="font-size:22px; font-weight:700; color:#1F2937;">Product Preview</span>
      <p style="font-size:13px; color:#6B7280; margin:4px 0 0;">
        See how your listing will appear on Meesho
      </p>
    </div>

    <!-- Two-column layout (responsive via container query approximation) -->
    <div
      class="preview-grid"
      style="display:grid; grid-template-columns:1fr 320px; gap:24px;"
    >
      <!-- Left column — Product info card -->
      <div
        style="background:#ffffff; border-radius:12px; padding:24px;
               box-shadow:0 1px 3px rgba(0,0,0,0.08);"
      >
        <p
          style="font-size:14px; font-weight:700; color:#374151;
                 border-bottom:1px solid #F3F4F6; padding-bottom:10px; margin-bottom:16px; margin-top:0;"
        >
          Basic Info
        </p>

        @for (row of infoRows; track row.label) {
          <div
            style="margin-bottom:14px; border-bottom:1px solid #F9FAFB; padding-bottom:14px;"
          >
            <p style="font-size:12px; color:#6B7280; margin:0 0 4px;">{{ row.label }}</p>
            @if (row.isStatus) {
              <mee-status-badge [status]="statusValue" />
            } @else {
              <p style="font-size:14px; color:#1F2937; margin:0;">{{ row.value }}</p>
            }
          </div>
        }
      </div>

      <!-- Right column — Mobile preview card -->
      <div
        style="background:#ffffff; border-radius:12px; padding:16px;
               box-shadow:0 1px 3px rgba(0,0,0,0.08);"
      >
        <p style="font-size:13px; font-weight:600; color:#374151; margin:0 0 12px;">
          Mobile Preview
        </p>

        <!-- Phone frame -->
        <div
          style="width:200px; margin:0 auto; border:2px solid #1F2937;
                 border-radius:20px; overflow:hidden; padding:8px;"
        >
          <!-- Image placeholder -->
          <div
            style="width:100%; height:200px; border-radius:10px;
                   background:linear-gradient(135deg, #f3f4f6, #e5e7eb);
                   display:flex; align-items:center; justify-content:center;"
          >
            <mat-icon style="font-size:40px; width:40px; height:40px; color:#D1D5DB;">
              image
            </mat-icon>
          </div>
          <!-- Product name + price inside frame -->
          <div style="padding:6px 2px 2px;">
            <p style="font-size:10px; color:#1F2937; margin:0; font-weight:600; line-height:1.3;">
              Cotton Kurti - Blue Floral Print - M
            </p>
            <p style="font-size:10px; color:#6B7280; margin:4px 0 0;">&#8377;&nbsp;599</p>
          </div>
        </div>

        <!-- Quality score pill -->
        <div style="text-align:center; margin-top:12px;">
          <span
            style="font-size:12px; background:#DCFCE7; color:#15803D;
                   border-radius:999px; padding:4px 12px; display:inline-block;"
          >
            Quality Score: 87/100
          </span>
        </div>
      </div>
    </div>

    <!-- Responsive stacking below 768px -->
    <style>
      @media (max-width: 767px) {
        .preview-grid {
          grid-template-columns: 1fr !important;
        }
      }
    </style>
  `,
})
export class PreviewComponent {
  readonly statusValue: ProductStatus = 'ready';

  readonly infoRows: PreviewInfoRow[] = [
    { label: 'Product Name', value: 'Cotton Kurti - Blue Floral Print - M' },
    { label: 'Category',     value: 'Women › Kurtis › Cotton Kurtis' },
    { label: 'MRP',          value: '₹ 599' },
    { label: 'Status',       value: '', isStatus: true },
  ];
}

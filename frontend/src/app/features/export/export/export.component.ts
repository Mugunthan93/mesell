// features/export/export/export.component.ts
// Visual shell — stub data only, no service injection per task scope.

import { ChangeDetectionStrategy, Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { StatusBadgeComponent } from '@shared/components/status-badge/status-badge.component';

interface ExportHistoryRow {
  date: string;
  products: string;
  status: 'ready' | 'failed';
  downloadLabel: string;
}

@Component({
  selector: 'mee-export',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatIconModule, StatusBadgeComponent],
  template: `
    <!-- Page header -->
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:24px;">
      <div>
        <h1 style="font-size:22px; font-weight:700; color:#1F2937; margin:0;">Export Catalog</h1>
        <p style="font-size:13px; color:#6B7280; margin:4px 0 0 0;">Generate Meesho-compatible CSV for upload</p>
      </div>
    </div>

    <!-- Ready-to-export summary card -->
    <div style="background:#ffffff; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08); margin-bottom:16px;">
      <div style="display:flex; align-items:center; gap:16px;">
        <div style="width:48px; height:48px; min-width:48px; background:#F0FDF4; border-radius:50%; display:flex; align-items:center; justify-content:center;">
          <mat-icon style="font-size:24px; width:24px; height:24px; color:#16A34A;">inventory_2</mat-icon>
        </div>
        <div>
          <div style="font-size:18px; font-weight:700; color:#1F2937;">8 products ready to export</div>
          <div style="font-size:13px; color:#6B7280; margin-top:2px;">All images validated · Quality score ≥ 80</div>
        </div>
      </div>
    </div>

    <!-- Warning banner -->
    <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px; padding:14px 16px; margin-bottom:16px; display:flex; gap:10px; align-items:flex-start;">
      <mat-icon style="font-size:20px; width:20px; height:20px; color:#D97706; flex-shrink:0; margin-top:1px;">warning_amber</mat-icon>
      <span style="font-size:13px; color:#92400E;">3 products are still in Draft state and will not be included.</span>
    </div>

    <!-- Export button -->
    <button
      type="button"
      style="display:flex; align-items:center; justify-content:center; gap:8px; width:100%; height:50px; background:#F26B23; color:#ffffff; border:none; border-radius:10px; font-size:16px; font-weight:700; cursor:pointer;"
    >
      <mat-icon>download</mat-icon>
      Export to Meesho CSV
    </button>

    <!-- Past exports section -->
    <div style="margin-top:32px;">
      <h2 style="font-size:16px; font-weight:700; color:#374151; margin:0 0 12px 0;">Export History</h2>

      <!-- Table card -->
      <div style="background:#ffffff; border-radius:10px; overflow:hidden;">
        <!-- Header row -->
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr 80px; background:#F9FAFB; border-bottom:1px solid #E5E7EB;">
          <div style="padding:10px 16px; font-size:11px; font-weight:700; color:#6B7280; text-transform:uppercase; letter-spacing:0.05em;">Date</div>
          <div style="padding:10px 16px; font-size:11px; font-weight:700; color:#6B7280; text-transform:uppercase; letter-spacing:0.05em;">Products</div>
          <div style="padding:10px 16px; font-size:11px; font-weight:700; color:#6B7280; text-transform:uppercase; letter-spacing:0.05em;">Status</div>
          <div style="padding:10px 16px; font-size:11px; font-weight:700; color:#6B7280; text-transform:uppercase; letter-spacing:0.05em;">Download</div>
        </div>

        <!-- Data rows -->
        @for (row of historyRows; track row.date) {
          <div style="display:grid; grid-template-columns:1fr 1fr 1fr 80px; border-bottom:1px solid #F9FAFB;">
            <div style="padding:12px 16px; font-size:14px; color:#1F2937;">{{ row.date }}</div>
            <div style="padding:12px 16px; font-size:14px; color:#1F2937;">{{ row.products }}</div>
            <div style="padding:12px 16px;">
              <mee-status-badge [status]="row.status" />
            </div>
            <div style="padding:12px 16px; font-size:14px;">
              @if (row.status === 'ready') {
                <a href="#" style="color:#F26B23; text-decoration:none; font-weight:500;">{{ row.downloadLabel }}</a>
              } @else {
                <span style="color:#9CA3AF;">—</span>
              }
            </div>
          </div>
        }
      </div>
    </div>
  `,
})
export class ExportComponent {
  readonly historyRows: ExportHistoryRow[] = [
    { date: '05 Jun 2026', products: '11 products', status: 'ready', downloadLabel: 'Download' },
    { date: '01 Jun 2026', products: '8 products', status: 'failed', downloadLabel: '—' },
  ];
}

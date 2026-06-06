// features/catalog-form/catalog-form/catalog-form.component.ts
// Route: /catalogs/:id/edit — visual shell (hardcoded stub data; no service injection)

import {
  ChangeDetectionStrategy,
  Component,
  signal,
} from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'mee-catalog-form',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatIconModule],
  template: `
    <!-- Page header -->
    <div style="display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:24px;">
      <div>
        <div style="font-size:22px; font-weight:700; color:#1F2937; line-height:1.2;">Edit Product</div>
        <div style="font-size:13px; color:#6B7280; margin-top:4px;">Cotton Kurti – Blue Floral Print</div>
      </div>
      <div style="display:flex; gap:8px; align-items:center;">
        <button type="button"
          style="border:1px solid #D1D5DB; background:#ffffff; color:#374151; padding:9px 16px; border-radius:8px; font-size:13px; cursor:pointer; line-height:1;">
          Save Draft
        </button>
        <button type="button"
          style="background:#F26B23; color:#ffffff; border:none; padding:9px 18px; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer; line-height:1;">
          Continue &rarr;
        </button>
      </div>
    </div>

    <!-- Step progress bar -->
    <div style="margin-bottom:24px;">
      <div style="display:flex; align-items:center;">
        @for (step of steps; track step.index; let i = $index) {
          <!-- Step circle + label -->
          <div style="display:flex; flex-direction:column; align-items:center; min-width:72px;">
            <div style="
              width:24px; height:24px; border-radius:50%; display:flex; align-items:center;
              justify-content:center; font-size:11px; font-weight:700;
              background:{{ step.index <= activeStep() ? '#F26B23' : '#E5E7EB' }};
              color:{{ step.index <= activeStep() ? '#ffffff' : '#9CA3AF' }};">
              {{ step.index }}
            </div>
            <div style="
              font-size:13px; margin-top:4px; white-space:nowrap;
              color:{{ step.index === activeStep() ? '#F26B23' : step.index < activeStep() ? '#6B7280' : '#9CA3AF' }};">
              {{ step.label }}
            </div>
          </div>
          <!-- Connector line (not after last step) -->
          @if (i < steps.length - 1) {
            <div style="
              flex:1; height:2px; margin-bottom:18px;
              background:{{ (i + 1) < activeStep() ? '#F26B23' : '#E5E7EB' }};">
            </div>
          }
        }
      </div>
    </div>

    <!-- Main two-column grid -->
    <div style="display:grid; grid-template-columns:1fr 320px; gap:24px;" class="catalog-form-grid">

      <!-- Left column — Form card -->
      <div style="background:#ffffff; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">

        <!-- Section: Basic Information -->
        <div style="font-size:15px; font-weight:700; color:#374151; border-bottom:1px solid #F3F4F6; padding-bottom:10px; margin-bottom:20px;">
          Basic Information
        </div>

        <!-- Field: Product Title -->
        <div style="margin-bottom:16px;">
          <label style="display:block; font-size:13px; font-weight:500; color:#374151; margin-bottom:6px;">
            Product Title <span style="color:#DC2626;">*</span>
          </label>
          <input type="text" value="Cotton Kurti - Blue Floral Print - M"
            style="width:100%; height:44px; border:1px solid #D1D5DB; border-radius:8px; padding:0 14px; font-size:14px; box-sizing:border-box; background:#F9FAFB;" />
          <p style="font-size:11px; color:#9CA3AF; margin:4px 0 0;">Max 100 characters. Be specific: fabric, color, size.</p>
        </div>

        <!-- Field: Description -->
        <div style="margin-bottom:16px;">
          <label style="display:block; font-size:13px; font-weight:500; color:#374151; margin-bottom:6px;">
            Description <span style="color:#DC2626;">*</span>
          </label>
          <textarea rows="4"
            style="width:100%; border:1px solid #D1D5DB; border-radius:8px; padding:10px 14px; font-size:14px; box-sizing:border-box; background:#F9FAFB; resize:vertical; font-family:inherit;">Lightweight cotton kurti with floral print. Available in sizes S, M, L, XL. Machine washable.</textarea>
          <p style="font-size:11px; color:#9CA3AF; margin:4px 0 0;">Describe material, fit, and care instructions.</p>
        </div>

        <!-- Field: MRP -->
        <div style="margin-bottom:16px;">
          <label style="display:block; font-size:13px; font-weight:500; color:#374151; margin-bottom:6px;">
            MRP (&#8377;) <span style="color:#DC2626;">*</span>
          </label>
          <input type="number" value="599"
            style="width:100%; height:44px; border:1px solid #D1D5DB; border-radius:8px; padding:0 14px; font-size:14px; box-sizing:border-box; background:#F9FAFB;" />
          <p style="font-size:11px; color:#9CA3AF; margin:4px 0 0;">Meesho minimum &#8377;99</p>
        </div>

        <!-- Field: Size Type -->
        <div style="margin-bottom:16px;">
          <label style="display:block; font-size:13px; font-weight:500; color:#374151; margin-bottom:6px;">
            Size Type
          </label>
          <select
            style="width:100%; height:44px; border:1px solid #D1D5DB; border-radius:8px; padding:0 14px; font-size:14px; box-sizing:border-box; background:#F9FAFB; appearance:auto;">
            <option value="Medium" selected>Medium</option>
            <option value="Small">Small</option>
            <option value="Large">Large</option>
            <option value="XL">XL</option>
            <option value="XXL">XXL</option>
          </select>
        </div>

        <!-- Section: Category -->
        <div style="font-size:15px; font-weight:700; color:#374151; border-bottom:1px solid #F3F4F6; padding-bottom:10px; margin-top:24px; margin-bottom:16px;">
          Category
        </div>

        <!-- Category read-only row -->
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <span style="
            background:#FFF3E8; color:#F26B23; border:1px solid #FDDCB5;
            border-radius:6px; padding:4px 10px; font-size:12px; font-weight:600;">
            Women / Kurtis / Cotton Kurtis
          </span>
          <span style="color:#6B7280; font-size:12px; cursor:pointer; text-decoration:underline;">Change</span>
        </div>

      </div><!-- /Left column -->

      <!-- Right column — Tips card -->
      <div style="background:#ffffff; border-radius:12px; padding:20px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">

        <div style="font-size:14px; font-weight:700; color:#374151; margin-bottom:14px;">
          &#128161; Listing Tips
        </div>

        @for (tip of tips; track tip.text) {
          <div style="display:flex; gap:10px; align-items:flex-start; margin-bottom:12px;">
            <mat-icon style="font-size:16px; width:16px; height:16px; color:#16A34A; flex-shrink:0; margin-top:1px;">check_circle</mat-icon>
            <span style="font-size:13px; color:#374151; line-height:1.4;">{{ tip.text }}</span>
          </div>
        }

        <!-- Autofill banner -->
        <div style="
          margin-top:16px; background:#EFF6FF; border-radius:8px;
          padding:12px; border:1px solid #BFDBFE;">
          <div style="font-size:13px; font-weight:600; color:#1D4ED8; margin-bottom:4px;">
            &#9889; AI Autofill available
          </div>
          <div style="font-size:12px; color:#3B82F6;">
            Paste your product description and let AI fill the form.
          </div>
          <button type="button"
            style="
              background:#1D4ED8; color:#ffffff; border:none; border-radius:6px;
              padding:6px 14px; font-size:12px; cursor:pointer; margin-top:8px; line-height:1.4;">
            Try Autofill &rarr;
          </button>
        </div>

      </div><!-- /Right column -->

    </div><!-- /grid -->
  `,
  styles: [`
    :host { display: block; }
    @media (max-width: 899px) {
      .catalog-form-grid {
        grid-template-columns: 1fr !important;
      }
    }
  `],
})
export class CatalogFormComponent {
  readonly activeStep = signal<number>(2);

  readonly steps: Array<{ index: number; label: string }> = [
    { index: 1, label: 'Category' },
    { index: 2, label: 'Product Info' },
    { index: 3, label: 'Images' },
    { index: 4, label: 'Pricing' },
  ];

  readonly tips: Array<{ text: string }> = [
    { text: 'Use specific fabric names (cotton, poly-silk)' },
    { text: 'Include size in the title' },
    { text: 'White background images get 2x views' },
    { text: 'Set competitive MRP — check similar listings' },
  ];
}

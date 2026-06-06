// features/landing/landing/landing.component.ts
// Route: / — Landing page visual shell (no service injection; hardcoded stub content)
// Rendered inside MeeAuthLayoutComponent's centered white card (max-width 440px)

import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'mee-landing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div style="padding: 32px 32px 28px;">

      <!-- Section 1: Hero -->
      <div>
        <span style="
          display: inline-block;
          background: #FFF3E8;
          color: #F26B23;
          border: 1px solid #FDDCB5;
          font-size: 11px;
          font-weight: 600;
          padding: 4px 10px;
          border-radius: 999px;
          margin-bottom: 16px;
          line-height: 1.4;
        ">&#128640; AI-powered catalog builder</span>

        <h1 style="
          font-size: 26px;
          font-weight: 800;
          color: #1F2937;
          line-height: 1.2;
          margin: 0 0 8px 0;
        ">Sell Smarter on Meesho</h1>

        <p style="
          font-size: 14px;
          color: #6B7280;
          line-height: 1.6;
          margin: 0;
        ">Create professional catalogs in minutes with AI. Quality-check images, auto-fill attributes, and export directly to Meesho.</p>
      </div>

      <!-- Section 2: CTAs -->
      <div style="margin-top: 24px;">
        <button
          [routerLink]="['/signup']"
          style="
            display: block;
            width: 100%;
            height: 46px;
            background: #F26B23;
            color: #ffffff;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            text-align: center;
            line-height: 46px;
            box-sizing: border-box;
          "
        >Get Started Free &rarr;</button>

        <button
          [routerLink]="['/login']"
          style="
            display: block;
            width: 100%;
            height: 46px;
            background: transparent;
            color: #374151;
            border: 1.5px solid #D1D5DB;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 400;
            cursor: pointer;
            text-align: center;
            margin-top: 10px;
            box-sizing: border-box;
          "
        >Already have an account? Login</button>
      </div>

      <!-- Section 3: Feature Highlights -->
      <div style="margin-top: 24px;">

        <!-- Row 1: AI Category Picker -->
        <div style="
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 10px 0;
          border-bottom: 1px solid #F3F4F6;
        ">
          <div style="
            width: 32px;
            height: 32px;
            min-width: 32px;
            background: #FFF3E8;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            line-height: 1;
          ">&#9889;</div>
          <div>
            <div style="font-size: 13px; font-weight: 600; color: #1F2937; margin-bottom: 2px;">AI Category Picker</div>
            <div style="font-size: 12px; color: #6B7280;">Describe your product; AI picks the right Meesho category.</div>
          </div>
        </div>

        <!-- Row 2: Quality Pre-Check -->
        <div style="
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 10px 0;
          border-bottom: 1px solid #F3F4F6;
        ">
          <div style="
            width: 32px;
            height: 32px;
            min-width: 32px;
            background: #F0FDF4;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            font-weight: 700;
            color: #16A34A;
            line-height: 1;
          ">&#10003;</div>
          <div>
            <div style="font-size: 13px; font-weight: 600; color: #1F2937; margin-bottom: 2px;">Quality Pre-Check</div>
            <div style="font-size: 12px; color: #6B7280;">Image validation: size, white background, watermark detection.</div>
          </div>
        </div>

        <!-- Row 3: P&L Calculator (no border-bottom on last row) -->
        <div style="
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 10px 0;
        ">
          <div style="
            width: 32px;
            height: 32px;
            min-width: 32px;
            background: #EFF6FF;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            line-height: 1;
          ">&#128202;</div>
          <div>
            <div style="font-size: 13px; font-weight: 600; color: #1F2937; margin-bottom: 2px;">P&amp;L Calculator</div>
            <div style="font-size: 12px; color: #6B7280;">See exact profit per SKU before you list.</div>
          </div>
        </div>

      </div>

      <!-- Section 4: Social Proof -->
      <div style="margin-top: 20px; text-align: center;">
        <span style="font-size: 12px; color: #9CA3AF;">&#11088;&#11088;&#11088;&#11088;&#11088; Trusted by 200+ Tirupur sellers</span>
      </div>

    </div>
  `,
})
export class LandingComponent {}

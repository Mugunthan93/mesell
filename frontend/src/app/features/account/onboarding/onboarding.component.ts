// features/account/onboarding/onboarding.component.ts
// Visual shell only — hardcoded stubs. signal<number> for currentStep,
// signal<Set<string>> for selected categories. No service injection, no FormBuilder.

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  signal,
} from '@angular/core';

@Component({
  selector: 'mee-onboarding-wizard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="padding:32px 32px 28px;">

      <!-- Step indicator: 4 dots connected by lines -->
      <div style="display:flex;align-items:center;justify-content:center;margin-bottom:24px;gap:0;">
        @for (dot of stepDots; track dot.step) {
          <span
            style="
              display:inline-block;
              border-radius:50%;
              transition:background 0.2s, width 0.2s, height 0.2s;
            "
            [style.width]="currentStep() === dot.step ? '10px' : '8px'"
            [style.height]="currentStep() === dot.step ? '10px' : '8px'"
            [style.background]="currentStep() === dot.step ? '#F26B23' : '#D1D5DB'"
          ></span>
          @if (dot.step < 4) {
            <div style="width:32px;height:1px;background:#E5E7EB;"></div>
          }
        }
      </div>

      <!-- Step content -->
      @switch (currentStep()) {

        @case (1) {
          <!-- Step 1: Verify OTP -->
          <h2 style="font-size:20px;font-weight:700;color:#1F2937;margin:0 0 8px;">Verify your number</h2>
          <p style="font-size:13px;color:#6B7280;margin:0 0 20px;">
            Enter the 6-digit code sent to +91 98765 43210
          </p>
          <!-- 6 OTP boxes -->
          <div style="display:inline-flex;gap:8px;margin-bottom:4px;">
            @for (box of otpBoxes; track box) {
              <input
                type="text"
                maxlength="1"
                inputmode="numeric"
                class="otp-box"
                style="
                  width:44px;
                  height:44px;
                  border:1px solid #D1D5DB;
                  border-radius:8px;
                  text-align:center;
                  font-size:20px;
                  font-weight:700;
                  color:#1F2937;
                  background:#F9FAFB;
                  outline:none;
                "
              />
            }
          </div>
        }

        @case (2) {
          <!-- Step 2: Business Details -->
          <h2 style="font-size:20px;font-weight:700;color:#1F2937;margin:0 0 20px;">Tell us about your business</h2>

          <label style="display:block;font-size:13px;font-weight:500;color:#374151;margin-bottom:6px;">
            Business Name
          </label>
          <input
            type="text"
            placeholder="e.g. Sri Murugan Textiles"
            class="mee-input"
            style="
              display:block;
              width:100%;
              box-sizing:border-box;
              height:44px;
              border:1px solid #D1D5DB;
              border-radius:8px;
              padding:0 14px;
              background:#F9FAFB;
              font-size:14px;
              color:#1F2937;
              outline:none;
              margin-bottom:16px;
            "
          />

          <label style="display:block;font-size:13px;font-weight:500;color:#374151;margin-bottom:6px;">
            City
          </label>
          <input
            type="text"
            placeholder="e.g. Tirupur"
            class="mee-input"
            style="
              display:block;
              width:100%;
              box-sizing:border-box;
              height:44px;
              border:1px solid #D1D5DB;
              border-radius:8px;
              padding:0 14px;
              background:#F9FAFB;
              font-size:14px;
              color:#1F2937;
              outline:none;
            "
          />
        }

        @case (3) {
          <!-- Step 3: Categories -->
          <h2 style="font-size:20px;font-weight:700;color:#1F2937;margin:0 0 8px;">What do you sell?</h2>
          <p style="font-size:13px;color:#6B7280;margin:0 0 20px;">Pick your main product categories</p>

          <div style="display:flex;flex-wrap:wrap;gap:10px;">
            @for (cat of categories; track cat) {
              <button
                type="button"
                (click)="toggleCategory(cat)"
                style="
                  height:34px;
                  padding:0 16px;
                  border-radius:999px;
                  font-size:13px;
                  cursor:pointer;
                  transition:background 0.15s, border-color 0.15s, color 0.15s;
                "
                [style.background]="isCategorySelected(cat) ? '#FFF3E8' : '#ffffff'"
                [style.border]="isCategorySelected(cat) ? '1px solid #F26B23' : '1px solid #D1D5DB'"
                [style.color]="isCategorySelected(cat) ? '#F26B23' : '#374151'"
              >{{ cat }}</button>
            }
          </div>
        }

        @case (4) {
          <!-- Step 4: Privacy & Terms -->
          <h2 style="font-size:20px;font-weight:700;color:#1F2937;margin:0 0 12px;">Almost there!</h2>
          <p style="font-size:13px;color:#6B7280;margin:0 0 20px;line-height:1.6;">
            MeeSell handles your data in compliance with India's Digital Personal
            Data Protection Act 2023.
          </p>

          <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer;">
            <input
              type="checkbox"
              style="
                width:18px;height:18px;
                margin-top:1px;
                flex-shrink:0;
                accent-color:#F26B23;
                cursor:pointer;
              "
            />
            <span style="font-size:13px;color:#374151;line-height:1.5;">
              I agree to the
              <a href="#" style="color:#F26B23;text-decoration:none;">Terms of Service</a>
              and
              <a href="#" style="color:#F26B23;text-decoration:none;">Privacy Policy</a>
            </span>
          </label>
        }

      }

      <!-- Navigation footer -->
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:28px;">

        <!-- Back button (hidden on step 1) -->
        @if (currentStep() > 1) {
          <button
            type="button"
            (click)="prevStep()"
            style="
              height:40px;
              padding:0 16px;
              background:transparent;
              border:none;
              font-size:14px;
              color:#6B7280;
              cursor:pointer;
            "
          >&larr; Back</button>
        } @else {
          <span></span>
        }

        <!-- Continue / Get Started button -->
        <button
          type="button"
          (click)="nextStep()"
          style="
            height:40px;
            padding:0 20px;
            background:#F26B23;
            color:#ffffff;
            font-size:14px;
            font-weight:600;
            border:none;
            border-radius:8px;
            cursor:pointer;
          "
        >{{ currentStep() < 4 ? 'Continue →' : 'Get Started!' }}</button>

      </div>

    </div>
  `,
  styles: [`
    .otp-box:focus { border-color: #F26B23; }
    .mee-input:focus { border-color: #F26B23; }
    input::placeholder { color: #9CA3AF; }
  `],
})
export class OnboardingWizardComponent {
  readonly currentStep = signal<number>(1);

  readonly selectedCategories = signal<Set<string>>(new Set());

  readonly stepDots = [
    { step: 1 },
    { step: 2 },
    { step: 3 },
    { step: 4 },
  ];

  readonly otpBoxes = [1, 2, 3, 4, 5, 6];

  readonly categories = ['Kurtis', 'Sarees', 'T-Shirts', 'Dresses', 'Leggings', 'Tops'];

  isCategorySelected(cat: string): boolean {
    return this.selectedCategories().has(cat);
  }

  toggleCategory(cat: string): void {
    const next = new Set(this.selectedCategories());
    if (next.has(cat)) {
      next.delete(cat);
    } else {
      next.add(cat);
    }
    this.selectedCategories.set(next);
  }

  nextStep(): void {
    if (this.currentStep() < 4) {
      this.currentStep.update(s => s + 1);
    }
  }

  prevStep(): void {
    if (this.currentStep() > 1) {
      this.currentStep.update(s => s - 1);
    }
  }
}

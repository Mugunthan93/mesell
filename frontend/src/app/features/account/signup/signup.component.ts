// features/account/signup/signup.component.ts
// Visual shell only — hardcoded stubs, no service injection, no FormBuilder.

import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'mee-signup',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="padding:32px 32px 28px;">

      <!-- Heading -->
      <h1 style="font-size:22px;font-weight:700;color:#1F2937;margin:0 0 4px;">Create your account</h1>
      <p style="font-size:14px;color:#6B7280;margin:0 0 24px;">Start your free 14-day trial</p>

      <!-- Business Name field -->
      <label style="display:block;font-size:13px;font-weight:500;color:#374151;margin-bottom:6px;">
        Business / Shop Name
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

      <!-- Mobile Number field -->
      <label style="display:block;font-size:13px;font-weight:500;color:#374151;margin-bottom:6px;">
        Mobile Number
      </label>
      <div class="phone-row"
           style="display:flex;border:1px solid #D1D5DB;border-radius:8px;overflow:hidden;margin-bottom:0;">
        <span style="
          display:flex;align-items:center;
          background:#F3F4F6;
          border-right:1px solid #D1D5DB;
          padding:0 12px;
          height:44px;
          font-size:14px;
          color:#6B7280;
          white-space:nowrap;
          flex-shrink:0;
        ">+91</span>
        <input
          type="tel"
          placeholder="98765 43210"
          style="
            flex:1;
            height:44px;
            border:none;
            outline:none;
            padding:0 14px;
            font-size:14px;
            color:#1F2937;
            background:#F9FAFB;
          "
        />
      </div>

      <!-- Continue button -->
      <button
        type="button"
        style="
          display:block;
          width:100%;
          height:44px;
          background:#F26B23;
          color:#ffffff;
          font-size:15px;
          font-weight:600;
          border:none;
          border-radius:8px;
          cursor:pointer;
          margin-top:16px;
        "
      >Continue</button>

      <!-- Privacy note -->
      <p style="font-size:12px;color:#9CA3AF;text-align:center;margin:16px 0 0;">
        By continuing you agree to our Terms &amp; Privacy Policy
      </p>

      <!-- Login link -->
      <p style="font-size:14px;color:#6B7280;text-align:center;margin:12px 0 0;">
        Already have an account?
        <a href="/login"
           style="color:#F26B23;font-weight:600;text-decoration:none;">Login</a>
      </p>

    </div>
  `,
  styles: [`
    .phone-row:focus-within {
      border-color: #F26B23;
      outline: none;
    }
    .mee-input:focus {
      border-color: #F26B23;
    }
    input::placeholder { color: #9CA3AF; }
  `],
})
export class SignupComponent {}

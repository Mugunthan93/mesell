// features/account/login/login.component.ts
// Visual shell only — hardcoded stubs, no service injection, no FormBuilder.

import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'mee-login',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="padding:32px 32px 28px;">

      <!-- Heading -->
      <h1 style="font-size:22px;font-weight:700;color:#1F2937;margin:0 0 4px;">Welcome back</h1>
      <p style="font-size:14px;color:#6B7280;margin:0 0 24px;">Enter your phone number to continue</p>

      <!-- Mobile number field -->
      <label style="display:block;font-size:13px;font-weight:500;color:#374151;margin-bottom:6px;">
        Mobile Number
      </label>
      <div class="phone-row"
           style="display:flex;border:1px solid #D1D5DB;border-radius:8px;overflow:hidden;">
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

      <!-- Send OTP button -->
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
      >Send OTP</button>

      <!-- Divider -->
      <div style="
        display:flex;align-items:center;
        margin:20px 0;
        gap:12px;
        color:#9CA3AF;
        font-size:13px;
      ">
        <div style="flex:1;height:1px;background:#E5E7EB;"></div>
        <span>Or</span>
        <div style="flex:1;height:1px;background:#E5E7EB;"></div>
      </div>

      <!-- Sign-up link -->
      <p style="font-size:14px;color:#6B7280;text-align:center;margin:0;">
        New here?
        <a href="/signup"
           style="color:#F26B23;font-weight:600;text-decoration:none;">Create an account</a>
      </p>

    </div>
  `,
  styles: [`
    .phone-row:focus-within {
      border-color: #F26B23;
      outline: none;
    }
    input::placeholder { color: #9CA3AF; }
  `],
})
export class LoginComponent {}

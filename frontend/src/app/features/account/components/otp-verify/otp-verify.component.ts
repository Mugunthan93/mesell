// features/account/components/otp-verify/otp-verify.component.ts
// Stub — full implementation by meesell-angular-component-builder per §7
// Wraps ng-otp-input (§6 pick #6) for paste-aware SMS auto-fill

import { ChangeDetectionStrategy, Component, EventEmitter, Output } from '@angular/core';

@Component({
  selector: 'mee-otp-verify',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="mee-otp-verify"><!-- OTP verify stub --></div>`,
})
export class OtpVerifyComponent {
  @Output() readonly otpComplete = new EventEmitter<string>();
}

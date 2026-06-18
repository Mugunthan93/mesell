import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnDestroy,
  OnInit,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Router } from '@angular/router';
import { AuthLayoutComponent } from '@mesell/composites';
import { AuthService } from '@mesell/core';
import { MeeOtpInputComponent, MeeButtonComponent } from '@mesell/ui-kit';

@Component({
  selector: 'mee-otp-verify',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AuthLayoutComponent, RouterLink, MeeOtpInputComponent, MeeButtonComponent],
  template: `
    <mee-auth-layout>
      <h1>Verify your number</h1>
      <p class="subtitle">We sent a 6-digit code to your mobile</p>

      <div class="otp-section" aria-label="One-time password entry">
        <!-- Not a <label> — OTP cells each get their own aria-label from PrimeNG.
             Use a <p> to avoid an orphaned label that fails WCAG 1.3.1. -->
        <p class="otp-label">Enter OTP</p>
        <mee-otp-input
          [length]="6"
          [disabled]="loading()"
          (completed)="onOtpCompleted($event)"
        />
        @if (otpValue().length > 0 && otpValue().length < 6) {
          <span class="error-text" role="alert">Enter the 6-digit OTP</span>
        }
      </div>

      <mee-button
        [label]="'Verify OTP'"
        [loading]="loading()"
        [disabled]="otpValue().length < 6"
        [fullWidth]="true"
        (clicked)="onSubmit()"
      />

      <div class="resend-area">
        @if (countdown() > 0) {
          <span class="countdown-text">Resend code in {{ countdown() }}s</span>
        } @else {
          <a class="resend-link" (click)="resendOtp()" role="button" tabindex="0"
             (keydown.enter)="resendOtp()" (keydown.space)="resendOtp()">Resend OTP</a>
        }
      </div>

      <p class="footer-text">
        <a routerLink="/login">← Back to login</a>
      </p>
    </mee-auth-layout>
  `,
  styles: [`
    h1 {
      font-size: 22px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin-bottom: var(--mee-space-1);
    }
    .subtitle {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      margin-bottom: var(--mee-space-6);
    }
    .otp-label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      margin-bottom: var(--mee-space-2);
      color: var(--mee-color-on-surface);
    }
    .otp-section { margin-top: var(--mee-space-4); }
    /* Make mee-otp-input host and PrimeNG wrapper fill the card width.
       At 360px (card content ≈ 288px after 20px padding): 6 cells with 8px gaps =
       (288 - 5*8) / 6 = (288-40)/6 = 41.3px per cell — above the 44px threshold only
       when browser renders fractionally. Enforce minimum via flex:1 per cell. */
    ::ng-deep mee-otp-input { display: block; width: 100%; }
    ::ng-deep mee-otp-input p-inputotp { display: block; width: 100%; }
    ::ng-deep mee-otp-input .p-inputotp { display: flex; width: 100%; }
    ::ng-deep mee-otp-input .p-inputotp-input {
      flex: 1;
      min-width: 0;
      min-height: 44px;
      font-size: 18px;
      font-weight: 600;
      text-align: center;
    }
    .error-text {
      display: block;
      font-size: 12px;
      color: var(--mee-color-error);
      margin-top: var(--mee-space-1);
    }
    .footer-text {
      text-align: center;
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
      margin-top: var(--mee-space-5);
    }
    .footer-text a {
      color: var(--mee-color-primary);
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      transition: color var(--mee-transition-fast);
    }
    .footer-text a:hover {
      text-decoration: underline;
    }
    .otp-section + * { margin-top: var(--mee-space-4); }
    .resend-area {
      text-align: center;
      margin-top: var(--mee-space-4);
      font-size: 13px;
    }
    .countdown-text { color: var(--mee-color-on-surface-muted); }
    .resend-link {
      color: var(--mee-color-primary);
      font-weight: 500;
      cursor: pointer;
      min-height: 44px;
      display: inline-flex;
      align-items: center;
    }
  `],
})
export class OtpVerifyComponent implements OnInit, OnDestroy {
  private readonly router = inject(Router);
  private readonly auth   = inject(AuthService);

  readonly loading   = signal(false);
  readonly countdown = signal(30);
  readonly otpValue  = signal<string>('');

  private intervalId?: ReturnType<typeof setInterval>;

  ngOnInit(): void {
    this.startCountdown();
  }

  ngOnDestroy(): void {
    clearInterval(this.intervalId);
  }

  onOtpCompleted(val: string): void {
    this.otpValue.set(val);
  }

  resendOtp(): void {
    this.countdown.set(30);
    clearInterval(this.intervalId);
    this.startCountdown();
  }

  onSubmit(): void {
    if (this.otpValue().length < 6) return;
    this.loading.set(true);
    setTimeout(() => {
      this.loading.set(false);
      this.auth.setSession('mock-token', {
        id: 1,
        name: 'Seller',
        phone: '+91XXXXXXXXXX',
      });
      this.router.navigate(['/dashboard']);
    }, 1500);
  }

  private startCountdown(): void {
    this.intervalId = setInterval(() => {
      if (this.countdown() > 0) {
        this.countdown.update(v => v - 1);
      } else {
        clearInterval(this.intervalId);
      }
    }, 1000);
  }
}

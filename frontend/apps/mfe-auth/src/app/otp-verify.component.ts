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
import { MeeOtpInputComponent } from '@mesell/ui-kit/otp-input/otp-input.component';
import { MeeButtonComponent } from '@mesell/ui-kit/button/button.component';

@Component({
  selector: 'mee-otp-verify',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AuthLayoutComponent, RouterLink, MeeOtpInputComponent, MeeButtonComponent],
  template: `
    <mee-auth-layout>
      <h1>Verify your number</h1>
      <p class="subtitle">We sent a 6-digit code to your mobile</p>

      <div class="otp-section">
        <label>Enter OTP</label>
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
      margin-bottom: 4px;
    }
    .subtitle {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      margin-bottom: 24px;
    }
    label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 6px;
      color: var(--mee-color-on-surface);
    }
    .otp-section { margin-top: 16px; }
    .error-text {
      display: block;
      font-size: 12px;
      color: var(--mee-color-error);
      margin-top: 4px;
    }
    .footer-text {
      text-align: center;
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      margin-top: 20px;
    }
    .footer-text a {
      color: var(--mee-color-primary);
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
    }
    .otp-section + * { margin-top: 16px; }
    .resend-area {
      text-align: center;
      margin-top: 16px;
      font-size: 14px;
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

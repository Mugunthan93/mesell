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
import { catchError, EMPTY, switchMap } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthLayoutComponent, MeeAlertBannerComponent } from '@mesell/composites';
import { AuthService, AuthApiService } from '@mesell/core';
import { MeeOtpInputComponent } from '@mesell/ui-kit/otp-input/otp-input.component';
import { MeeButtonComponent } from '@mesell/ui-kit/button/button.component';

@Component({
  selector: 'mee-otp-verify',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AuthLayoutComponent, RouterLink, MeeOtpInputComponent, MeeButtonComponent, MeeAlertBannerComponent],
  template: `
    <mee-auth-layout>
      <h1>Verify your number</h1>
      <p class="subtitle">We sent a 6-digit code to {{ maskedPhone() }}</p>

      <!-- Contextual error banner — offline state handled globally by AuthLayoutComponent -->
      @if (errorMessage()) {
        <mee-alert-banner
          variant="error"
          [message]="errorMessage()!"
          class="banner-spacing"
        />
      }

      <div class="otp-section">
        <label [id]="otpLabelId">Enter OTP</label>
        <mee-otp-input
          [length]="6"
          [disabled]="loading()"
          [attr.aria-labelledby]="otpLabelId"
          (completed)="onOtpCompleted($event)"
        />
        @if (otpValue().length > 0 && otpValue().length < 6) {
          <span class="error-text" role="alert" aria-live="polite">Enter the 6-digit OTP</span>
        }
      </div>

      <mee-button
        [label]="'Verify OTP'"
        [loading]="loading()"
        [disabled]="otpValue().length < 6 || loading()"
        [fullWidth]="true"
        (clicked)="onSubmit()"
      />

      <div class="resend-area" aria-live="polite" aria-atomic="true">
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
    /* Ensure minimum 44px tap target on footer + resend links */
    .footer-text a,
    .resend-link {
      min-height: 44px;
    }
    .footer-text a {
      display: inline-block;
      line-height: 44px;
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
      display: inline-flex;
      align-items: center;
    }
    /* Spacing below banner before the OTP input */
    .banner-spacing { margin-bottom: 16px; }

    /* 360px — tighten heading so card fits */
    @media (max-width: 400px) {
      h1 { font-size: 20px; }
    }
  `],
})
export class OtpVerifyComponent implements OnInit, OnDestroy {
  private readonly router   = inject(Router);
  private readonly auth     = inject(AuthService);
  private readonly authApi  = inject(AuthApiService);

  readonly loading      = signal(false);
  readonly countdown    = signal(30);
  readonly otpValue     = signal<string>('');
  readonly errorMessage = signal<string | null>(null);

  /** Unique ID for aria-labelledby wiring on the OTP input */
  readonly otpLabelId = `mee-otp-label-${Math.random().toString(36).slice(2)}`;

  /** Phone received from Router state (login/signup → navigate with state: { phone }) */
  private _phone: string = '';

  private intervalId?: ReturnType<typeof setInterval>;

  ngOnInit(): void {
    // Read phone from Router navigation state.
    // Navigation state is present when arriving from login/signup.
    // If directly visiting this URL (no state), redirect to /login (§5.2 spec).
    const nav = this.router.getCurrentNavigation();
    const phone = (nav?.extras?.state as { phone?: string })?.phone
      ?? (window.history.state as { phone?: string })?.phone;

    if (!phone) {
      // Direct URL visit with no state — redirect to login
      this.router.navigate(['/login']);
      return;
    }
    this._phone = phone;
    this.startCountdown();
  }

  ngOnDestroy(): void {
    clearInterval(this.intervalId);
  }

  onOtpCompleted(val: string): void {
    this.otpValue.set(val);
  }

  resendOtp(): void {
    if (!this._phone) return;
    this.errorMessage.set(null);
    this.authApi.sendOtp(this._phone)
      .pipe(
        catchError(() => {
          this.errorMessage.set('Failed to resend OTP. Please try again.');
          return EMPTY;
        }),
      )
      .subscribe(() => {
        this.countdown.set(30);
        clearInterval(this.intervalId);
        this.startCountdown();
      });
  }

  onSubmit(): void {
    if (this.otpValue().length < 6 || this.loading()) return;
    this.errorMessage.set(null);
    this.loading.set(true);

    // Critical order per spec handoff:
    // 1. verifyOtp() success → (2) auth.setSession(token, user) → (3) auth.scheduleRefresh → (4) navigate
    this.authApi.verifyOtp(this._phone, this.otpValue())
      .pipe(
        switchMap((resp) => {
          // Hydrate user from /me before calling setSession
          return this.authApi.me().pipe(
            catchError(() => {
              // /me failed — use a minimal user with phone only (graceful fallback)
              this.auth.setSession(resp.access_token, { phone: this._phone });
              this.auth.scheduleRefresh(resp.expires_in);
              this.loading.set(false);
              this.router.navigate(['/dashboard']);
              return EMPTY;
            }),
            switchMap((meResp) => {
              // Full hydration: set session with real user data from /me
              this.auth.setSession(resp.access_token, {
                phone: meResp.phone,
                user_id: meResp.user_id,
                plan: meResp.plan,
                created_at: meResp.created_at,
                last_login_at: meResp.last_login_at,
              });
              this.auth.scheduleRefresh(resp.expires_in);
              this.loading.set(false);
              this.router.navigate(['/dashboard']);
              return EMPTY;
            }),
          );
        }),
        catchError((err: HttpErrorResponse) => {
          this.loading.set(false);
          if (err.status === 400 || err.status === 401) {
            this.errorMessage.set('Invalid or expired code. Please try again.');
          } else if (err.status === 429) {
            this.errorMessage.set('Too many attempts. Please wait before retrying.');
          } else {
            this.errorMessage.set('Something went wrong. Please try again.');
          }
          return EMPTY;
        }),
      )
      .subscribe();
  }

  maskedPhone(): string {
    if (!this._phone) return 'your mobile';
    // Show last 4 digits only: e.g. +91XXXXXX1234
    const digits = this._phone.replace(/\D/g, '');
    return '+' + digits.slice(0, 2) + 'XXXXXX' + digits.slice(-4);
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

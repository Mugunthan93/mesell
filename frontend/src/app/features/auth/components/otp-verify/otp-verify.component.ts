// features/auth/components/otp-verify/otp-verify.component.ts
// OTP entry + verify + resend — Dispatch 3.
// Standalone, OnPush, selector: mee-otp-verify.
// Consumes AuthApiService (verifyOtp + sendOtp) + ApiClient (GET /seller-profile).
// Post-verify routing per Q-AUTH-003 Option A: profile_complete → /dashboard else /onboarding.

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  Input,
  OnInit,
  signal,
  ViewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslocoModule, TranslocoService } from '@jsverse/transloco';
import { NgOtpInputModule, NgOtpInputComponent } from 'ng-otp-input';
import { interval } from 'rxjs';
import { take } from 'rxjs/operators';

import { AuthApiService } from '../../auth-api.service';
import { ApiClient } from '@core/api/api-client.service';
import { ApiError } from '@core/api/api-error';
import { ErrorService } from '@core/services/error.service';
import { SellerProfile } from '@core/models/seller-profile.model';

@Component({
  selector: 'mee-otp-verify',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'mee-otp-verify' },
  imports: [
    NgOtpInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslocoModule,
  ],
  template: `
    <div class="flex flex-col gap-6 max-w-sm mx-auto px-4 py-8">

      <!-- Title -->
      <h2 class="text-mee-2xl font-bold text-on-surface">
        {{ 'account.otp.title' | transloco }}
      </h2>

      <!-- Subtitle: "OTP sent to 9876543210" — strip +91 for display -->
      <p class="text-mee-sm text-on-surface-variant" aria-live="polite">
        {{ 'account.otp.sent_to' | transloco: { phone: displayPhone() } }}
      </p>

      <!-- OTP input widget -->
      <div class="flex justify-center" role="group" aria-label="Enter 6-digit OTP">
        <ng-otp-input
          #otpInput
          [config]="otpConfig"
          (onInputChange)="onOtpChange($event)"
        />
      </div>

      <!-- Inline error (M3: plain language, never backend codes) -->
      @if (errorMsg()) {
        <p
          class="text-error text-mee-sm"
          role="alert"
          aria-live="assertive"
        >{{ errorMsg() }}</p>
      }

      <!-- Verify button -->
      <button
        mat-flat-button
        color="primary"
        class="w-full min-h-[44px]"
        [disabled]="otpValue().length < 6 || verifying() || attempts() >= 3"
        (click)="doVerify()"
        aria-label="Verify OTP"
      >
        @if (verifying()) {
          <mat-spinner diameter="20" class="inline-block"></mat-spinner>
        } @else {
          {{ 'account.otp.verify' | transloco }}
        }
      </button>

      <!-- Resend section -->
      <div class="text-center text-mee-sm">
        @if (timeLeft() > 0) {
          <span class="text-on-surface-variant">
            {{ 'account.otp.resend_in' | transloco: { seconds: timeLeft() } }}
          </span>
        } @else if (attempts() < 3) {
          <button
            mat-button
            color="primary"
            class="min-h-[44px]"
            [disabled]="resending()"
            (click)="onResend()"
          >
            @if (resending()) {
              <mat-spinner diameter="16" class="inline-block"></mat-spinner>
            } @else {
              {{ 'account.otp.resend' | transloco }}
            }
          </button>
        }
      </div>

    </div>
  `,
})
export class OtpVerifyComponent implements OnInit {
  @Input({ required: true }) phone = '';     // E.164: +91XXXXXXXXXX
  @Input({ required: true }) requestId = ''; // MSG91 correlation ID

  @ViewChild('otpInput') otpInput!: NgOtpInputComponent;

  private readonly authApi = inject(AuthApiService);
  private readonly apiClient = inject(ApiClient);
  private readonly errorService = inject(ErrorService);
  private readonly transloco = inject(TranslocoService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly otpValue     = signal('');
  readonly verifying    = signal(false);
  readonly resending    = signal(false);
  readonly timeLeft     = signal(60);
  readonly attempts     = signal(0);
  readonly errorMsg     = signal<string | null>(null);
  private readonly localRequestId = signal('');

  /** Strip +91 prefix for display. E.g. +919876543210 → 9876543210 */
  readonly displayPhone = computed<string>(() => {
    const p = this.phone;
    if (p.startsWith('+91')) return p.slice(3);
    return p;
  });

  readonly otpConfig = {
    length: 6,
    allowNumbersOnly: true,
    inputStyles: {
      'font-size': '1.25rem',
      'text-align': 'center',
      'border-radius': 'var(--mee-radius-sm)',
    },
  };

  ngOnInit(): void {
    this.localRequestId.set(this.requestId);
    this.startCountdown();
  }

  private startCountdown(): void {
    this.timeLeft.set(60);
    interval(1000)
      .pipe(
        take(60),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        this.timeLeft.update(t => Math.max(0, t - 1));
      });
  }

  onOtpChange(val: string): void {
    this.otpValue.set(val);
    if (val.length === 6 && !this.verifying() && this.attempts() < 3) {
      this.doVerify();
    }
  }

  doVerify(): void {
    this.verifying.set(true);
    this.errorMsg.set(null);

    this.authApi.verifyOtp({ phone: this.phone, otp: this.otpValue() }).subscribe({
      next: (_res) => {
        // AuthApiService.verifyOtp() already called AuthService.setAccess() via tap.
        // Now check profile completeness per Q-AUTH-003 ruling (Option A).
        this.apiClient.get<SellerProfile>('/seller-profile').subscribe({
          next: (profile) => {
            if (profile.profile_complete) {
              this.router.navigate(['/dashboard']);
            } else {
              this.router.navigate(['/onboarding']);
            }
            // verifying stays true during navigate — component will unmount
          },
          error: (_profileErr) => {
            // 404 = no profile yet → go to onboarding
            // any other error → also go to onboarding (safe fallback per Q-AUTH-003)
            this.router.navigate(['/onboarding']);
          },
        });
      },
      error: (err: ApiError) => {
        this.verifying.set(false);
        this.attempts.update(a => a + 1);
        if (this.attempts() >= 3) {
          this.errorMsg.set(
            this.transloco.translate('auth.otp_attempts_exceeded') as string,
          );
        } else if (err.status === 429) {
          this.errorService.showError(
            this.transloco.translate('account.otp.rate_limit', { minutes: '60' }) as string,
          );
        } else {
          // 400/422 = wrong OTP
          this.errorMsg.set(
            this.transloco.translate('auth.otp_invalid') as string,
          );
        }
        // Reset the OTP input widget
        if (this.otpInput) {
          this.otpInput.setValue('');
        }
        this.otpValue.set('');
      },
    });
  }

  onResend(): void {
    this.resending.set(true);

    this.authApi.sendOtp({ phone: this.phone }).subscribe({
      next: (res) => {
        this.localRequestId.set(res.request_id);
        this.errorMsg.set(null);
        this.resending.set(false);
        this.startCountdown();
        // Reset OTP input
        if (this.otpInput) {
          this.otpInput.setValue('');
        }
        this.otpValue.set('');
      },
      error: (err: ApiError) => {
        this.resending.set(false);
        if (err.status === 429) {
          this.errorService.showError(
            this.transloco.translate('account.otp.rate_limit', { minutes: '60' }) as string,
          );
        } else {
          this.errorService.showError(
            this.transloco.translate('common.error') as string,
          );
        }
      },
    });
  }
}

// features/auth/signup/signup.component.ts
// Signup page — phone entry → OTP phase transition.
// Standalone, OnPush, selector: mee-signup.

import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslocoModule, TranslocoService } from '@jsverse/transloco';
import { ApiError } from '@core/api/api-error';
import { ErrorService } from '@core/services/error.service';
import { AuthApiService } from '../auth-api.service';
import { PhoneInputComponent } from '../components/phone-input/phone-input.component';
import { OtpVerifyComponent } from '../components/otp-verify/otp-verify.component';

@Component({
  selector: 'mee-signup',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    RouterLink,
    TranslocoModule,
    PhoneInputComponent,
    OtpVerifyComponent,
  ],
  template: `
    <div class="flex flex-col gap-6 p-8">

      <h1 class="text-2xl font-bold">{{ 'account.signup.title' | transloco }}</h1>

      @if (phase() === 'phone') {
        <form [formGroup]="form" (ngSubmit)="onSubmit()" novalidate>

          <mee-phone-input
            formControlName="phone"
            [label]="'account.signup.phone_label' | transloco"
          />

          <button
            mat-flat-button
            color="primary"
            type="submit"
            class="w-full min-h-[44px] mt-4"
            [disabled]="sending() || form.invalid"
          >
            @if (sending()) {
              <mat-spinner diameter="20" class="inline-block"></mat-spinner>
            } @else {
              {{ 'account.signup.send_otp' | transloco }}
            }
          </button>

        </form>

        <p class="text-sm text-center">
          {{ 'auth.signup.login_link' | transloco }}
          <a routerLink="/login" class="text-primary font-semibold min-h-[44px] inline-flex items-center">
            {{ 'account.login.title' | transloco }}
          </a>
        </p>
      }

      @if (phase() === 'otp_sent') {
        <mee-otp-verify
          [phone]="phone()"
          [requestId]="requestId() ?? ''"
        />
      }

    </div>
  `,
})
export class SignupComponent {
  private readonly authApi = inject(AuthApiService);
  private readonly errorService = inject(ErrorService);
  private readonly transloco = inject(TranslocoService);
  private readonly fb = inject(FormBuilder);

  readonly phase = signal<'phone' | 'otp_sent'>('phone');
  readonly sending = signal(false);
  readonly requestId = signal<string | null>(null);
  readonly phone = signal<string>('');

  readonly form = this.fb.group({
    phone: ['', [Validators.required]],
  });

  onSubmit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) return;

    const phoneValue = this.form.value.phone ?? '';
    this.sending.set(true);

    this.authApi.sendOtp({ phone: phoneValue }).subscribe({
      next: (res) => {
        this.requestId.set(res.request_id);
        this.phone.set(phoneValue);
        this.phase.set('otp_sent');
        this.sending.set(false);
      },
      error: (err: ApiError) => {
        this.sending.set(false);
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

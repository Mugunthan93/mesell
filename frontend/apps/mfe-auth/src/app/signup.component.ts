import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { catchError, EMPTY } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthLayoutComponent } from '@mesell/composites';
import { MeeInputComponent } from '@mesell/ui-kit/input/input.component';
import { MeeButtonComponent } from '@mesell/ui-kit/button/button.component';
import { AuthApiService } from '@mesell/core';
import { NetworkService } from '@mesell/core';

@Component({
  selector: 'mee-signup',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AuthLayoutComponent, ReactiveFormsModule, RouterLink, MeeInputComponent, MeeButtonComponent],
  template: `
    <mee-auth-layout>
      <h1>Create your account</h1>
      <p class="subtitle">Start selling smarter</p>

      @if (!networkSvc.online()) {
        <div class="offline-banner" role="alert" aria-live="polite">
          You are offline. Please check your connection.
        </div>
      }

      @if (errorMessage()) {
        <div class="error-banner" role="alert" aria-live="polite">
          {{ errorMessage() }}
        </div>
      }

      <form [formGroup]="form" (ngSubmit)="onSubmit()">
        <mee-input
          [label]="'Full Name'"
          [placeholder]="'Your name'"
          [error]="nameError()"
          [required]="true"
          formControlName="name"
        />

        <mee-input
          [label]="'Mobile Number'"
          [prefix]="'+91'"
          [placeholder]="'10-digit number'"
          [error]="phoneError()"
          [required]="true"
          formControlName="phone"
        />

        <mee-button
          [label]="'Create Account'"
          [loading]="loading()"
          [disabled]="form.invalid || loading()"
          [fullWidth]="true"
          (clicked)="onSubmit()"
        />
      </form>

      <p class="footer-text">
        Already have an account?
        <a routerLink="/login">Log in</a>
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
    form > * + * { margin-top: 16px; }
    .offline-banner {
      background: var(--mee-color-warning-light, rgba(234,179,8,0.1));
      border: 1px solid var(--mee-color-warning, #ca8a04);
      color: var(--mee-color-warning, #ca8a04);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 14px;
      margin-bottom: 16px;
    }
    .error-banner {
      background: var(--mee-color-error-light, rgba(239,68,68,0.1));
      border: 1px solid var(--mee-color-error, #dc2626);
      color: var(--mee-color-error, #dc2626);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 14px;
      margin-bottom: 16px;
    }
  `],
})
export class SignupComponent {
  private readonly router   = inject(Router);
  private readonly authApi  = inject(AuthApiService);
  readonly networkSvc       = inject(NetworkService);

  readonly loading      = signal(false);
  readonly errorMessage = signal<string | null>(null);

  readonly form = new FormGroup({
    name: new FormControl('', [
      Validators.required,
      Validators.minLength(2),
      Validators.maxLength(60),
    ]),
    phone: new FormControl('', [
      Validators.required,
      Validators.pattern(/^[6-9]\d{9}$/),
    ]),
  });

  readonly nameError = computed(() =>
    this.form.get('name')?.touched && this.form.get('name')?.invalid
      ? 'Enter your full name (min 2 characters)'
      : undefined
  );

  readonly phoneError = computed(() =>
    this.form.get('phone')?.touched && this.form.get('phone')?.invalid
      ? 'Enter a valid 10-digit mobile number'
      : undefined
  );

  onSubmit(): void {
    if (this.form.invalid || this.loading()) return;
    this.errorMessage.set(null);
    this.loading.set(true);

    // Normalise: form holds 10-digit raw value; backend requires E.164 (+91)
    const raw   = this.form.get('phone')!.value ?? '';
    const phone = '+91' + raw;

    // V1: signup uses the same OTP send endpoint as login (no separate signup endpoint)
    this.authApi.sendOtp(phone)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          this.loading.set(false);
          if (err.status === 429) {
            this.errorMessage.set('Too many attempts. Please try again later.');
          } else if (err.status === 400) {
            this.errorMessage.set('Invalid phone number. Please check and retry.');
          } else {
            this.errorMessage.set('Something went wrong. Please try again.');
          }
          return EMPTY;
        }),
      )
      .subscribe(() => {
        this.loading.set(false);
        // Hand off phone via Router state so otp-verify can pre-fill/normalise
        this.router.navigate(['/otp-verify'], { state: { phone } });
      });
  }
}

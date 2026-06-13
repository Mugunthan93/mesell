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
import { AuthLayoutComponent, MeeAlertBannerComponent } from '@mesell/composites';
// F-001: barrel import — subpaths are not in the federation import map at runtime
import { MeeInputComponent, MeeButtonComponent } from '@mesell/ui-kit';
import { AuthApiService } from '@mesell/core';

@Component({
  selector: 'mee-signup',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AuthLayoutComponent, ReactiveFormsModule, RouterLink, MeeInputComponent, MeeButtonComponent, MeeAlertBannerComponent],
  template: `
    <mee-auth-layout>
      <h1>Create your account</h1>
      <p class="subtitle">Start selling smarter</p>

      <!-- Contextual error banner — offline state handled globally by AuthLayoutComponent -->
      @if (errorMessage()) {
        <mee-alert-banner
          variant="error"
          [message]="errorMessage()!"
          class="banner-spacing"
        />
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
    /* Ensure minimum 44px tap target on the footer link */
    .footer-text a {
      display: inline-block;
      min-height: 44px;
      line-height: 44px;
    }
    form > * + * { margin-top: 16px; }
    /* Spacing below banner before the form */
    .banner-spacing { margin-bottom: 16px; }

    /* 360px — tighten heading so card fits */
    @media (max-width: 400px) {
      h1 { font-size: 20px; }
    }
  `],
})
export class SignupComponent {
  private readonly router   = inject(Router);
  private readonly authApi  = inject(AuthApiService);

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

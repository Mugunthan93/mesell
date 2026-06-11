import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthLayoutComponent } from '../../layouts/auth-layout/auth-layout.component';
import { MeeInputComponent } from '@mesell/ui-kit/input/input.component';
import { MeeButtonComponent } from '@mesell/ui-kit/button/button.component';

@Component({
  selector: 'mee-signup',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [AuthLayoutComponent, ReactiveFormsModule, RouterLink, MeeInputComponent, MeeButtonComponent],
  template: `
    <mee-auth-layout>
      <h1>Create your account</h1>
      <p class="subtitle">Start selling smarter</p>

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
          [disabled]="form.invalid"
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
  `],
})
export class SignupComponent {
  private readonly router = inject(Router);

  readonly loading = signal(false);

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
    if (this.form.invalid) return;
    this.loading.set(true);
    setTimeout(() => {
      this.loading.set(false);
      this.router.navigate(['/otp-verify']);
    }, 1500);
  }
}

import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthLayoutComponent, MeeAlertBannerComponent } from '@mesell/composites';
import {
  AuthApiService,
  AuthService,
  GoogleIdentityService,
  type GoogleCredentialResponse,
} from '@mesell/core';
import { MeeInputComponent, MeeButtonComponent } from '@mesell/ui-kit';
import { mapGoogleError, mapSendOtpError } from './auth-error-map';

@Component({
  selector: 'mee-login',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    AuthLayoutComponent,
    ReactiveFormsModule,
    RouterLink,
    MeeInputComponent,
    MeeButtonComponent,
    MeeAlertBannerComponent,
  ],
  template: `
    <mee-auth-layout>
      <h1>Welcome back</h1>
      <p class="subtitle">Enter your mobile number to continue</p>

      @if (errorMessage()) {
        <mee-alert-banner variant="error" [message]="errorMessage()!" />
      }

      <form class="auth-form" [formGroup]="form" (ngSubmit)="onSubmit()">
        <mee-input
          [label]="'Mobile Number'"
          [prefix]="'+91'"
          [placeholder]="'10-digit number'"
          [error]="phoneError()"
          [required]="true"
          formControlName="phone"
        />

        <mee-button
          [label]="'Continue →'"
          [loading]="loading()"
          [disabled]="form.invalid || googleLoading()"
          [fullWidth]="true"
          (clicked)="onSubmit()"
        />
      </form>

      <div class="or-divider" aria-hidden="true">
        <span class="or-divider__rule"></span>
        <span class="or-divider__text">or</span>
        <span class="or-divider__rule"></span>
      </div>

      <div
        class="google-area"
        role="group"
        aria-label="Sign in with Google"
        [class.google-area--busy]="loading() || googleLoading()"
      >
        <div
          #googleBtn
          class="google-btn-host"
          aria-label="Continue with Google"
        ></div>
        @if (googleLoading()) {
          <span class="google-busy" role="status" aria-live="polite" aria-busy="true">
            Signing you in…
          </span>
        }
      </div>

      <p class="footer-text">
        Don't have an account?
        <a routerLink="/signup">Sign up</a>
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
    mee-alert-banner { display: block; margin-bottom: var(--mee-space-4); }
    .auth-form {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
    }
    .or-divider {
      display: flex;
      align-items: center;
      gap: var(--mee-space-3);
      margin: var(--mee-space-5) 0;
    }
    .or-divider__rule {
      flex: 1;
      height: 1px;
      background: var(--mee-color-border);
    }
    .or-divider__text {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
    }
    .google-area {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--mee-space-2);
      min-height: 44px;
    }
    /* When busy, cover the GIS button (it cannot be truly disabled) to block clicks. */
    .google-area--busy .google-btn-host {
      pointer-events: none;
      opacity: 0.6;
    }
    .google-btn-host { width: 100%; display: flex; justify-content: center; }
    .google-busy {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
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
  `],
})
export class LoginComponent implements AfterViewInit, OnDestroy {
  private readonly router  = inject(Router);
  private readonly authApi = inject(AuthApiService);
  private readonly auth    = inject(AuthService);
  private readonly gis     = inject(GoogleIdentityService);

  readonly loading       = signal(false);
  readonly googleLoading = signal(false);
  readonly errorMessage  = signal<string | null>(null);

  private readonly googleBtn = viewChild<ElementRef<HTMLDivElement>>('googleBtn');

  readonly form = new FormGroup({
    phone: new FormControl('', [
      Validators.required,
      Validators.pattern(/^[6-9]\d{9}$/),
    ]),
  });

  readonly phoneError = computed(() =>
    this.form.get('phone')?.touched && this.form.get('phone')?.invalid
      ? 'Enter a valid 10-digit mobile number'
      : undefined
  );

  // ── Google sign-in (GIS) ───────────────────────────────────────────────────

  ngAfterViewInit(): void {
    void this.initGoogleButton();
  }

  ngOnDestroy(): void {
    this.gis.cancel();
  }

  private async initGoogleButton(): Promise<void> {
    const host = this.googleBtn()?.nativeElement;
    if (!host) return;
    try {
      await this.gis.load();
      this.gis.initialize((resp: GoogleCredentialResponse) =>
        this.onGoogleCredential(resp.credential),
      );
      this.gis.renderButton(host, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        shape: 'pill',
        logo_alignment: 'left',
        width: host.clientWidth || 320,
      });
    } catch {
      this.errorMessage.set(
        "Couldn't load Google sign-in. Check your connection and try again.",
      );
    }
  }

  /** GIS credential callback target — runs the shared success pipeline. */
  onGoogleCredential(credential: string): void {
    this.errorMessage.set(null);
    this.googleLoading.set(true);
    this.authApi.googleVerify(credential).subscribe({
      next: (resp) => {
        this.auth.completeLogin(resp).subscribe({
          next: ({ route }) => {
            this.googleLoading.set(false);
            void this.router.navigate(route);
          },
          error: () => {
            // completeLogin never errors, but guard defensively.
            this.googleLoading.set(false);
            void this.router.navigate(['/dashboard']);
          },
        });
      },
      error: (err: unknown) => {
        this.googleLoading.set(false);
        this.errorMessage.set(mapGoogleError(err));
      },
    });
  }

  // ── Phone OTP send ──────────────────────────────────────────────────────────

  onSubmit(): void {
    if (this.form.invalid) return;
    this.errorMessage.set(null);
    this.loading.set(true);
    const phone = `+91${this.form.get('phone')!.value}`;
    this.authApi.sendOtp(phone).subscribe({
      next: () => {
        this.loading.set(false);
        void this.router.navigate(['/otp-verify'], { state: { phone } });
      },
      error: (err: unknown) => {
        this.loading.set(false);
        this.errorMessage.set(mapSendOtpError(err));
      },
    });
  }
}


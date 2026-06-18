import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';
import { MeeCardComponent, MeeBadgeComponent, MeeInputComponent, MeeButtonComponent, MeeIconComponent } from '@mesell/ui-kit';
import type { MeeBadgeSeverity } from '@mesell/ui-kit';
import { AuthService } from '@mesell/core';

@Component({
  selector: 'app-profile',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MeeCardComponent,
    MeeBadgeComponent,
    MeeInputComponent,
    MeeButtonComponent,
    MeeIconComponent,
  ],
  styles: [`
    :host {
      display: block;
      padding: var(--mee-space-4);
      padding-bottom: calc(var(--mee-space-8) + env(safe-area-inset-bottom, 0px));
    }

    .profile-header {
      padding: var(--mee-space-2) 0 var(--mee-space-5);
    }

    .profile-title {
      font-size: 24px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0 0 var(--mee-space-1);
    }

    .profile-subtitle {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }

    .profile-content {
      max-width: 560px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-6);
    }

    .identity-card-body {
      display: flex;
      align-items: center;
      gap: var(--mee-space-4);
      padding: var(--mee-space-2) 0;
    }

    .avatar-circle {
      width: 48px;
      height: 48px;
      border-radius: var(--mee-radius-full);
      background: var(--mee-color-primary-light);
      color: var(--mee-color-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      font-weight: 700;
      flex-shrink: 0;
      user-select: none;
    }

    .identity-info {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-1);
      min-width: 0;
    }

    .identity-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .identity-phone-row {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
      flex-wrap: wrap;
    }

    .identity-phone {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
    }

    .edit-form-row {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
    }

    .form-error-msg {
      font-size: 14px;
      color: var(--mee-color-error);
      margin: 0;
    }

    .plan-card-body {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-3);
    }

    .plan-label {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin: 0;
    }

    .plan-name {
      font-size: 20px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0;
    }

    .plan-features {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
    }

    .plan-feature-item {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
      font-size: 14px;
      color: var(--mee-color-on-surface);
    }

    .plan-feature-item i {
      color: var(--mee-color-success);
      font-size: 14px;
    }

    .plan-manage-link {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      text-align: right;
      font-size: 14px;
      color: var(--mee-color-primary);
      font-weight: 500;
      text-decoration: none;
      cursor: pointer;
      transition: opacity var(--mee-transition-fast);
      min-height: 44px;
    }

    .plan-manage-link:hover {
      opacity: 0.8;
    }

    .logout-btn {
      width: 100%;
      min-height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--mee-space-2);
      background: transparent;
      border: 1.5px solid var(--mee-color-error);
      border-radius: var(--mee-radius-md);
      color: var(--mee-color-error);
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      transition: background var(--mee-transition-fast), color var(--mee-transition-fast);
      padding: var(--mee-space-3) var(--mee-space-4);
    }

    .logout-btn:hover {
      background: rgba(220, 38, 38, 0.06);
    }
  `],
  template: `
    <!-- Page heading -->
    <div class="profile-header">
      <h1 class="profile-title">Profile</h1>
      <p class="profile-subtitle">Manage your account</p>
    </div>

    <!-- Centered content column -->
    <div class="profile-content">

      <!-- Section 2: Identity card -->
      <mee-card>
        <div class="identity-card-body">
          <!-- Avatar initial circle -->
          <div class="avatar-circle" aria-hidden="true">
            {{ avatarInitial() }}
          </div>

          <!-- Name + phone row -->
          <div class="identity-info">
            <span class="identity-name">
              {{ auth.currentUser()?.name || 'Seller' }}
            </span>
            <div class="identity-phone-row">
              <span class="identity-phone">
                {{ formattedPhone() }}
              </span>
              <mee-badge
                [value]="planLabel()"
                [severity]="planSeverity()"
              />
            </div>
          </div>
        </div>
      </mee-card>

      <!-- Section 3: Edit form (no card wrapper) -->
      <form [formGroup]="form" (ngSubmit)="onSubmit()" novalidate class="edit-form-row">

        <!-- Display name -->
        <mee-input
          [label]="'Display Name'"
          [placeholder]="'Your name'"
          [required]="true"
          [error]="nameError()"
          formControlName="name"
        />

        <!-- Error message -->
        @if (errorMessage()) {
          <p class="form-error-msg" role="alert">
            {{ errorMessage() }}
          </p>
        }

        <!-- Save button — right-aligned, not full-width -->
        <div class="form-actions">
          <mee-button
            [label]="saved() ? 'Saved!' : 'Save changes'"
            variant="secondary"
            [loading]="saving()"
            [disabled]="form.invalid || saving()"
            [fullWidth]="false"
            (clicked)="onSubmit()"
          />
        </div>
      </form>

      <!-- Section 4: Plan card -->
      <mee-card>
        <div class="plan-card-body">
          <p class="plan-label">Current plan</p>
          <p class="plan-name">{{ planLabel() }}</p>

          <ul class="plan-features" aria-label="Plan features">
            <li class="plan-feature-item">
              <mee-icon name="check" />
              50 products / month
            </li>
            <li class="plan-feature-item">
              <mee-icon name="check" />
              AI autofill
            </li>
            <li class="plan-feature-item">
              <mee-icon name="check" />
              XLSX export
            </li>
          </ul>

          <a class="plan-manage-link" role="button" tabindex="0">
            Manage subscription
          </a>
        </div>
      </mee-card>

      <!-- Section 5: Logout button (no card wrapper) -->
      <button
        type="button"
        class="logout-btn"
        (click)="onLogout()"
      >
        <mee-icon name="logout" />
        Log out
      </button>

    </div>
  `,
})
export class ProfileComponent implements OnInit {
  protected readonly auth   = inject(AuthService);
  private  readonly router  = inject(Router);
  private  readonly fb      = inject(FormBuilder);

  readonly form = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(60)]],
  });

  // Local reactive state
  readonly saving       = signal(false);
  readonly saved        = signal(false);
  readonly errorMessage = signal<string | null>(null);

  // Derived display values
  readonly displayPhone = computed<string>(() => {
    const p = this.auth.currentUser()?.phone ?? '';
    return p.startsWith('+91') ? p.slice(3) : p;
  });

  readonly formattedPhone = computed<string>(() => {
    const digits = this.displayPhone();
    if (digits.length === 10) {
      return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
    }
    return digits ? `+91 ${digits}` : '';
  });

  readonly planSeverity = computed<MeeBadgeSeverity>(() => 'neutral');

  readonly planLabel = computed<string>(() => 'Free plan');

  readonly avatarInitial = computed<string>(() => {
    const name = this.auth.currentUser()?.name ?? '';
    return name.charAt(0).toUpperCase() || 'S';
  });

  /**
   * Not a computed() signal — FormControl state is not reactive to Angular signals.
   * Must be called as a method in the template: nameError()
   * Re-evaluated on every change detection cycle (OnPush: triggered by markAllAsTouched
   * or manual detectChanges in tests).
   */
  nameError(): string | undefined {
    const ctrl = this.form.get('name');
    if (!ctrl || ctrl.valid || ctrl.pristine) return undefined;
    if (ctrl.hasError('required'))   return 'Name is required';
    if (ctrl.hasError('minlength'))  return 'Name must be at least 2 characters';
    if (ctrl.hasError('maxlength'))  return 'Name must be 60 characters or fewer';
    return undefined;
  }

  ngOnInit(): void {
    this.form.patchValue({
      name: this.auth.currentUser()?.name ?? '',
    });
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving()) return;

    this.form.markAllAsTouched();
    if (this.form.invalid) return;

    this.saving.set(true);
    this.errorMessage.set(null);

    // Simulated save — Wave 6 will replace with real PATCH /api/v1/seller-profile
    // Direct setTimeout (no Promise wrapper) so vi.advanceTimersByTime() works in tests.
    setTimeout(() => {
      this.saving.set(false);
      this.saved.set(true);
      setTimeout(() => {
        if (this.saved()) this.saved.set(false);
      }, 3000);
    }, 800);
  }

  onLogout(): void {
    this.auth.logout();
    void this.router.navigate(['/login']);
  }
}

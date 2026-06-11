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
import { MeeCardComponent }   from '@mesell/ui-kit/card/card.component';
import { MeeBadgeComponent }  from '@mesell/ui-kit/badge/badge.component';
import { MeeInputComponent }  from '@mesell/ui-kit/input/input.component';
import { MeeButtonComponent } from '@mesell/ui-kit/button/button.component';
import type { MeeBadgeSeverity } from '@mesell/ui-kit/badge/badge.types';
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
  ],
  template: `
    <!-- Page heading -->
    <div class="p-4 pb-2 md:p-8 md:pb-4">
      <h1 class="text-2xl font-semibold" style="color: var(--mee-color-on-surface)">Profile</h1>
      <p class="text-sm mt-1" style="color: var(--mee-color-on-surface-muted)">Manage your account</p>
    </div>

    <!-- Centered content column -->
    <div class="w-full max-w-[560px] mx-auto px-4 pb-8 md:px-8 space-y-6">

      <!-- Identity card -->
      <mee-card>
        <div class="flex items-center gap-4 py-2">
          <!-- Avatar initial circle -->
          <div
            class="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full text-lg font-bold select-none"
            style="background: var(--mee-color-primary-light); color: var(--mee-color-primary)"
            aria-hidden="true"
          >
            {{ avatarInitial() }}
          </div>

          <!-- Name + phone row -->
          <div class="flex flex-col gap-1 min-w-0">
            <span class="text-base font-semibold truncate" style="color: var(--mee-color-on-surface)">
              {{ auth.currentUser()?.name || 'Seller' }}
            </span>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-sm" style="color: var(--mee-color-on-surface-muted)">
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

      <!-- Edit form -->
      <form [formGroup]="form" (ngSubmit)="onSubmit()" novalidate class="space-y-4">

        <!-- Display name -->
        <mee-input
          [label]="'Display Name'"
          [placeholder]="'Your name'"
          [required]="true"
          [error]="nameError()"
          formControlName="name"
        />

        <!-- Phone read-only — displayed via placeholder; no CVA binding needed -->
        <mee-input
          [label]="'Phone'"
          [disabled]="true"
          [placeholder]="displayPhone()"
        />

        <!-- Error message -->
        @if (errorMessage()) {
          <p class="text-sm" style="color: var(--mee-color-error)" role="alert">
            {{ errorMessage() }}
          </p>
        }

        <!-- Save button -->
        <mee-button
          [label]="saved() ? 'Saved!' : 'Save changes'"
          variant="primary"
          [loading]="saving()"
          [disabled]="form.invalid || saving()"
          [fullWidth]="true"
          (clicked)="onSubmit()"
        />
      </form>

      <!-- Divider -->
      <hr style="border-color: var(--mee-color-outline)" />

      <!-- Log out -->
      <mee-button
        label="Log out"
        variant="danger"
        [fullWidth]="true"
        (clicked)="onLogout()"
      />

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

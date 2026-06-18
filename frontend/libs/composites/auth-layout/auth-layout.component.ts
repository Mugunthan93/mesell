import {
  ChangeDetectionStrategy, Component
} from '@angular/core';

@Component({
  selector: 'mee-auth-layout',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [],
  template: `
    <div class="auth-wrapper">
      <div class="auth-card">
        <div class="auth-brand">
          <span class="auth-logo" aria-label="MeeSell">M</span>
          <span class="auth-wordmark">MeeSell</span>
        </div>
        <ng-content />
      </div>
    </div>
  `,
  styles: [`
    .auth-wrapper {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--mee-color-bg);
      /* 12px outer gutter at ≤359px so card can reach 336px on a 360px screen.
         Increase to --mee-space-4 (16px) at 640px+ (card is then constrained by max-width). */
      padding: var(--mee-space-3);
    }
    @media (min-width: 640px) {
      .auth-wrapper {
        padding: var(--mee-space-4);
      }
    }
    .auth-card {
      background: var(--mee-color-surface);
      border-radius: var(--mee-radius-lg);
      box-shadow: var(--mee-shadow-md);
      width: 100%;
      max-width: 420px;
      /* Mobile: tighter horizontal padding so form fields have breathing room at 360px.
         --mee-space-5 = 20px. At 360px card width = 336px; effective content = 296px.
         Desktop (sm+, ≥640px): restore 32px (--mee-space-8) padding. */
      padding: var(--mee-space-5);
    }
    @media (min-width: 640px) {
      .auth-card {
        padding: var(--mee-space-8);
      }
    }
    .auth-brand {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--mee-space-2);
      margin-bottom: var(--mee-space-6);
    }
    .auth-logo {
      color: var(--mee-color-primary);
      font-size: 32px;
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.5px;
    }
    .auth-wordmark {
      color: var(--mee-color-on-surface);
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.3px;
    }
  `],
})
export class AuthLayoutComponent {}

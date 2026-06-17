import {
  ChangeDetectionStrategy, Component
} from '@angular/core';
import { MeeOfflineBannerComponent } from '../offline-banner/offline-banner.component';

/**
 * AuthLayoutComponent — centred card layout for auth pages.
 *
 * Includes the global MeeOfflineBannerComponent at the top so every
 * auth page (login / signup / otp-verify) surfaces the offline state
 * both in federated mode (shell hosts the route) and in standalone
 * dev-serve mode (mfe-auth dev server).
 *
 * Individual auth pages still own their per-page inline error/warning banners
 * via MeeAlertBannerComponent for contextual error messaging.
 */
@Component({
  selector: 'mee-auth-layout',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeOfflineBannerComponent],
  template: `
    <!-- Global offline indicator — fixed top bar, visible on any auth page -->
    <mee-offline-banner />

    <div class="auth-wrapper">
      <div class="auth-card">
        <div class="auth-logo">MeeSell</div>
        <ng-content />
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }

    .auth-wrapper {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--mee-color-bg);
      /* Top padding accounts for the offline banner when it is visible */
      padding: var(--mee-space-4);
    }
    .auth-card {
      background: var(--mee-color-surface);
      border-radius: var(--mee-radius-md);
      box-shadow: var(--mee-shadow-md);
      width: 100%;
      max-width: 440px;
      padding: var(--mee-space-8);
    }
    /* 360px — reduce card padding so content breathes on small phones */
    @media (max-width: 400px) {
      .auth-card {
        padding: var(--mee-space-6);
        border-radius: var(--mee-radius-sm);
      }
    }
    .auth-logo {
      color: var(--mee-color-primary);
      font-size: 24px;
      font-weight: 700;
      text-align: center;
      margin-bottom: var(--mee-space-6);
      letter-spacing: -0.5px;
    }
  `],
})
export class AuthLayoutComponent {}

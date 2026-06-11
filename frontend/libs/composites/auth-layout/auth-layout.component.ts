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
        <div class="auth-logo">MeeSell</div>
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

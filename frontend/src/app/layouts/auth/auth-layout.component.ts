// layouts/auth/auth-layout.component.ts
// MeeAuthLayoutComponent — Full-page centered layout for unauthenticated routes:
// /, /signup, /login. Gradient background + white card containing router-outlet.
// No sidebar, no top header.

import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'mee-auth-layout',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet],
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 100%;
    }

    .auth-bg {
      flex: 1;
      min-height: 100vh;
      background: linear-gradient(135deg, #f5f5f5 0%, #ffe8d6 100%);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
    }

    /* ── Brand header above card ── */
    .auth-brand {
      text-align: center;
      margin-bottom: 24px;
    }

    .auth-brand-logo {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      background: #F26B23;
      border-radius: 12px;
      color: #fff;
      font-size: 22px;
      font-weight: 800;
      margin-bottom: 12px;
    }

    .auth-brand-name {
      display: block;
      font-size: 24px;
      font-weight: 800;
      color: #111827;
      letter-spacing: -0.02em;
    }

    .auth-brand-tagline {
      display: block;
      font-size: 13px;
      color: rgba(0, 0, 0, 0.45);
      margin-top: 4px;
    }

    /* ── White content card ── */
    .auth-card {
      background: #ffffff;
      width: 100%;
      max-width: 440px;
      border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
      overflow: hidden;
    }

    /* Footer note below card */
    .auth-footer {
      margin-top: 20px;
      text-align: center;
      font-size: 12px;
      color: rgba(0, 0, 0, 0.35);
    }
  `],
  template: `
    <div class="auth-bg">
      <!-- Brand above card -->
      <div class="auth-brand">
        <div class="auth-brand-logo">M</div>
        <span class="auth-brand-name">MeeSell</span>
        <span class="auth-brand-tagline">AI Catalog Builder for Meesho Sellers</span>
      </div>

      <!-- White card wrapping the auth route content -->
      <div class="auth-card">
        <router-outlet />
      </div>

      <p class="auth-footer">
        &copy; 2024 MeeSell. All rights reserved.
      </p>
    </div>
  `,
})
export class MeeAuthLayoutComponent {}

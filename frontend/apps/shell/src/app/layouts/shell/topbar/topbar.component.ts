import { ChangeDetectionStrategy, Component, computed, inject, viewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from '@mesell/core';
import { MeeMenuComponent, MeeIconComponent } from '@mesell/ui-kit';
import type { MeeMenuItem } from '@mesell/ui-kit';

import { LayoutService } from '../layout.service';

@Component({
  selector: 'mee-topbar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterModule, MeeMenuComponent, MeeIconComponent],
  template: `
    <header class="mee-topbar" role="banner">
      <button
        class="mee-topbar__hamburger"
        type="button"
        (click)="layoutService.onMenuToggle()"
        aria-label="Toggle navigation menu"
      >
        <mee-icon name="menu" />
      </button>

      <a class="mee-topbar__brand" routerLink="/dashboard" aria-label="MeeSell home">
        <svg width="28" height="28" viewBox="0 0 100 100" fill="none" aria-hidden="true">
          <rect width="100" height="100" rx="16" fill="var(--mee-color-primary)" />
          <text
            x="50"
            y="72"
            font-family="Arial Black,sans-serif"
            font-size="62"
            font-weight="900"
            fill="var(--mee-color-on-primary)"
            text-anchor="middle"
          >M</text>
        </svg>
        <span class="mee-topbar__wordmark">mesell</span>
      </a>

      <div class="mee-topbar__actions">
        <div
          class="mee-topbar__user"
          role="button"
          tabindex="0"
          aria-haspopup="true"
          aria-label="User menu"
          (click)="toggleUserMenu($event)"
          (keydown.enter)="toggleUserMenu($event)"
          (keydown.space)="toggleUserMenu($event)"
        >
          <div class="mee-topbar__avatar" aria-hidden="true">{{ userInitials }}</div>
          <span class="mee-topbar__username">{{ userName }}</span>
        </div>
        <mee-menu #userMenu [items]="userMenuItems" />
      </div>
    </header>
  `,
  styles: [
    `
      :host {
        display: block;
      }

      .mee-topbar {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 200;
        height: 60px;
        background: var(--mee-color-surface);
        box-shadow: var(--mee-shadow-sm);
        border-bottom: 1px solid var(--mee-color-outline);
        display: flex;
        align-items: center;
        padding: 0 var(--mee-space-4);
        gap: var(--mee-space-3);
      }

      .mee-topbar__hamburger {
        background: none;
        border: none;
        cursor: pointer;
        width: 40px;
        height: 40px;
        min-width: 44px;
        min-height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--mee-radius-sm);
        color: var(--mee-color-on-surface);
        font-size: 18px;
        transition: background var(--mee-transition-fast);
        flex-shrink: 0;
      }

      .mee-topbar__hamburger:hover,
      .mee-topbar__hamburger:focus-visible {
        background: var(--mee-color-bg);
        outline: 2px solid var(--mee-color-primary);
        outline-offset: 1px;
      }

      .mee-topbar__brand {
        display: flex;
        align-items: center;
        gap: var(--mee-space-2);
        text-decoration: none;
        color: inherit;
        flex-shrink: 0;
      }

      .mee-topbar__wordmark {
        font-size: 18px;
        font-weight: 700;
        color: var(--mee-color-on-surface);
        letter-spacing: -0.3px;
      }

      .mee-topbar__actions {
        margin-left: auto;
        display: flex;
        align-items: center;
        position: relative;
      }

      .mee-topbar__user {
        display: flex;
        align-items: center;
        gap: var(--mee-space-2);
        cursor: pointer;
        padding: var(--mee-space-1) var(--mee-space-2);
        border-radius: var(--mee-radius-sm);
        transition: background var(--mee-transition-fast);
        min-height: 44px;
      }

      .mee-topbar__user:hover,
      .mee-topbar__user:focus-visible {
        background: var(--mee-color-bg);
        outline: 2px solid var(--mee-color-primary);
        outline-offset: 1px;
      }

      .mee-topbar__avatar {
        width: 36px;
        height: 36px;
        border-radius: var(--mee-radius-full);
        background: var(--mee-color-primary);
        color: var(--mee-color-on-primary);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 14px;
        flex-shrink: 0;
      }

      .mee-topbar__username {
        font-size: 14px;
        font-weight: 500;
        color: var(--mee-color-on-surface-muted);
      }

      @media (max-width: 639px) {
        .mee-topbar__username {
          display: none;
        }

        .mee-topbar__hamburger {
          display: none;
        }
      }
    `,
  ],
})
export class TopbarComponent {
  protected readonly layoutService = inject(LayoutService);
  private readonly auth = inject(AuthService);

  private readonly userMenu = viewChild.required<MeeMenuComponent>('userMenu');

  protected readonly userMenuItems: MeeMenuItem[] = [
    { label: 'My Profile', icon: 'user', routerLink: '/profile' },
    { separator: true },
    { label: 'Log out', icon: 'logout', command: () => this.auth.logout() },
  ];

  protected toggleUserMenu(event: Event): void {
    this.userMenu().toggle(event);
  }

  protected get userName(): string {
    return this.auth.currentUser()?.name ?? 'Seller';
  }

  protected get userInitials(): string {
    const name = this.auth.currentUser()?.name ?? 'S';
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }
}

// layouts/shell/shell.component.ts
// MeeShellComponent — Spike Admin-style dark sidebar shell layout.
// Used by all authenticated routes (/dashboard, /catalogs/*, /profile).
// Design spec: dark navy sidebar #111c2d, 270px open / 80px collapsed,
// MeeSell orange active indicator #F26B23.

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { OfflineBannerComponent } from '@shared/components/offline-banner/offline-banner.component';
import { AuthService } from '@core/auth/auth.service';
import { map } from 'rxjs/operators';

interface NavItem {
  label: string;
  icon: string;       // Material icon name (outlined style)
  route: string;
  section?: string;   // Section header rendered above this item (first item in each section)
}

const NAV_ITEMS: NavItem[] = [
  { section: 'HOME',     label: 'Dashboard',   icon: 'dashboard',         route: '/dashboard' },
  {                      label: 'New Catalog',  icon: 'add_box',           route: '/catalogs/new' },
  { section: 'CATALOGS', label: 'My Catalogs', icon: 'list_alt',          route: '/dashboard' },
  { section: 'ACCOUNT',  label: 'Profile',     icon: 'manage_accounts',   route: '/profile' },
];

@Component({
  selector: 'mee-shell',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatToolbarModule,
    MatTooltipModule,
    OfflineBannerComponent,
  ],
  styles: [`
    :host {
      display: flex;
      height: 100%;
    }

    /* ── Sidenav container ── */
    mat-sidenav-container {
      flex: 1;
      height: 100%;
      background: #f0f5f9;
    }

    /* ── Sidebar panel ── */
    mat-sidenav {
      width: 270px;
      border: none;
      background: transparent;
      overflow: visible;
    }

    mat-sidenav.sidenav-collapsed {
      width: 80px;
    }

    /* ── Floating card wrapper (desktop) ── */
    .sidebar-card {
      background: #111c2d;
      height: calc(100vh - 32px);
      margin: 16px;
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      width: 238px; /* 270 - 32px margin */
    }

    .sidenav-collapsed .sidebar-card {
      width: 48px; /* 80 - 32px margin */
    }

    /* ── Mobile: full-height, no margin, no radius ── */
    .sidebar-mobile .sidebar-card {
      height: 100vh;
      margin: 0;
      border-radius: 0;
      width: 270px;
    }

    /* ── Sidebar header (branding) ── */
    .sidebar-header {
      padding: 24px 20px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      gap: 12px;
      overflow: hidden;
    }

    .brand-icon {
      width: 32px;
      height: 32px;
      background: #F26B23;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      color: #fff;
      font-size: 18px;
      font-weight: 700;
    }

    .brand-text {
      overflow: hidden;
    }

    .brand-name {
      color: #ffffff;
      font-size: 18px;
      font-weight: 700;
      line-height: 1.2;
      white-space: nowrap;
    }

    .brand-tagline {
      color: rgba(255, 255, 255, 0.5);
      font-size: 11px;
      white-space: nowrap;
    }

    /* ── Nav list ── */
    .nav-list {
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 8px 0;
    }

    .nav-section-header {
      padding: 20px 20px 6px;
      color: rgba(255, 255, 255, 0.4);
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      white-space: nowrap;
      overflow: hidden;
    }

    .sidenav-collapsed .nav-section-header {
      visibility: hidden;
      height: 20px;
      padding-bottom: 0;
    }

    /* ── Nav item ── */
    .nav-item {
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 0 16px;
      height: 44px;
      min-height: 44px;
      margin: 2px 8px;
      border-radius: 8px;
      cursor: pointer;
      text-decoration: none;
      color: rgba(255, 255, 255, 0.7);
      transition: background 0.15s ease;
      position: relative;
      overflow: hidden;
      border-left: 3px solid transparent;
    }

    .nav-item:hover {
      background: rgba(255, 255, 255, 0.06);
    }

    .nav-item.nav-active {
      background: rgba(242, 107, 35, 0.12);
      border-left-color: #F26B23;
      color: #F26B23;
    }

    .nav-item .nav-icon {
      font-size: 22px;
      width: 22px;
      height: 22px;
      flex-shrink: 0;
      color: rgba(255, 255, 255, 0.5);
      font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }

    .nav-item.nav-active .nav-icon {
      color: #F26B23;
    }

    .nav-label {
      font-size: 14px;
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
    }

    .sidenav-collapsed .nav-label {
      display: none;
    }

    .sidenav-collapsed .nav-item {
      padding: 0;
      justify-content: center;
      border-left: none;
      border-radius: 8px;
    }

    .sidenav-collapsed .nav-item.nav-active {
      background: rgba(242, 107, 35, 0.2);
    }

    /* ── Sidebar footer ── */
    .sidebar-footer {
      padding: 12px 8px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      flex-shrink: 0;
    }

    .logout-btn {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 16px;
      height: 44px;
      width: 100%;
      border-radius: 8px;
      cursor: pointer;
      color: rgba(255, 255, 255, 0.5);
      background: transparent;
      border: none;
      text-align: left;
      font-size: 14px;
      font-weight: 500;
      transition: background 0.15s ease;
    }

    .logout-btn:hover {
      background: rgba(255, 255, 255, 0.06);
      color: rgba(255, 255, 255, 0.8);
    }

    .sidenav-collapsed .logout-btn {
      justify-content: center;
      padding: 0;
    }

    .sidenav-collapsed .logout-label {
      display: none;
    }

    /* ── Main content area ── */
    mat-sidenav-content {
      display: flex;
      flex-direction: column;
    }

    /* ── Top header ── */
    .top-header {
      background: #ffffff;
      height: 64px;
      min-height: 64px;
      border-bottom: 1px solid #e8ecf0;
      display: flex;
      align-items: center;
      padding: 0 24px;
      gap: 16px;
      flex-shrink: 0;
      z-index: 10;
    }

    .header-toggle-btn {
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 8px;
      border: none;
      background: transparent;
      cursor: pointer;
      color: #374151;
      transition: background 0.15s ease;
      flex-shrink: 0;
    }

    .header-toggle-btn:hover {
      background: #f3f4f6;
    }

    .header-spacer {
      flex: 1;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .header-icon-btn {
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 8px;
      border: none;
      background: transparent;
      cursor: pointer;
      color: #6b7280;
      transition: background 0.15s ease;
      position: relative;
    }

    .header-icon-btn:hover {
      background: #f3f4f6;
    }

    .notification-dot {
      position: absolute;
      top: 10px;
      right: 10px;
      width: 7px;
      height: 7px;
      background: #F26B23;
      border-radius: 50%;
      border: 1px solid #fff;
    }

    .user-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #F26B23;
      color: #fff;
      font-size: 13px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      flex-shrink: 0;
      user-select: none;
    }

    /* ── Page content ── */
    .page-content {
      flex: 1;
      padding: 24px;
      overflow: auto;
      background: #f0f5f9;
    }

    @media (max-width: 1023px) {
      .page-content {
        padding: 16px;
      }
    }
  `],
  template: `
    <mat-sidenav-container>
      <!-- ── SIDEBAR ── -->
      <mat-sidenav
        #sidenav
        [mode]="isMobile() ? 'over' : 'side'"
        [opened]="!isMobile()"
        [class.sidenav-collapsed]="!isMobile() && sidebarCollapsed()"
        [class.sidebar-mobile]="isMobile()"
        fixedInViewport="false"
      >
        <div class="sidebar-card">
          <!-- Branding header -->
          <div class="sidebar-header">
            <div class="brand-icon">M</div>
            @if (!sidebarCollapsed() || isMobile()) {
              <div class="brand-text">
                <div class="brand-name">MeeSell</div>
                <div class="brand-tagline">AI Catalog Builder</div>
              </div>
            }
          </div>

          <!-- Nav list -->
          <nav class="nav-list" aria-label="Main navigation">
            @for (item of navItems; track item.route + item.label) {
              @if (item.section) {
                <div class="nav-section-header" aria-hidden="true">{{ item.section }}</div>
              }
              <a
                class="nav-item"
                [routerLink]="item.route"
                routerLinkActive="nav-active"
                [routerLinkActiveOptions]="{ exact: false }"
                [matTooltip]="sidebarCollapsed() && !isMobile() ? item.label : ''"
                matTooltipPosition="right"
                [attr.aria-label]="item.label"
              >
                <mat-icon class="nav-icon" fontSet="material-symbols-outlined">{{ item.icon }}</mat-icon>
                <span class="nav-label">{{ item.label }}</span>
              </a>
            }
          </nav>

          <!-- Footer: logout -->
          <div class="sidebar-footer">
            <button
              class="logout-btn"
              (click)="logout()"
              [matTooltip]="sidebarCollapsed() && !isMobile() ? 'Logout' : ''"
              matTooltipPosition="right"
              aria-label="Logout"
            >
              <mat-icon style="font-size:20px;width:20px;height:20px;flex-shrink:0;color:rgba(255,255,255,0.4);">logout</mat-icon>
              <span class="logout-label">Logout</span>
            </button>
          </div>
        </div>
      </mat-sidenav>

      <!-- ── MAIN CONTENT ── -->
      <mat-sidenav-content>
        <!-- Top header -->
        <header class="top-header">
          <button
            class="header-toggle-btn"
            (click)="toggleSidebar(sidenav)"
            aria-label="Toggle navigation"
          >
            <mat-icon>menu</mat-icon>
          </button>

          <span class="header-spacer"></span>

          <div class="header-actions">
            <!-- Notification bell -->
            <button class="header-icon-btn" aria-label="Notifications">
              <mat-icon style="font-size:22px;width:22px;height:22px;">notifications_none</mat-icon>
              <span class="notification-dot" aria-hidden="true"></span>
            </button>

            <!-- User avatar with initials -->
            <div class="user-avatar" role="button" tabindex="0" aria-label="User account" (click)="goToProfile()">
              {{ userInitials() }}
            </div>
          </div>
        </header>

        <!-- Offline banner -->
        <mee-offline-banner />

        <!-- Routed page content -->
        <main class="page-content">
          <router-outlet />
        </main>
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
})
export class MeeShellComponent implements OnInit {
  private readonly breakpointObserver = inject(BreakpointObserver);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly isMobile = signal(false);
  readonly sidebarCollapsed = signal(false);

  readonly navItems: NavItem[] = NAV_ITEMS;

  // Derive user initials from JWT userId (UUID) — show "?" until auth signal resolves
  readonly userInitials = computed<string>(() => {
    const uid = this.auth.userId();
    if (!uid) return '?';
    // Show first 2 chars of UUID in uppercase as a placeholder for real name
    return uid.slice(0, 2).toUpperCase();
  });

  ngOnInit(): void {
    // Subscribe to breakpoint changes — update isMobile signal
    this.breakpointObserver
      .observe(['(max-width: 1023px)'])
      .subscribe(result => {
        this.isMobile.set(result.matches);
        // Auto-expand on desktop after being on mobile
        if (!result.matches) {
          this.sidebarCollapsed.set(false);
        }
      });
  }

  toggleSidebar(sidenav: { toggle: () => void }): void {
    if (this.isMobile()) {
      // On mobile: toggle the overlay drawer open/closed
      sidenav.toggle();
    } else {
      // On desktop: collapse/expand the mini sidebar
      this.sidebarCollapsed.update(c => !c);
    }
  }

  logout(): void {
    this.auth.logout().subscribe();
  }

  goToProfile(): void {
    this.router.navigate(['/profile']);
  }
}

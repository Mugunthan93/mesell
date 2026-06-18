import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  OnInit,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router, RouterModule } from '@angular/router';
import { Subscription, filter } from 'rxjs';

import { meeIconClass } from '@mesell/ui-kit';
import type { MeeIconName } from '@mesell/ui-kit';

import { LayoutService } from '../layout.service';

interface NavItem {
  label: string;
  icon: MeeIconName;
  route: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

@Component({
  selector: 'mee-sidebar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="mee-sidebar" [class.mee-sidebar--open]="layoutService.isSidebarActive()">
      <div class="mee-sidebar__brand">
        <svg width="28" height="28" viewBox="0 0 100 100" fill="none" aria-hidden="true">
          <rect width="100" height="100" rx="14" fill="var(--mee-color-primary)" />
          <text
            x="50"
            y="70"
            font-family="Arial Black,sans-serif"
            font-size="60"
            font-weight="900"
            fill="var(--mee-color-on-primary)"
            text-anchor="middle"
          >M</text>
        </svg>
        <span>mesell</span>
      </div>

      <nav class="mee-sidebar__nav" aria-label="Primary">
        @for (group of navGroups; track group.label) {
          <div class="mee-sidebar__group">
            <span class="mee-sidebar__group-label">{{ group.label }}</span>
            @for (item of group.items; track item.route) {
              <a
                class="mee-sidebar__item"
                [routerLink]="item.route"
                routerLinkActive="mee-sidebar__item--active"
              >
                <i [class]="iconClass(item.icon)" aria-hidden="true"></i>
                <span>{{ item.label }}</span>
              </a>
            }
          </div>
        }
      </nav>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }
      .mee-sidebar {
        position: fixed;
        top: 60px;
        left: 0;
        bottom: 0;
        z-index: 150;
        width: 260px;
        background: var(--mee-color-sidebar);
        overflow-y: auto;
        overflow-x: hidden;
        transition: transform var(--mee-transition-base);
      }
      .mee-sidebar__brand {
        display: flex;
        align-items: center;
        gap: var(--mee-space-3);
        padding: var(--mee-space-5) var(--mee-space-4) var(--mee-space-4);
        color: var(--mee-color-on-primary);
        font-size: 16px;
        font-weight: 700;
        border-bottom: 1px solid color-mix(in srgb, var(--mee-color-outline) 12%, transparent);
        margin-bottom: var(--mee-space-2);
      }
      .mee-sidebar__nav {
        display: block;
      }
      .mee-sidebar__group {
        padding: var(--mee-space-2) 0;
      }
      .mee-sidebar__group-label {
        display: block;
        padding: var(--mee-space-1) var(--mee-space-4) var(--mee-space-2);
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: color-mix(in srgb, var(--mee-color-sidebar-text) 70%, transparent);
      }
      .mee-sidebar__item {
        display: flex;
        align-items: center;
        gap: var(--mee-space-3);
        padding: var(--mee-space-3) var(--mee-space-4);
        margin: var(--mee-space-1) var(--mee-space-2);
        border-radius: var(--mee-radius-sm);
        color: var(--mee-color-sidebar-text);
        text-decoration: none;
        font-size: 14px;
        font-weight: 500;
        transition: background var(--mee-transition-fast), color var(--mee-transition-fast);
      }
      .mee-sidebar__item:hover {
        background: color-mix(in srgb, var(--mee-color-sidebar-text) 12%, transparent);
        color: var(--mee-color-on-primary);
      }
      .mee-sidebar__item--active {
        background: var(--mee-color-primary-light);
        color: var(--mee-color-sidebar-active);
        border-left: 3px solid var(--mee-color-sidebar-active);
        padding-left: calc(var(--mee-space-4) - 3px);
      }
      .mee-sidebar__item i {
        font-size: 16px;
        width: 20px;
        text-align: center;
      }

      /* Desktop ≥992px: always visible */
      @media (min-width: 992px) {
        .mee-sidebar {
          transform: translateX(0) !important;
        }
      }
      /* <992px: hidden, slides in as overlay when open */
      @media (max-width: 991px) {
        .mee-sidebar {
          transform: translateX(-100%);
          box-shadow: var(--mee-shadow-lg);
        }
        .mee-sidebar--open {
          transform: translateX(0);
        }
      }
    `,
  ],
})
export class SidebarComponent implements OnInit, OnDestroy {
  protected readonly layoutService = inject(LayoutService);
  private readonly router = inject(Router);
  private readonly host = inject(ElementRef<HTMLElement>);

  private navSub?: Subscription;

  protected readonly navGroups: NavGroup[] = [
    {
      label: 'Main',
      items: [{ label: 'Home', icon: 'home', route: '/dashboard' }],
    },
    {
      label: 'Catalogs',
      items: [
        { label: 'My Catalogs', icon: 'list', route: '/catalogs' },
        { label: 'New Product', icon: 'add', route: '/catalog/new' },
        { label: 'Categories', icon: 'tag', route: '/categories' },
      ],
    },
    {
      label: 'Tools',
      items: [
        { label: 'Pricing', icon: 'calculator', route: '/pricing' },
        { label: 'Export', icon: 'download', route: '/export' },
      ],
    },
    {
      label: 'Account',
      items: [{ label: 'Profile', icon: 'user', route: '/profile' }],
    },
  ];

  /** Resolve a nav item's semantic icon name to its PrimeIcons class (FE-2: raw `pi pi-*` stays in the registry). */
  protected readonly iconClass = (name: MeeIconName): string => meeIconClass(name);

  ngOnInit(): void {
    this.navSub = this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(() => this.layoutService.closeMobileMenu());
  }

  ngOnDestroy(): void {
    this.navSub?.unsubscribe();
  }

  @HostListener('document:click', ['$event'])
  protected onDocumentClick(event: MouseEvent): void {
    if (!this.layoutService.isSidebarActive()) {
      return;
    }
    const target = event.target as Node | null;
    if (target && !this.host.nativeElement.contains(target)) {
      this.layoutService.closeMobileMenu();
    }
  }
}

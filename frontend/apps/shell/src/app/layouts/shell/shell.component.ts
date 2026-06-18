import { NgClass } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { meeIconClass } from '@mesell/ui-kit';
import type { MeeIconName } from '@mesell/ui-kit';

import { LayoutService } from './layout.service';
import { TopbarComponent } from './topbar/topbar.component';
import { SidebarComponent } from './sidebar/sidebar.component';

interface BottomNavItem {
  label: string;
  icon: MeeIconName;
  route: string;
}

@Component({
  selector: 'mee-shell',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    NgClass,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    TopbarComponent,
    SidebarComponent,
  ],
  templateUrl: './shell.component.html',
  styleUrls: ['./shell.component.css'],
})
export class ShellComponent {
  protected readonly layoutService = inject(LayoutService);

  protected readonly layoutClass = computed(() => ({
    'mee-layout--sidebar-inactive': this.layoutService.layoutState().staticMenuDesktopInactive,
    'mee-layout--overlay-active': this.layoutService.layoutState().overlayMenuActive,
    'mee-layout--mobile-active': this.layoutService.layoutState().mobileMenuActive,
  }));

  // Bottom-tab routes adapted to the shell's real route table. Pricing/Export are
  // :id-scoped, so the tab entry points at /catalogs.
  protected readonly bottomNavItems: BottomNavItem[] = [
    { label: 'Home', icon: 'home', route: '/dashboard' },
    { label: 'Catalogs', icon: 'list', route: '/catalogs' },
    { label: 'New', icon: 'add', route: '/catalogs/new' },
    { label: 'Account', icon: 'user', route: '/profile' },
  ];

  /** Resolve a nav item's semantic icon name to its PrimeIcons class (FE-2: raw `pi pi-*` stays in the registry). */
  protected readonly iconClass = (name: MeeIconName): string => meeIconClass(name);
}

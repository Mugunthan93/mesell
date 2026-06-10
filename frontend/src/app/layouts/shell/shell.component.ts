import {
  ChangeDetectionStrategy, Component, inject, signal, viewChild
} from '@angular/core';

import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { MeeDrawerComponent, MeeMenuComponent } from '../../ui';
import type { MeeMenuItem } from '../../ui';

@Component({
  selector: 'mee-shell',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterOutlet, RouterLink, RouterLinkActive,
    MeeDrawerComponent, MeeMenuComponent,
  ],
  templateUrl: './shell.component.html',
  styleUrls:   ['./shell.component.css'],
})
export class ShellComponent {
  private readonly userMenu = viewChild.required<MeeMenuComponent>('userMenu');

  readonly auth = inject(AuthService);
  protected mobileSidebarVisible = signal(false);

  protected readonly navItems = [
    { label: 'Dashboard',   route: '/dashboard',    icon: 'pi pi-home' },
    { label: 'New Catalog', route: '/catalogs/new', icon: 'pi pi-plus-circle' },
    { label: 'My Catalogs', route: '/catalogs',     icon: 'pi pi-list' },
    { label: 'Profile',     route: '/profile',      icon: 'pi pi-user' },
  ] as const;

  protected readonly userMenuItems: MeeMenuItem[] = [
    { label: 'My Profile', icon: 'pi pi-user',     routerLink: '/profile' },
    { separator: true },
    { label: 'Log out',    icon: 'pi pi-sign-out', command: () => this.auth.logout() },
  ];

  protected toggleUserMenu(event: Event): void {
    this.userMenu().toggle(event);
  }

  protected get userInitials(): string {
    const name = this.auth.currentUser()?.name ?? 'U';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }
}

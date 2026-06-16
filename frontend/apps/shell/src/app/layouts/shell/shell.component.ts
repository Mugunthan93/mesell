import {
  ChangeDetectionStrategy, Component, computed, inject, signal, viewChild
} from '@angular/core';

import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '@mesell/core';
import { MeeDrawerComponent, MeeMenuComponent, MeeIconComponent } from '@mesell/ui-kit';
import type { MeeMenuItem, MeeIconName } from '@mesell/ui-kit';

/** A single navigable sidebar entry within a group. */
interface NavItem {
  readonly label: string;
  readonly route: string;
  /** Semantic icon name resolved via MEE_ICONS registry. */
  readonly icon: MeeIconName;
  /** Render as an accent/primary call-to-action (e.g. "+ New Catalog"). */
  readonly accent?: boolean;
  /** When true, also keep the group active for any path PREFIXED by `route`
   *  (e.g. /catalogs stays active on /catalogs/new and /catalogs/:id/*). When
   *  false/undefined, exact-match active highlighting is used so e.g. /catalogs
   *  does NOT bleed into /categories/*. */
  readonly prefixMatch?: boolean;
  /** Optional visibility predicate — item is rendered only when this returns true.
   *  Used for the conditional Onboarding item (founder DECISION #1). */
  readonly visible?: () => boolean;
}

/** A labelled group of sidebar items (founder-approved 4-group structure). */
interface NavGroup {
  readonly label: string;
  readonly items: readonly NavItem[];
}

@Component({
  selector: 'mee-shell',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterOutlet, RouterLink, RouterLinkActive,
    MeeDrawerComponent, MeeMenuComponent, MeeIconComponent,
  ],
  templateUrl: './shell.component.html',
  styleUrls:   ['./shell.component.css'],
})
export class ShellComponent {
  private readonly userMenu = viewChild.required<MeeMenuComponent>('userMenu');

  readonly auth = inject(AuthService);
  protected mobileSidebarVisible = signal(false);

  /**
   * Onboarding completion — founder DECISION #1 (2026-06-16): HIDE the Onboarding
   * sidebar item once the seller has finished onboarding.
   *
   * INTEGRATION SEAM CLOSED (Path B, 2026-06-16): the `onboarding_complete` flag is
   * now promoted onto the shared `@mesell/core` AuthUser, sourced from
   * `GET /api/v1/auth/me` (backend reads it from the customer service). It hydrates
   * on login, app boot, silent refresh, and on `AuthService.refreshUser()` after an
   * onboarding submit — so this predicate reflects real state with no remote-boundary
   * breach. Absent flag (legacy mock users) ⇒ false ⇒ item stays visible (safe default).
   */
  protected readonly onboardingComplete = computed<boolean>(
    () => this.auth.currentUser()?.onboarding_complete === true,
  );

  /**
   * Founder-approved 4-group sidebar (ratified 2026-06-16). Protected (post-auth)
   * routes ONLY — public routes ('' landing, /login, /signup, /otp-verify) are not
   * here. The per-catalog sub-flow (/catalogs/:id/{edit,images,pricing,preview,
   * export}) is DELIBERATELY EXCLUDED: those are :id-scoped and would be dead links
   * without an open catalog — they live in the catalog detail step/tab bar, not here.
   */
  protected readonly navGroups: readonly NavGroup[] = [
    {
      label: 'Home',
      items: [
        { label: 'Dashboard', route: '/dashboard', icon: 'dashboard' },
      ],
    },
    {
      label: 'Catalogs',
      items: [
        // prefixMatch: /catalogs stays active on /catalogs/new AND /catalogs/:id/*
        { label: 'All Catalogs',   route: '/catalogs',     icon: 'catalog', prefixMatch: true },
        // Accent CTA. Exact-match so it doesn't stay active on every /catalogs/* page.
        { label: 'New Catalog',    route: '/catalogs/new', icon: 'add', accent: true },
      ],
    },
    {
      label: 'Categories',
      items: [
        { label: 'Browse', route: '/categories/browse', icon: 'browse', prefixMatch: true },
      ],
    },
    {
      label: 'Account',
      items: [
        { label: 'Profile',    route: '/profile',    icon: 'user' },
        // Founder DECISION #1: visible ONLY while onboarding is NOT complete.
        { label: 'Onboarding', route: '/onboarding', icon: 'send',
          visible: () => !this.onboardingComplete() },
      ],
    },
  ];

  /** Items in `group` that pass their visibility predicate (if any). */
  protected visibleItems(group: NavGroup): readonly NavItem[] {
    return group.items.filter(item => item.visible ? item.visible() : true);
  }

  protected readonly userMenuItems: MeeMenuItem[] = [
    { label: 'My Profile', icon: 'user',   routerLink: '/profile' },
    { separator: true },
    { label: 'Log out',    icon: 'logout', command: () => this.auth.logout() },
  ];

  protected toggleUserMenu(event: Event): void {
    this.userMenu().toggle(event);
  }

  protected get userInitials(): string {
    const name = this.auth.currentUser()?.name ?? 'U';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }
}

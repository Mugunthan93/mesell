import {
  ChangeDetectionStrategy, Component, computed, inject, signal, viewChild
} from '@angular/core';

import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '@mesell/core';
import { MeeDrawerComponent, MeeMenuComponent } from '@mesell/ui-kit';
import type { MeeMenuItem } from '@mesell/ui-kit';

/** A single navigable sidebar entry within a group. */
interface NavItem {
  readonly label: string;
  readonly route: string;
  /** PrimeNG `pi pi-*` icon class (the codebase-wide icon convention; founder
   *  DECISION #2 ratified the placeholders are adjustable — Material names in the
   *  spec map to their nearest `pi` equivalent to avoid pulling a second icon font). */
  readonly icon: string;
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
    MeeDrawerComponent, MeeMenuComponent,
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
   * GAP (reported to the Director): there is NO onboarding-completion flag on the
   * shell-shared `@mesell/core` AuthService / AuthUser singleton. The real flag
   * (`onboarding_complete: boolean`) lives on the `SellerProfile` model driven by
   * `SellerProfileService`, which is REMOTE-PRIVATE and explicitly NON-root
   * (mfe-onboarding, SP05 D32) — the shell cannot read it without breaching the
   * remote boundary or inventing new cross-boundary state (both forbidden by the
   * dispatch brief: "reuse, do NOT invent a new source of truth").
   *
   * So this is wired to the CLOSEST existing shell signal: derive from the shared
   * AuthService user. Until an `onboarding_complete` flag is promoted onto the
   * `@mesell/core` AuthUser (the documented integration seam below), we default to
   * "not complete" => the Onboarding item stays visible. When the flag lands,
   * change the body to `this.auth.currentUser()?.onboarding_complete === true`.
   */
  protected readonly onboardingComplete = computed<boolean>(() => {
    const user = this.auth.currentUser();
    // INTEGRATION SEAM: replace with `user?.onboarding_complete === true` once
    // the flag is promoted onto @mesell/core AuthUser. Today AuthUser has no such
    // field, so this is always false (item visible) — the safe default per #1.
    return (user as { onboarding_complete?: boolean } | null)?.onboarding_complete === true;
  });

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
        { label: 'Dashboard', route: '/dashboard', icon: 'pi pi-th-large' },
      ],
    },
    {
      label: 'Catalogs',
      items: [
        // prefixMatch: /catalogs stays active on /catalogs/new AND /catalogs/:id/*
        { label: 'All Catalogs',   route: '/catalogs',     icon: 'pi pi-box', prefixMatch: true },
        // Accent CTA. Exact-match so it doesn't stay active on every /catalogs/* page.
        { label: 'New Catalog',    route: '/catalogs/new', icon: 'pi pi-plus', accent: true },
      ],
    },
    {
      label: 'Categories',
      items: [
        { label: 'Browse', route: '/categories/browse', icon: 'pi pi-sitemap', prefixMatch: true },
      ],
    },
    {
      label: 'Account',
      items: [
        { label: 'Profile',    route: '/profile',    icon: 'pi pi-user' },
        // Founder DECISION #1: visible ONLY while onboarding is NOT complete.
        { label: 'Onboarding', route: '/onboarding', icon: 'pi pi-send',
          visible: () => !this.onboardingComplete() },
      ],
    },
  ];

  /** Items in `group` that pass their visibility predicate (if any). */
  protected visibleItems(group: NavGroup): readonly NavItem[] {
    return group.items.filter(item => item.visible ? item.visible() : true);
  }

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

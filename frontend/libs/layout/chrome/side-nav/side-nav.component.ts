import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { MeeNavItemComponent } from '../nav-item/nav-item.component';
import type { MeeNavGroup } from '../chrome.types';

/**
 * `mee-side-nav` — the sidebar: brand + labelled nav groups (chrome primitive).
 *
 * Placement-agnostic so the host can use ONE instance for the fixed desktop
 * sidebar AND a second instance inside the mobile `mee-drawer`. Re-emits
 * `navigated` from any child `mee-nav-item` so the drawer can close on select.
 *
 * Presentational: receives already-filtered `MeeNavGroup[]` (the host applies
 * visibility predicates + drops empty groups + maps prefixMatch→exact). Holds
 * no AuthService / routes table.
 *
 * SHELL-ONLY (FE-3). Positioning (width / fixed / responsive-hide) stays
 * host-side on `.sidebar-desktop`; this component owns the sidebar's inner
 * identity (dark surface, brand, group dividers, nav items). Lifted verbatim
 * from the pre-Phase-4 ShellComponent; class names preserved for parity.
 */
@Component({
  selector: 'mee-side-nav',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeNavItemComponent],
  template: `
    <nav aria-label="Main navigation">
      <div class="sidebar-brand">{{ brand() }}</div>
      @for (group of groups(); track group.label) {
        @if (group.items.length > 0) {
          <div class="nav-group" role="group" [attr.aria-label]="group.label">
            <h2 class="nav-group__label">{{ group.label }}</h2>
            <ul class="sidebar-nav">
              @for (item of group.items; track item.route) {
                <li>
                  <mee-nav-item
                    [route]="item.route"
                    [label]="item.label"
                    [icon]="item.icon"
                    [accent]="item.accent ?? false"
                    [exact]="item.exact ?? true"
                    (navigated)="navigated.emit()"
                  />
                </li>
              }
            </ul>
          </div>
        }
      }
    </nav>
  `,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      background: var(--mee-color-sidebar);
    }

    .sidebar-brand {
      color: #ffffff;
      font-size: 20px;
      font-weight: 700;
      padding: 24px 20px 20px;
      letter-spacing: -0.3px;
    }

    /* Sidebar groups (Home / Catalogs / Categories / Account) */
    .nav-group {
      padding: 4px 0;
    }

    .nav-group + .nav-group {
      margin-top: 4px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
    }

    .nav-group__label {
      margin: 0;
      padding: 14px 20px 6px;
      font-size: 11px;
      font-weight: 600;
      line-height: 1;
      letter-spacing: 0.6px;
      text-transform: uppercase;
      color: color-mix(in srgb, var(--mee-color-sidebar-text) 65%, transparent);
    }

    .sidebar-nav {
      list-style: none;
      margin: 0;
      padding: 4px 0;
    }
  `],
})
export class MeeSideNavComponent {
  /** Brand text shown at the top of the sidebar. Default 'MeeSell'. */
  readonly brand = input<string>('MeeSell');
  /** Labelled nav groups (host-filtered, host-mapped to the lib shape). */
  readonly groups = input.required<readonly MeeNavGroup[]>();

  /** Re-emitted from any child nav item's click (host drawer closes on this). */
  readonly navigated = output<void>();
}

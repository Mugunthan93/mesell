import {
  ChangeDetectionStrategy,
  Component,
  input,
  viewChild,
} from '@angular/core';
import { MeeMenuComponent } from '@mesell/ui-kit';
import type { MeeMenuItem } from '@mesell/ui-kit';

/**
 * `mee-user-menu` — avatar trigger + popup dropdown (chrome primitive).
 *
 * The avatar is a keyboard-accessible button (role/tabindex/enter/space) that
 * toggles an internal `mee-menu` popup. Presentational: the host passes the
 * user's `initials` and the `items` model; this component owns only the
 * toggle wiring (lifted from the shell's `toggleUserMenu`).
 *
 * SHELL-ONLY (FE-3). Lifted verbatim; `.avatar` class + dimensions preserved
 * for parity.
 */
@Component({
  selector: 'mee-user-menu',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeMenuComponent],
  template: `
    <div class="user-menu-trigger">
      <div
        class="avatar"
        role="button"
        tabindex="0"
        aria-haspopup="true"
        aria-label="User menu"
        (click)="toggle($event)"
        (keydown.enter)="toggle($event)"
        (keydown.space)="toggle($event)"
      >
        {{ initials() }}
      </div>
      <mee-menu #userMenu [items]="items()" />
    </div>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
    }

    .avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--mee-color-primary);
      color: var(--mee-color-on-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      user-select: none;
      min-height: 44px;
      min-width: 44px;
    }
  `],
})
export class MeeUserMenuComponent {
  /** User initials shown in the avatar (e.g. 'MS'). */
  readonly initials = input.required<string>();
  /** Dropdown menu items in MeeSell-semantic shape. */
  readonly items = input.required<MeeMenuItem[]>();

  private readonly menu = viewChild.required<MeeMenuComponent>('userMenu');

  /** Toggle the popup menu, anchored to the originating event target. */
  toggle(event: Event): void {
    this.menu().toggle(event);
  }
}

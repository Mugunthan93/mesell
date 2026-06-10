import {
  ChangeDetectionStrategy,
  Component,
  input,
  viewChild,
} from '@angular/core';
import { Menu } from 'primeng/menu';
import type { MenuItem } from 'primeng/api';
import type { MeeMenuItem } from './menu.types';

/**
 * MeeSell popup menu wrapper — Layer 2 abstraction over PrimeNG's <p-menu>.
 * Consumers pass `MeeMenuItem[]` and call `toggle(event)` to open the popup
 * anchored to a trigger element. PrimeNG's MenuItem shape stays internal.
 */
@Component({
  selector: 'mee-menu',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Menu],
  template: `<p-menu #menu [model]="primeItems()" [popup]="true" />`,
})
export class MeeMenuComponent {
  /** Menu items in MeeSell-semantic shape. */
  readonly items = input.required<MeeMenuItem[]>();

  private readonly menu = viewChild.required<Menu>('menu');

  /** Maps the MeeSell-semantic items to PrimeNG's MenuItem shape. */
  protected primeItems(): MenuItem[] {
    return this.items().map((item) => ({
      label: item.label,
      icon: item.icon,
      routerLink: item.routerLink,
      command: item.command ? () => item.command!() : undefined,
      separator: item.separator,
    }));
  }

  /** Toggles the popup menu, anchored to the originating event target. */
  toggle(event: Event): void {
    this.menu().toggle(event);
  }
}

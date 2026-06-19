import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { RouterModule } from '@angular/router';
import { Breadcrumb } from 'primeng/breadcrumb';
import type { MenuItem } from 'primeng/api';
import type { MeeMenuItem } from '../menu/menu.types';
import { MEE_ICONS } from '../icon/icon.registry';

/** Map a MeeMenuItem to the PrimeNG MenuItem shape expected by p-breadcrumb. */
function toMenuItem(item: MeeMenuItem): MenuItem {
  return {
    label:      item.label,
    icon:       item.icon ? MEE_ICONS[item.icon] : undefined,
    routerLink: item.routerLink,
    command:    item.command,
  };
}

@Component({
  selector: 'mee-breadcrumb',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Breadcrumb, RouterModule],
  template: `
    <p-breadcrumb [model]="pgItems()" [home]="pgHome()" />
  `,
})
export class MeeBreadcrumbComponent {
  /** Trail crumbs (excluding home). */
  readonly items = input.required<MeeMenuItem[]>();
  /** Optional home crumb (icon 'dashboard' typical). */
  readonly home  = input<MeeMenuItem | undefined>(undefined);

  readonly pgItems = computed<MenuItem[]>(() =>
    this.items().map(toMenuItem),
  );

  readonly pgHome = computed<MenuItem | undefined>(() => {
    const h = this.home();
    return h ? toMenuItem(h) : undefined;
  });
}

import {
  ChangeDetectionStrategy,
  Component,
  input,
  model,
} from '@angular/core';
import { Drawer } from 'primeng/drawer';

/**
 * MeeSell drawer wrapper — Layer 2 abstraction over PrimeNG's <p-drawer>.
 * Exposes only the MeeSell-semantic surface: a two-way `visible` model, an
 * optional `modal` flag, and a `styleClass` passthrough. Projects arbitrary
 * content. PrimeNG stays sealed inside this wrapper.
 */
@Component({
  selector: 'mee-drawer',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Drawer],
  template: `
    <p-drawer
      [visible]="visible()"
      (visibleChange)="visible.set($event)"
      [modal]="modal()"
      [styleClass]="styleClass()"
    >
      <ng-content />
    </p-drawer>
  `,
})
export class MeeDrawerComponent {
  /** Two-way bound visibility of the drawer. */
  readonly visible = model<boolean>(false);
  /** When true, renders a backdrop and traps focus. */
  readonly modal = input<boolean>(true);
  /** Passthrough style class applied to the underlying panel. */
  readonly styleClass = input<string>('');
}

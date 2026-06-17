import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { MEE_ICONS, MeeIconName } from './icon.registry';

/**
 * mee-icon — semantic icon component.
 *
 * Renders a PrimeIcons <i> element using a MeeIconName semantic key.
 * The icon set is fully defined in icon.registry.ts — this component
 * adds no raw icon class literals.
 *
 * Usage: <mee-icon name="dashboard" />
 *        <mee-icon [name]="item.icon" />
 *
 * aria-hidden="true" is always set because icons are decorative here;
 * meaningful labels live in adjacent text elements.
 */
@Component({
  selector: 'mee-icon',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<i [class]="resolved()" aria-hidden="true"></i>`,
})
export class MeeIconComponent {
  readonly name = input.required<MeeIconName>();

  readonly resolved = computed<string>(() => MEE_ICONS[this.name()]);
}
